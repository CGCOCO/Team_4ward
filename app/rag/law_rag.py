"""Search the bundled official law snapshots."""

import json
import re
from pathlib import Path
from urllib.parse import quote, urljoin

from rank_bm25 import BM25Okapi

LAW_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "ai/scripts/forge_db/law/lawData.json"
)
ACT_DATA_PATH = LAW_DATA_PATH.with_name("occupationalSafetyAndHealthAct.json")
ACT_NAME = re.compile(r"산업\s*안전\s*보건\s*법(?!\s*시행(?:령|규칙))|산안법")
RULE_NAME = re.compile(r"산업\s*안전\s*보건\s*기준\s*에\s*관한\s*규칙|안전보건규칙")
ARTICLE_REFERENCE = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")
APPENDIX_REFERENCE = re.compile(r"별표\s*(\d+)(?:\s*의\s*(\d+))?")
EXTERNAL_LAW_SUFFIX = re.compile(r"(?:」|시행령|시행규칙|\b영|\b규칙)\s*$")
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


def _load_articles(path):
    law = json.loads(path.read_text(encoding="utf-8"))["법령"]
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
    appendices = {}
    for node in _items(law.get("별표", {}).get("별표단위")):
        if node["별표구분"] != "별표" or node["별표제목"].startswith("삭제"):
            continue
        number = int(node["별표번호"])
        branch = int(node.get("별표가지번호") or 0)
        label = _appendix_label(str(number), str(branch) if branch else "")
        appendix_id = f"{info['법령ID']}-appendix-{node['별표키']}"
        appendices[label] = {
            "id": appendix_id,
            "law_title": title,
            "article": label,
            "heading": node["별표제목"],
            "text": "\n".join(_original_lines(node, "별표내용", ())),
            "url": urljoin("https://www.law.go.kr", node["별표서식PDF파일링크"]),
            "score": 0.0,
        }
    return articles, appendices


def _appendix_label(number, branch):
    return f"별표 {int(number)}" + (f"의{int(branch)}" if branch else "")


def _linked_appendices(text):
    return tuple(dict.fromkeys(
        label
        for match in APPENDIX_REFERENCE.finditer(text)
        if not EXTERNAL_LAW_SUFFIX.search(text[max(0, match.start() - 12):match.start()])
        if (label := _appendix_label(match[1], match[2])) in _APPENDICES
    ))


def _tokenize(text):
    tokens = []
    for word in SEARCH_WORD.findall(text.lower()):
        tokens.append(word)
        if "가" <= word[0] <= "힣":
            tokens.extend(f"#{word[i:i + 2]}" for i in range(len(word) - 1))
    return tokens


_ARTICLES, _APPENDICES = _load_articles(LAW_DATA_PATH)
_ACT_ARTICLES, _ = _load_articles(ACT_DATA_PATH)
_SOURCES = {**_ARTICLES, **_ACT_ARTICLES, **{row["id"]: row for row in _APPENDICES.values()}}
_LINKS = {key: _linked_appendices(row["text"]) for key, row in _ARTICLES.items()}
_ROWS = tuple(_ARTICLES.values())
_APPENDIX_TITLE_TERMS = {
    label: set(_tokenize(row["heading"].split("(")[0]))
    for label, row in _APPENDICES.items()
}
_ADVISOR_ROWS = (*_ROWS, *_ACT_ARTICLES.values())


def _build_index(rows):
    return BM25Okapi([_tokenize(row["text"] + "\n" + row["heading"]) for row in rows])


_INDEX = _build_index(_ROWS)
_ADVISOR_INDEX = _build_index(_ADVISOR_ROWS)
_REFERENCE_BOOST = 1 + sum(value for value in _ADVISOR_INDEX.idf.values() if value > 0)


def search_articles(query: str, top_k: int = 6) -> list[dict]:
    """Rank article candidates for the photo analysis pipeline."""
    return _rank_articles(query, top_k, _ROWS, _INDEX)


def _rank_articles(query, top_k, rows, index, act_only=False, rule_only=False):
    if top_k <= 0 or not query.strip():
        return []
    references = {
        f"제{int(number)}조" + (f"의{int(branch)}" if branch else "")
        for number, branch in ARTICLE_REFERENCE.findall(query)
    }
    keywords = list(dict.fromkeys(_tokenize(ARTICLE_REFERENCE.sub(" ", query))))
    scores = index.get_scores(keywords)
    ranked = [
        (float(score) + (_REFERENCE_BOOST if row["article"] in references else 0), row)
        for row, score in zip(rows, scores)
        if not act_only or row["id"] in _ACT_ARTICLES
        if not rule_only or row["id"] in _ARTICLES
        if score > 0 or row["article"] in references
    ]
    ranked.sort(key=lambda match: match[0], reverse=True)
    return [{**row, "score": score} for score, row in ranked[:top_k]]


def search_laws(query: str, top_k: int = 6) -> list[dict]:
    """Find articles and include appendices that support the answer."""
    if top_k <= 0:
        return []
    mentions_act = bool(ACT_NAME.search(query))
    mentions_rule = bool(RULE_NAME.search(query))
    act_only = mentions_act and not mentions_rule
    rule_only = mentions_rule and not mentions_act
    requested = dict.fromkeys(
        _appendix_label(number, branch)
        for number, branch in APPENDIX_REFERENCE.findall(query)
    )
    results = [
        {**_APPENDICES[label], "score": float(_REFERENCE_BOOST * 2)}
        for label in requested if label in _APPENDICES and not act_only
    ]
    article_query = APPENDIX_REFERENCE.sub(" ", query)
    article_query = ACT_NAME.sub(" ", RULE_NAME.sub(" ", article_query))
    articles = _rank_articles(
        article_query, top_k, _ADVISOR_ROWS, _ADVISOR_INDEX,
        act_only=act_only, rule_only=rule_only,
    )
    query_terms = set(_tokenize(article_query))
    # Expand rule appendices only when the rule leads the article results.
    include_linked = not requested and articles and articles[0]["id"] in _ARTICLES
    for article in articles:
        results.append(article)
        links = _LINKS.get(article["id"], ())
        if include_linked and links and len(results) < top_k:
            label = max(links, key=lambda link: len(_APPENDIX_TITLE_TERMS[link] & query_terms))
            results.append({**_APPENDICES[label], "score": article["score"]})
            include_linked = False
        if len(results) >= top_k:
            break
    return results[:top_k]


def get_article(article_id: str) -> dict | None:
    """Return the original article or appendix for a citation ID."""
    article = _SOURCES.get(article_id)
    return article.copy() if article is not None else None
