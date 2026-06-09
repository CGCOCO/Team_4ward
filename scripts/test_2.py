import chromadb
import vertexai
import json
import re
from pathlib import Path
from google import genai
from google.genai.types import HttpOptions
from google.genai import types

from rank_bm25 import BM25Okapi
from kiwipiepy import Kiwi
import builtins


# =====================================================
# CONFIG
# =====================================================

PROJECT_ID = "kun-kgp-mytnt831"
LOCATION = "us-central1"

ACCIDENT_COLLECTION = "accident_case_full"
LAW_COLLECTION = "kosha_rag_v2"

BM25_TOP_K = 10
FINAL_TOP_K = 5

CHROMA_PATH = "./chroma_db"

kiwi = Kiwi()
_original_print = builtins.print
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
def print(*args, **kwargs):

    text = " ".join(
        str(arg)
        for arg in args
    )

    log_file.write(text + "\n")
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

        model="gemini-3.1-flash-lite",

        contents=[

            prompt,

            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],

        config=types.GenerateContentConfig(
            temperature=0.0,
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

law_collection = client.get_collection(
    LAW_COLLECTION
)


# =====================================================
# IMAGE
# =====================================================

IMAGE_PATH = "image/전도.jpg"
image_name = Path(IMAGE_PATH).stem

Path("results").mkdir(exist_ok=True)

LOG_FILE = f"results/{image_name}.txt"

log_file = open(
    LOG_FILE,
    "w",
    encoding="utf-8"
)

vision_output = analyze_image(
    IMAGE_PATH
)

print("\n")
print("=" * 100)
print("VISION OUTPUT")
print("=" * 100)

print(
    json.dumps(
        vision_output,
        ensure_ascii=False,
        indent=2
    )
)

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

print("\n")
print("=" * 100)
print("QUERY")
print("=" * 100)

print(query)


# bm25가 어떤 토큰을 사용하는지 확인하기
print("\n")
print("=" * 100)
print("BM25 TOKENS")
print("=" * 100)

print(
    tokenize(query)
)

print("\n")
print("=" * 100)
print("TOKEN COUNT")
print("=" * 100)

print(
    len(tokenize(query))
)
# =====================================================
# VECTOR SEARCH
# =====================================================



# =====================================================
# BM25 BUILD
# =====================================================

print("Loading BM25 corpus...")


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


# ---------- Law ----------

law_data = law_collection.get(

    where={
        "source": "law"
    },

    include=[
        "documents",
        "metadatas"
    ]
)

law_docs = law_data["documents"]
law_meta = law_data["metadatas"]

law_tokens = [

    tokenize(doc)

    for doc in law_docs

]

law_bm25 = BM25Okapi(
    law_tokens
)


# =====================================================
# BM25 SEARCH
# =====================================================

def bm25_search_accident():

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


def bm25_search_law():

    scores = law_bm25.get_scores(
        tokenize(query)
    )

    ranked = sorted(

        zip(
            scores,
            law_docs,
            law_meta
        ),

        key=lambda x: x[0],

        reverse=True
    )

    output = []

    for score, doc, meta in ranked[:BM25_TOP_K]:

        output.append({

            "id":
                meta["article"],

            "document":
                doc,

            "metadata":
                meta

        })

    return output



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

        model="gemini-3.1-flash-lite",

        contents=[ 
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],

        config=types.GenerateContentConfig(
            temperature=0.0,
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

        print("ACCIDENT RERANK ERROR")
        print(response.text)

        return candidates[:top_k]
    
    selected = result.get("selected", [])

    if len(selected) == 0:
        return candidates[:top_k]
    
    valid_selected = []

    for idx in selected:

        if 1 <= idx <= len(candidates):

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

        model="gemini-3.1-flash-lite",

        contents=[ 
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.0,
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

        print("LAW RERANK ERROR")
        print(response.text)

        return candidates[:top_k]
    
    selected = result.get("selected", [])

    if len(selected) == 0:
        return candidates[:top_k]
    
    valid_selected = []

    for idx in selected:
        if 1 <= idx <= len(candidates):

            valid_selected.append(idx)
    reranked = [

        candidates[i-1]
        for i in valid_selected[:top_k]
    ]

    return reranked

# =====================================================
# PRINT
# =====================================================

def print_results(

    title,
    results,
    is_law=False

):

    print("\n")
    print("=" * 100)
    print(title)
    print("=" * 100)

    for rank, item in enumerate(

        results,

        start=1

    ):

        meta = item["metadata"]

        print("\n")
        print("-" * 80)

        print(
            f"TOP {rank}"
        )

        if is_law:

            print(
                f"ARTICLE : {meta['article']}"
            )

        else:

            print(
                f"FILENAME : {meta['filename']}"
            )

        print()

        print(
            item["document"][:500]
        )


# =====================================================
# ACCIDENT
# =====================================================


acc_bm25 = bm25_search_accident()

acc_rerank = rerank_accident_cases(
    IMAGE_PATH,
    vision_output,
    acc_bm25,
)

print_results(

    "ACCIDENT - BM25",

    acc_bm25
)
print_results(

    "ACCIDENT - RERANK",

    acc_rerank
)


# =====================================================
# LAW
# =====================================================


law_bm25 = bm25_search_law()


law_rerank = rerank_law_cases(
    IMAGE_PATH,
    vision_output,
    law_bm25,
)

print_results(

    "LAW - BM25",

    law_bm25,

    True
)

print_results(

    "LAW - RERANK",

    law_rerank,

    True
)



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

입력 이미지를 분석하여

1. 주요 위험요소
2. 발생 가능한 사고
3. 필요한 안전조치
4. 예방대책
5. 관련 법령

을 설명하라.

주의:

- 이미지를 최우선으로 판단
- 사고사례는 참고자료
- 법령은 반드시 RAG CONTEXT 내 법령만 사용
"""

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = multimodal_client.models.generate_content(

        model="gemini-3.5-flash",

        contents=[
            prompt,

            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg"
            ),
        ]
    )

    return response.text

context = build_context(
    acc_rerank,
    law_rerank
)

final_response = generate_final_response(
    IMAGE_PATH,
    vision_output,
    context
)

print("\n")
print("=" * 100)
print("FINAL RESPONSE")
print("=" * 100)

print(final_response)

log_file.close()

_original_print(
    f"Logs saved to {LOG_FILE}"
)
