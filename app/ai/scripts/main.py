import chromadb
import vertexai
import json
import logging
import re
import sys
from pathlib import Path
from google import genai
from google.genai.types import HttpOptions
from google.genai import types

from rank_bm25 import BM25Okapi
from kiwipiepy import Kiwi

from app.config import (
    ANALYSIS_FINAL_MODEL,
    ANALYSIS_MODEL,
    GOOGLE_CLOUD_PROJECT,
    VERTEX_LOCATION,
)

# =====================================================
# CONFIG
# =====================================================

PROJECT_ID = GOOGLE_CLOUD_PROJECT
LOCATION = VERTEX_LOCATION

logger = logging.getLogger(__name__)

ACCIDENT_COLLECTION = "accident_case_full"

BM25_TOP_K = 10
FINAL_TOP_K = 5

SCRIPT_DIR = Path(__file__).resolve().parent
CHROMA_PATH = str(SCRIPT_DIR / "chroma_db")

kiwi = Kiwi()
# =====================================================
# Vertex AI
# =====================================================

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)


# =====================================================
# Gemini Vision
# =====================================================

vision_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",
    http_options=HttpOptions(
        api_version="v1"
    )
)
# =====================================================
# Gemini Multimodal Client
# =====================================================

multimodal_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global"
)



STOPWORDS = {
    "제",
    "조",
    "항",
    "호",
    "및",
    "또는",
    "등"
}

def tokenize(text):
    return [
        token.form
        for token
        in kiwi.tokenize(text)
        if (
            len(token.form) > 1
            and token.form not in STOPWORDS
        )
    ]
# =====================================================
# Vision Analysis
# =====================================================

def analyze_image(image_path):

    with open(image_path, "rb") as f:

        image_bytes = f.read()

    prompt = """
당신은 산업 안전 사고 검색 시스템이다.

이미지를 분석해서 아래 JSON schema만 출력하라.

{
  "hazard_description": [
    "위험 상황 설명"
  ],
  "hazard_keywords": [
    "핵심 위험 키워드"
  ]
}

규칙:

- hazard_description
  - 검색에 유리하도록 작성
  - 2~5개 생성

- hazard_keywords
  - 위험 상황을 직접 설명하는 keyword 추출
  - 일반적인 안전관리 용어 제외
  - 5~10개 생성

- JSON 외 텍스트 출력 금지
"""

    response = vision_client.models.generate_content(

        model=ANALYSIS_MODEL,

        contents=[

            prompt,

            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],

        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
            response_mime_type="application/json"
        )
    )

    return json.loads(
        response.text
    )


# =====================================================
# Chroma
# =====================================================

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

accident_collection = client.get_collection(
    ACCIDENT_COLLECTION
)



# IMAGE analysis is executed from run_analysis(image_path) below.
# =====================================================
# VECTOR SEARCH
# =====================================================



# =====================================================
# BM25 BUILD
# =====================================================

accident_docs = None
accident_meta = None
accident_bm25 = None


def build_bm25_corpus():
    global accident_docs
    global accident_meta
    global accident_bm25

    if accident_bm25 is not None:
        return

    logger.info("BM25 말뭉치 로딩")

    # ---------- Accident ----------

    accident_data = accident_collection.get(

        include=[
            "documents",
            "metadatas"
        ]
    )

    accident_docs = accident_data["documents"]
    accident_meta = accident_data["metadatas"]

    accident_tokens = [

        tokenize(doc)

        for doc in accident_docs

    ]

    accident_bm25 = BM25Okapi(
        accident_tokens
    )

# =====================================================
# BM25 SEARCH
# =====================================================

def bm25_search_accident(query):

    scores = accident_bm25.get_scores(
        tokenize(query)
    )

    ranked = sorted(

        zip(
            scores,
            accident_docs,
            accident_meta
        ),

        key=lambda x: x[0],

        reverse=True
    )

    output = []

    for score, doc, meta in ranked[:BM25_TOP_K]:

        output.append({

            "id":
                meta["filename"],

            "document":
                doc,

            "metadata":
                meta

        })

    return output


def bm25_search_law(query):
    from app.rag.law_rag import search_articles

    return [
        {
            "id": article["id"],
            "document": article["text"],
            "metadata": article,
        }
        for article in search_articles(query, top_k=BM25_TOP_K)
    ]


# =====================================================
# GEMINI RERANK
# =====================================================
def rerank_accident_cases(
    image_path,
    vision_output,
    candidates,
    top_k=FINAL_TOP_K

):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    candidates_text = []

    for idx, item in enumerate(

        candidates,
        start=1

    ):

        meta = item["metadata"]
        doc = item["document"]

        candidates_text.append(
            f"""
[{idx}]

파일명:
{meta.get("filename","")}

산업군:
{meta.get("industry","")}

내용:
{doc[:500]}
"""
        )

    prompt = f"""
당신은 산업안전 전문가이다.

이미지와 vision_output을 함께 분석하여 종합적으로 고려하여 가장 유사한 사고사례 5개를 선택하라.
현재 위험상황과 가장 유사한 사고사례를 관련도 순으로 재정렬하라.

현재 위험상황:

{json.dumps(
    vision_output,
    ensure_ascii=False,
    indent=2
)}

후보 사고사례:

{''.join(candidates_text)}


판단 기준

1. 사고유형 일치
2. 위험행동 일치
3. 위험설비 일치 
4. 위험환경 일치

- 특정 키워드 하나에 집중하지 말고, 전체 작업 상황에서 가장 직접적으로 발생 가능한 사고사례를 우선 선택하라.
- 반드시 JSON 형식으로 출력할 것.

{{
  "selected":[1,5,2,8,3]
}}
"""

    response = vision_client.models.generate_content(

        model=ANALYSIS_MODEL,

        contents=[ 
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],

        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
            response_mime_type="application/json"
        )
    )

    try:

        response_text = (
            response.text
            .replace("```json","")
            .replace("```","")
            .strip()
        )

        match = re.search(
            r"\{[\s\S]*\}",
            response_text
        )

        if not match:
            raise ValueError(
                "JSON not found"
            )

        result = json.loads(
            match.group()
        )

    except Exception:

        logger.warning("사고사례 재순위 응답 파싱 실패, BM25 순서 사용: %s", (response.text or "")[:500])

        return candidates[:top_k]
    
    selected = result.get("selected", [])

    if len(selected) == 0:
        return candidates[:top_k]
    
    valid_selected = []

    for idx in selected:

        if (
            1 <= idx <= len(candidates)
            and idx not in valid_selected
        ):
            valid_selected.append(idx)

    reranked = [
        candidates[i-1]
        for i in valid_selected[:top_k]
    ]

    return reranked


def rerank_law_cases(
    image_path,
    vision_output,
    candidates,
    top_k=FINAL_TOP_K

):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    candidates_text = []

    for idx, item in enumerate(

        candidates,
        start=1

    ):

        meta = item["metadata"]
        doc = item["document"]

        candidates_text.append(
            f"""
[{idx}]

조항:
{meta.get("article","")}

내용:
{doc[:500]}
"""
        )

    prompt = f"""
당신은 산업안전보건기준에 관한 규칙 전문가이다.

이미지와 vision_output을 함께 분석하여 현재 위험상황에 가장 관련성이 높은 법령 5개를 선택하라.

현재 위험상황:

{json.dumps(
    vision_output,
    ensure_ascii=False,
    indent=2
)}

후보 법령:

{''.join(candidates_text)}

판단 기준

1. 설비 일치
2. 작업유형 일치
3. 사고유형 일치
4. 예방조치 일치

- 반드시 JSON 형식으로 출력할 것.

{{
  "selected":[4,1,2,8,3]
}}
"""

    response = vision_client.models.generate_content(

        model=ANALYSIS_MODEL,

        contents=[ 
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW),
            response_mime_type="application/json"
        )
    )

    try:

        response_text = (
            response.text
            .replace("```json","")
            .replace("```","")
            .strip()
        )

        match = re.search(
            r"\{[\s\S]*\}",
            response_text
        )

        if not match:
            raise ValueError(
                "JSON not found"
            )

        result = json.loads(
            match.group()
        )

    except Exception:

        logger.warning("법령 재순위 응답 파싱 실패, BM25 순서 사용: %s", (response.text or "")[:500])

        return candidates[:top_k]
    
    selected = result.get("selected", [])

    if len(selected) == 0:
        return candidates[:top_k]
    
    valid_selected = []

    for idx in selected:
        if (
            1 <= idx <= len(candidates)
            and idx not in valid_selected
        ):
            valid_selected.append(idx)
    reranked = [

        candidates[i-1]
        for i in valid_selected[:top_k]
    ]

    return reranked

# =====================================================
# PRINT
# =====================================================

def log_results(title, results, is_law=False):
    """검색 결과를 디버그 로그로 남긴다 (LOG_LEVEL=DEBUG 일 때만 출력)."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    lines = [f"===== {title} ====="]
    for rank, item in enumerate(results, start=1):
        meta = item["metadata"]
        label = f"ARTICLE : {meta['article']}" if is_law else f"FILENAME : {meta['filename']}"
        lines.append(f"--- TOP {rank} | {label}\n{item['document'][:500]}")
    logger.debug("\n".join(lines))


def build_context(
    accident_results,
    law_results
):

    contexts = []

    # =============================================
    # Accident Cases (Full Case)
    # =============================================

    for item in accident_results:

        doc = item["document"]
        meta = item["metadata"]
    
        context = f"""
[유사 사고사례]

파일명:
{meta.get("filename", "")}

산업군:
{meta.get("industry", "")}

내용:
{doc}
"""

        contexts.append(context)

    # =============================================
    # Laws
    # =============================================

    for item in law_results:

        doc = item["document"]
        meta = item["metadata"]

        context = f"""
[관련 법령]

조항:
{meta.get("article", "")}

내용:
{doc}
"""

        contexts.append(context)

    return "\n\n".join(contexts)

def generate_final_response(
    image_path,
    vision_output,
    context
):

    json_schema = """
{
  "hazards": ["주요 위험요소"],
  "accidents": ["발생 가능한 사고"],
  "preventions": ["예방대책"],
  "related_laws": [{
    "article": "조항명",
    "content": "내용"}],
  "work_name": "사진에서 추정되는 작업명 (예: 지게차 화물 운반 작업)",
  "work_content": "사진에서 확인되는 작업내용 한 문장",
  "tbm_risks": [{
    "hazard": "TBM 회의록에 기재할 잠재위험요인",
    "measure": "해당 위험요인에 대응하는 대책"}],
  "key_risk": {
    "index": 1,
    "reason": "중점위험으로 선정한 이유",
    "measure": "중점위험요인에 대한 핵심 대책"}
}
"""


    prompt = f"""
당신은 산업안전 전문가이다.

========================
VISION ANALYSIS
========================

{json.dumps(
    vision_output,
    ensure_ascii=False,
    indent=2
)}

========================
RAG CONTEXT
========================

{context}

========================
TASK
========================

입력 이미지를 분석하여 다음 내용을 도출하라.

1. 주요 위험요소
2. 발생 가능한 아차사고(Near Miss)
3. 예방대책
4. 관련 법령

아차사고(Near Miss)는 실제 사고로 이어지지는 않았지만,
현재 상황에서 사고가 발생할 수 있었던 위험한 순간을 의미한다.

## 주의사항
- 이미지를 최우선으로 판단
- 발생 가능한 사고는 아차사고(Near Miss) 관점에서 작성할 것.
- 사고사례 RAG CONTEXT 는 발생 가능한 아차사고(accidents)와 예방대책 (preventions)을 도출하는 참고자료로 활용할 것.
- 법령은 반드시 RAG CONTEXT 내 법령만 사용할 것.
- 관련성이 높은 법령을 최대 5개까지 출력하라.

## TBM(작업 전 안전점검회의) 회의록 항목
- tbm_risks: 주요 위험요소(hazards) 중 중요한 순서로 최대 3개를 골라, 각 위험요인과 1:1로 대응하는 대책을 짝지어 작성할 것.
  주요 위험요소가 3개 미만이면 그 개수만큼만 작성하고, hazards에 없는 위험요인을 새로 만들지 말 것.
- 대책은 제거 → 대체 → 통제(공학적·관리적 대책, 보호구) 순서를 고려하여 가장 근본적인 대책을 우선할 것.
- key_risk: tbm_risks 중 중상해 이상의 산업재해로 이어질 가능성이 가장 높은 중점위험 1개를 선정하고,
  index는 tbm_risks 내 순번(1부터 시작)으로 기재할 것.
- work_name, work_content는 이미지에서 확인 가능한 작업 기준으로 간결하게 작성하고, 판단이 어려우면 빈 문자열로 둘 것.

반드시 아래 JSON 형식으로만 출력하라.

{json_schema}

"""

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = multimodal_client.models.generate_content(

        model=ANALYSIS_FINAL_MODEL,

        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            ),
        ],

        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    return response.text


def parse_final_response(response_text):
    cleaned_text = (
        response_text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    match = re.search(
        r"\{[\s\S]*\}",
        cleaned_text
    )

    if not match:
        raise ValueError(
            "JSON not found"
        )

    return json.loads(
        match.group()
    )


def run_analysis(image_path, *, retrieval_trace=None):
    image_path = str(image_path)

    vision_output = analyze_image(
        image_path
    )

    logger.debug("VISION OUTPUT\n%s", json.dumps(vision_output, ensure_ascii=False, indent=2))

    descriptions = "\n".join(
        vision_output["hazard_description"]
    )

    keywords = ", ".join(
        vision_output["hazard_keywords"]
    )

    query = f"""
hazard_description:
{descriptions}

hazard_keywords:
{keywords}
"""

    tokens = tokenize(query)
    logger.debug("QUERY\n%s\nBM25 TOKENS (%d): %s", query, len(tokens), tokens)

    build_bm25_corpus()

    acc_bm25 = bm25_search_accident(query)

    acc_rerank = rerank_accident_cases(
        image_path,
        vision_output,
        acc_bm25,
    )

    log_results(
        "ACCIDENT - BM25",
        acc_bm25
    )
    log_results(
        "ACCIDENT - RERANK",
        acc_rerank
    )

    law_bm25 = bm25_search_law(query)

    law_rerank = rerank_law_cases(
        image_path,
        vision_output,
        law_bm25,
    )

    if retrieval_trace is not None:
        retrieval_trace["candidates"] = [item["id"] for item in law_bm25]
        retrieval_trace["reranked"] = [item["id"] for item in law_rerank]

    log_results(
        "LAW - BM25",
        law_bm25,
        True
    )

    log_results(
        "LAW - RERANK",
        law_rerank,
        True
    )

    context = build_context(
        acc_rerank,
        law_rerank
    )

    final_response = generate_final_response(
        image_path,
        vision_output,
        context
    )

    logger.debug("FINAL RESPONSE\n%s", final_response)

    return parse_final_response(
        final_response
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    logger.setLevel(logging.DEBUG)  # CLI 실행 시에는 중간 결과까지 출력
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.ai.scripts.main <image_path>  (프로젝트 루트에서 실행)")

    print(
        json.dumps(
            run_analysis(sys.argv[1]),
            ensure_ascii=False,
            indent=2
        )
    )
