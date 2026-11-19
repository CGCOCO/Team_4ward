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
DECREE_DATA_PATH = LAW_DATA_PATH.with_name("occupationalSafetyAndHealthDecree.json")
ENFORCEMENT_RULE_DATA_PATH = LAW_DATA_PATH.with_name("occupationalSafetyAndHealthEnforcementRule.json")
ACT_ALIAS = r"(?:산업\s*안전\s*보건\s*법|산안법)"
LAW_NAME = re.compile(
    rf"(?P<decree>{ACT_ALIAS}\s*시행령)|"
    rf"(?P<enforcement_rule>{ACT_ALIAS}\s*시행규칙)|"
    rf"(?P<act>{ACT_ALIAS})|"
    r"(?P<safety_rule>산업\s*안전\s*보건\s*기준\s*에\s*관한\s*규칙|안전보건규칙)"
)
ARTICLE_REFERENCE = re.compile(r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?")
PARENT_ACT_REFERENCE = re.compile(r"(?:^|[\s(])법\s+" + ARTICLE_REFERENCE.pattern)
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


def _linked_appendices(text, appendices):
    return tuple(dict.fromkeys(
        label
        for match in APPENDIX_REFERENCE.finditer(text)
        if not EXTERNAL_LAW_SUFFIX.search(text[max(0, match.start() - 12):match.start()])
        if (label := _appendix_label(match[1], match[2])) in appendices
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
_DECREE_ARTICLES, _DECREE_APPENDICES = _load_articles(DECREE_DATA_PATH)
_ENFORCEMENT_RULE_ARTICLES, _ = _load_articles(ENFORCEMENT_RULE_DATA_PATH)
_LAW_ARTICLES = {
    "safety_rule": _ARTICLES,
    "act": _ACT_ARTICLES,
    "decree": _DECREE_ARTICLES,
    "enforcement_rule": _ENFORCEMENT_RULE_ARTICLES,
}
_LAW_APPENDICES = {"safety_rule": _APPENDICES, "decree": _DECREE_APPENDICES}
_APPENDIX_ROWS = {
    row["id"]: row for appendices in _LAW_APPENDICES.values() for row in appendices.values()
}
_ARTICLE_LAWS = {
    article_id: law for law, articles in _LAW_ARTICLES.items() for article_id in articles
}
_LINKS = {
    key: tuple(appendices[label]["id"] for label in _linked_appendices(row["text"], appendices))
    for law, appendices in _LAW_APPENDICES.items()
    for key, row in _LAW_ARTICLES[law].items()
}
_ROWS = tuple(_ARTICLES.values())
_APPENDIX_TITLE_TERMS = {
    appendix_id: set(_tokenize(row["heading"].split("(")[0]))
    for appendix_id, row in _APPENDIX_ROWS.items()
}
_ADVISOR_ROWS = tuple(row for articles in _LAW_ARTICLES.values() for row in articles.values())
_SOURCES = {**{row["id"]: row for row in _ADVISOR_ROWS}, **_APPENDIX_ROWS}


def _build_index(rows):
    return BM25Okapi([_tokenize(row["text"] + "\n" + row["heading"]) for row in rows])


_INDEX = _build_index(_ROWS)
_ADVISOR_INDEX = _build_index(_ADVISOR_ROWS)
_ADVISOR_TITLE_INDEX = BM25Okapi([_tokenize(row["heading"]) for row in _ADVISOR_ROWS])
_REFERENCE_BOOST = 1 + sum(value for value in _ADVISOR_INDEX.idf.values() if value > 0)


def search_articles(query: str, top_k: int = 6) -> list[dict]:
    """Rank article candidates for the photo analysis pipeline."""
    return _rank_articles(query, top_k, _ROWS, _INDEX)


def _rank_articles(query, top_k, rows, index, laws=(), title_index=None):
    if top_k <= 0 or not query.strip():
        return []
    references = {
        f"제{int(number)}조" + (f"의{int(branch)}" if branch else "")
        for number, branch in ARTICLE_REFERENCE.findall(query)
    }
    keywords = list(dict.fromkeys(_tokenize(ARTICLE_REFERENCE.sub(" ", query))))
    scores = index.get_scores(keywords)
    if title_index is not None:
        scores += title_index.get_scores(keywords) * 1.5
    ranked = [
        (float(score) + (_REFERENCE_BOOST if row["article"] in references else 0), row)
        for row, score in zip(rows, scores)
        if not laws or _ARTICLE_LAWS[row["id"]] in laws
        if score > 0 or row["article"] in references
    ]
    ranked.sort(key=lambda match: match[0], reverse=True)
    return [{**row, "score": score} for score, row in ranked[:top_k]]


def search_laws(query: str, top_k: int = 6) -> list[dict]:
    """Find articles and include appendices that support the answer."""
    if top_k <= 0:
        return []
    laws = {match.lastgroup for match in LAW_NAME.finditer(query)}
    requested = dict.fromkeys(
        _appendix_label(number, branch)
        for number, branch in APPENDIX_REFERENCE.findall(query)
    )
    results = [
        {**appendices[label], "score": float(_REFERENCE_BOOST * 2)}
        for label in requested
        for law, appendices in _LAW_APPENDICES.items()
        if (not laws or law in laws) and label in appendices
    ]
    article_query = APPENDIX_REFERENCE.sub(" ", query)
    article_query = LAW_NAME.sub(" ", article_query)
    articles = _rank_articles(
        article_query, top_k, _ADVISOR_ROWS, _ADVISOR_INDEX, laws, _ADVISOR_TITLE_INDEX
    )
    query_terms = set(_tokenize(article_query))
    include_linked = not requested
    leading_rule = articles and articles[0]["id"] in _ARTICLES
    included_ids = {row["id"] for row in results}
    for article in articles:
        if article["id"] in included_ids:
            continue
        results.append(article)
        included_ids.add(article["id"])
        links = _LINKS.get(article["id"], ())
        if include_linked and links and len(results) < top_k and (
            leading_rule or article["id"] in _DECREE_ARTICLES
        ):
            related = max(links, key=lambda link: len(_APPENDIX_TITLE_TERMS[link] & query_terms))
            results.append({**_APPENDIX_ROWS[related], "score": article["score"]})
            include_linked = False
            if article["id"] in _DECREE_ARTICLES and not laws and len(results) < top_k:
                reference = PARENT_ACT_REFERENCE.search(article["text"])
                if reference:
                    number, branch = reference.groups()
                    parent_id = f"001766-{number}" + (f"-{branch}" if branch else "")
                    if parent_id in _ACT_ARTICLES and parent_id not in included_ids:
                        results.append({**_ACT_ARTICLES[parent_id], "score": article["score"]})
                        included_ids.add(parent_id)
        if len(results) >= top_k:
            break
    return results[:top_k]


def get_article(article_id: str) -> dict | None:
    """Return the original article or appendix for a citation ID."""
    article = _SOURCES.get(article_id)
    return article.copy() if article is not None else None
