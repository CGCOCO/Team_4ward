"""
AI 어드바이저 <-> 법령 RAG 인터페이스 (계약)

RAG 담당은 아래 두 함수를 가진 모듈을 구현하고, 환경변수 RAG_BACKEND 로 선택한다.
  - RAG_BACKEND=mock (기본값) : app.rag.mock_rag
  - RAG_BACKEND=<모듈경로>     : 예) app.rag.law_rag

규칙
  - 필드명은 LawArticle 그대로 유지한다.
  - text 는 조문 원문(항·호·목 포함) 또는 별표 원문을 가공 없이 넣는다.
    별표 근거는 article 필드에 "별표 4"처럼 표시한다.
  - search_laws 는 대화 맥락이 반영된 "독립된 한 문장 질의"를 받는다.
  - 동시 요청에 안전해야 한다(모듈 전역변수에 질의 상태 저장 금지).
  - 결과가 없으면 빈 리스트 / None 을 반환한다. 예외를 던지지 않는다.
"""

import importlib
import os
from functools import lru_cache
from typing import Protocol, TypedDict


class LawArticle(TypedDict):
    id: str          # 조문 고유 ID, 예: "산업안전보건법-17", "안전보건규칙-42"
    law_title: str   # 예: "산업안전보건법 시행령"
    article: str     # 예: "제16조"
    heading: str     # 예: "안전관리자의 선임 등"
    text: str        # 조문 원문
    url: str         # law.go.kr 링크
    score: float     # 검색 점수 (높을수록 관련)


class LawRAG(Protocol):
    def search_laws(self, query: str, top_k: int = 6) -> list[LawArticle]: ...

    def get_article(self, article_id: str) -> LawArticle | None: ...


@lru_cache(maxsize=1)
def get_rag() -> LawRAG:
    backend = os.getenv("RAG_BACKEND", "mock")
    module_path = "app.rag.mock_rag" if backend == "mock" else backend
    return importlib.import_module(module_path)
