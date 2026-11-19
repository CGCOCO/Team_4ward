"""
개발용 목업 RAG. 실제 조문 10개(mock_articles.json)를 글자 bigram 겹침으로 검색한다.
실제 RAG 가 준비되면 RAG_BACKEND 환경변수로 교체한다.
"""

import json
from pathlib import Path

from app.rag.interface import LawArticle

_ARTICLES: list[dict] = json.loads(
    (Path(__file__).with_name("mock_articles.json")).read_text(encoding="utf-8")
)
_BY_ID = {article["id"]: article for article in _ARTICLES}


def _bigrams(text: str) -> set[str]:
    compact = "".join(text.split())
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def search_laws(query: str, top_k: int = 6) -> list[LawArticle]:
    query_grams = _bigrams(query)
    if not query_grams:
        return []

    scored = []
    for article in _ARTICLES:
        # 제목 겹침에 가중치를 더 준다
        title_grams = _bigrams(article["law_title"] + article["heading"])
        body_grams = _bigrams(article["text"])
        score = 3 * len(query_grams & title_grams) + len(query_grams & body_grams)
        if score > 0:
            scored.append({**article, "score": float(score)})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def get_article(article_id: str) -> LawArticle | None:
    article = _BY_ID.get(article_id)
    return {**article, "score": 0.0} if article else None
