import json
import os
import re
from collections.abc import Iterator
from functools import lru_cache
from threading import Lock

from fastapi import HTTPException
from google import genai
from google.genai import types

from app.db import get_connection
from app.rag.interface import LawArticle, get_rag


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "kun-kgp-mytnt831")
MODEL = os.getenv("ADVISOR_MODEL", "gemini-3.5-flash")
TOP_K = 6
HISTORY_TURNS = 6  # 질의 재작성·답변에 넘길 최근 메시지 수
_CLIENT_LOCK = Lock()

DISCLAIMER = "※ 본 답변은 참고용이며 법적 판단이 아닙니다. 최신 법령 원문을 반드시 확인하세요."

ANSWER_SYSTEM_PROMPT = f"""
너는 산업안전보건 법령 상담 AI 어드바이저다.
사업주·관리감독자·근로자가 이해하기 쉽게, 아래 [근거 조문]만을 근거로 답한다.

규칙
1. 첫 문단에서 질문에 대한 결론을 1~2문장으로 먼저 말한다.
2. 이어서 필요한 의무·기준·절차를 짧은 항목(- )으로 정리한다.
3. 법령 내용을 말하는 모든 문장 끝에 근거 조문 번호를 [1], [2] 형식으로 붙인다.
4. [근거 조문]에 없는 법령·조문·수치는 절대 지어내지 않는다.
5. 근거 조문으로 답할 수 없으면 "제공된 법령 조문만으로는 확인하기 어렵습니다"라고 말하고,
   답변에 필요한 추가 정보(업종, 상시근로자 수, 작업 종류 등)를 되묻는다.
6. 산업안전보건과 무관한 질문에는 답하지 말고 어드바이저의 역할을 안내한다.
7. 마크다운 표·제목(#)은 쓰지 말고, 굵게(**)와 목록(- )만 사용한다.
8. 마지막 줄에 다음 문장을 그대로 붙인다: {DISCLAIMER}
9. 같은 조번호라도 법령명이 다르면 다른 근거다. 원문에 시행일 안내가 있으면 적용 시기와 대상을 구분하고, 아직 시행되지 않은 규정을 현재 의무로 설명하지 않는다.
""".strip()

REWRITE_PROMPT = """
아래 대화의 마지막 사용자 질문을, 이전 대화 맥락 없이도 이해되는 법령 검색용 한 문장 질의로 바꿔라.
질문과 관련 있는 현장 장비와 위험요소를 질의에 포함하되, 현장 상황에 없는 사실은 추가하지 마라.
질의 문장만 출력하라.

[대화]
{history}

[현장 상황]
{context}

[마지막 질문]
{message}
""".strip()

FOLLOWUP_PROMPT = """
다음 질문과 답변을 보고, 사용자가 이어서 물어볼 만한 산업안전보건 법령 질문 3개를 만들어라.
각 질문은 30자 이내 한국어로, JSON 문자열 배열로만 출력하라.

[질문]
{question}

[답변]
{answer}
""".strip()


@lru_cache(maxsize=1)
def _create_client() -> genai.Client:
    return genai.Client(vertexai=True, project=PROJECT_ID, location="global")


def _client() -> genai.Client:
    with _CLIENT_LOCK:
        return _create_client()


def _config(**kwargs) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
        **kwargs,
    )


# =====================================================
# 세션 / 메시지 저장
# =====================================================

def _get_or_create_session(user_id: int, session_id: int | None, first_message: str) -> int:
    with get_connection() as conn:
        if session_id is not None:
            row = conn.execute(
                "SELECT id FROM advisor_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
            return row["id"]

        cursor = conn.execute(
            "INSERT INTO advisor_sessions (user_id, title) VALUES (?, ?)",
            (user_id, first_message[:40]),
        )
        return cursor.lastrowid


def _load_history(session_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM advisor_messages
            WHERE session_id = ? ORDER BY id DESC LIMIT ?
            """,
            (session_id, HISTORY_TURNS),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _save_turn(session_id: int, question: str, answer: str, sources: list[dict]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO advisor_messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, question),
        )
        conn.execute(
            """
            INSERT INTO advisor_messages (session_id, role, content, sources)
            VALUES (?, 'assistant', ?, ?)
            """,
            (session_id, answer, json.dumps(sources, ensure_ascii=False)),
        )
        conn.execute(
            "UPDATE advisor_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )


def list_sessions(current_user: dict) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at FROM advisor_sessions
            WHERE user_id = ? ORDER BY updated_at DESC, id DESC
            """,
            (current_user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id: int, current_user: dict) -> dict:
    with get_connection() as conn:
        session = conn.execute(
            "SELECT id, title, created_at, updated_at FROM advisor_sessions WHERE id = ? AND user_id = ?",
            (session_id, current_user["id"]),
        ).fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        messages = conn.execute(
            "SELECT id, role, content, sources, created_at FROM advisor_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

    return {
        **dict(session),
        "messages": [
            {**dict(row), "sources": json.loads(row["sources"]) if row["sources"] else []}
            for row in messages
        ],
    }


# =====================================================
# RAG + 생성
# =====================================================

def _format_history(history: list[dict]) -> str:
    return "\n".join(
        f"{'사용자' if turn['role'] == 'user' else '어드바이저'}: {turn['content'][:500]}"
        for turn in history
    )


def rewrite_query(history: list[dict], message: str, context: str | None = None) -> str:
    situation = " ".join(context.split()) if context else ""
    fallback = f"{message} {situation}" if situation else message
    if not history:
        return fallback
    response = _client().models.generate_content(
        model=MODEL,
        contents=REWRITE_PROMPT.format(
            history=_format_history(history), context=situation, message=message
        ),
        config=_config(temperature=0),
    )
    return (response.text or "").strip() or fallback


def _source_payload(index: int, article: LawArticle) -> dict:
    return {
        "n": index,
        "id": article["id"],
        "law_title": article["law_title"],
        "article": article["article"],
        "heading": article["heading"],
        "text": article["text"],
        "url": article["url"],
    }


def _build_contents(history: list[dict], message: str, sources: list[dict], context: str | None) -> list:
    evidence = "\n\n".join(
        f"[{s['n']}] {s['law_title']} {s['article']}({s['heading']})\n{s['text']}" for s in sources
    ) or "(검색된 조문 없음)"

    contents = [
        types.Content(
            role="user" if turn["role"] == "user" else "model",
            parts=[types.Part(text=turn["content"])],
        )
        for turn in history
    ]
    situation = f"[현장 상황]\n{context}\n\n" if context else ""
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=f"{situation}[근거 조문]\n{evidence}\n\n[질문]\n{message}")],
        )
    )
    return contents


def suggest_followups(question: str, answer: str) -> list[str]:
    try:
        response = _client().models.generate_content(
            model=MODEL,
            contents=FOLLOWUP_PROMPT.format(question=question, answer=answer[:1500]),
            config=_config(temperature=0.4, response_mime_type="application/json"),
        )
        items = json.loads(response.text or "[]")
        return [str(item) for item in items if item][:3]
    except Exception:
        return []


def _cited_numbers(answer: str, max_n: int) -> list[int]:
    numbers = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return sorted(n for n in numbers if 1 <= n <= max_n)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_chat(
    current_user: dict,
    message: str,
    session_id: int | None = None,
    context: str | None = None,
) -> Iterator[str]:
    """SSE 이벤트: progress → sources → delta* → done (실패 시 error)"""
    session_id = _get_or_create_session(current_user["id"], session_id, message)

    try:
        history = _load_history(session_id)

        yield _sse("progress", {"stage": "rewrite", "message": "질문을 이해하고 있습니다"})
        query = rewrite_query(history, message, context)

        yield _sse("progress", {"stage": "search", "message": "관련 법령을 찾고 있습니다", "query": query})
        articles = get_rag().search_laws(query, top_k=TOP_K)
        sources = [_source_payload(i, article) for i, article in enumerate(articles, start=1)]
        yield _sse("sources", {"session_id": session_id, "query": query, "sources": sources})

        yield _sse("progress", {"stage": "answer", "message": "답변을 작성하고 있습니다"})
        answer = ""
        stream = _client().models.generate_content_stream(
            model=MODEL,
            contents=_build_contents(history, message, sources, context),
            config=_config(system_instruction=ANSWER_SYSTEM_PROMPT, temperature=0.2),
        )
        for chunk in stream:
            if chunk.text:
                answer += chunk.text
                yield _sse("delta", {"text": chunk.text})

        cited = _cited_numbers(answer, len(sources))
        _save_turn(session_id, message, answer, sources)
        yield _sse("done", {
            "session_id": session_id,
            "cited": cited,
            "followups": suggest_followups(message, answer),
        })
    except Exception as exc:
        yield _sse("error", {"message": "답변 생성 중 오류가 발생했습니다.", "detail": str(exc)[:300]})
