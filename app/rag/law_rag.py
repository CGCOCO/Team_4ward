"""Shared search index for the bundled official law snapshot."""

import json
import re
from pathlib import Path
from urllib.parse import quote

from rank_bm25 import BM25Okapi

LAW_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "ai/scripts/forge_db/law/lawData.json"
)
ARTICLE_REFERENCE = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")
SEARCH_WORD = re.compile(r"[가-힣]{2,}|[a-z0-9]{2,}", re.IGNORECASE)


def _items(value):
    return value if isinstance(value, list) else [value] if value is not None else []


def _original_lines(node, field, children):
    for content in _items(node.get(field)):
        if isinstance(content, list):
            yield from _original_lines({field: content}, field, ())
        else:
            yield content
    if children:
        child_field, text_field, *remaining = children
        for child in _items(node.get(child_field)):
            yield from _original_lines(child, text_field, remaining)


def _load_articles():
    law = json.loads(LAW_DATA_PATH.read_text(encoding="utf-8"))["법령"]
    info = law["기본정보"]
    title = info["법령명_한글"]
    version = ",".join(info[key] for key in ("시행일자", "공포번호", "공포일자"))
    base_url = f"https://www.law.go.kr/법령/{quote(title.replace(' ', ''))}/({version})"
    articles = {}
    for node in _items(law["조문"]["조문단위"]):
        if node["조문여부"] != "조문":
            continue
        number = int(node["조문번호"])
        branch = int(node.get("조문가지번호") or 0)
        article = f"제{number}조" + (f"의{branch}" if branch else "")
        article_id = f"{info['법령ID']}-{number}" + (f"-{branch}" if branch else "")
        if article_id in articles:
            raise ValueError(f"Duplicate article ID: {article_id}")
        articles[article_id] = {
            "id": article_id,
            "law_title": title,
            "article": article,
            "heading": node.get("조문제목", ""),
            "text": "\n".join(_original_lines(
                node, "조문내용", ("항", "항내용", "호", "호내용", "목", "목내용")
            )),
            "url": f"{base_url}/{quote(article)}",
            "score": 0.0,
        }
    return articles


def _tokenize(text):
    tokens = []
    for word in SEARCH_WORD.findall(text.lower()):
        tokens.append(word)
        if "가" <= word[0] <= "힣":
            tokens.extend(f"#{word[i:i + 2]}" for i in range(len(word) - 1))
    return tokens


_ARTICLES = _load_articles()
_ROWS = tuple(_ARTICLES.values())
_INDEX = BM25Okapi([
    _tokenize(row["text"] + "\n" + row["heading"])
    for row in _ROWS
])
_REFERENCE_BOOST = 1 + sum(value for value in _INDEX.idf.values() if value > 0)


def search_laws(query: str, top_k: int = 6) -> list[dict]:
    """Search a standalone question and return scored copies of the source rows."""
    if top_k <= 0 or not query.strip():
        return []
    references = {
        f"제{int(number)}조" + (f"의{int(branch)}" if branch else "")
        for number, branch in ARTICLE_REFERENCE.findall(query)
    }
    keywords = list(dict.fromkeys(_tokenize(ARTICLE_REFERENCE.sub(" ", query))))
    scores = _INDEX.get_scores(keywords)
    ranked = [
        (float(score) + (_REFERENCE_BOOST if row["article"] in references else 0), row)
        for row, score in zip(_ROWS, scores)
        if score > 0 or row["article"] in references
    ]
    ranked.sort(key=lambda match: match[0], reverse=True)
    return [{**row, "score": score} for score, row in ranked[:top_k]]


def get_article(article_id: str) -> dict | None:
    """Return the original source row for a citation ID."""
    article = _ARTICLES.get(article_id)
    return article.copy() if article is not None else None
