import json
import chromadb
import vertexai

from google import genai
from google.genai.types import HttpOptions
from google.genai import types

from vertexai.language_models import TextEmbeddingModel


# =====================================================
# CONFIG
# =====================================================

PROJECT_ID = "kun-kgp-mytnt831"
LOCATION = "us-central1"

CHROMA_PATH = "./chroma_db"

IMAGE_PATH = "image/추락.jpg"


# =====================================================
# Vertex AI Init
# =====================================================

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)


# =====================================================
# Embedding Model
# =====================================================

embedding_model = TextEmbeddingModel.from_pretrained(
    "text-embedding-005"
)


# =====================================================
# Gemini Vision Client
# =====================================================

vision_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global",
    http_options=HttpOptions(api_version="v1")
)


# =====================================================
# Gemini Multimodal Client
# =====================================================

multimodal_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location="global"
)


# =====================================================
# ChromaDB
# =====================================================

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

# 법령 DB
kosha_collection = client.get_collection(
    "kosha_rag_v2"
)

# Full Case DB
accident_collection = client.get_collection(
    "accident_case_full"
)


# =====================================================
# Embedding
# =====================================================

def get_embedding(text):

    return embedding_model.get_embeddings(
        [text]
    )[0].values


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
            ),
        ],

        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        ),
    )

    return json.loads(response.text)


# =====================================================
# Query Build
# =====================================================

def build_query(vision_output):

    descriptions = "\n".join(
        vision_output["hazard_description"]
    )

    keywords = ", ".join(
        vision_output["hazard_keywords"]
    )

    return f"""
hazard_description:
{descriptions}

hazard_keywords:
{keywords}
"""


# =====================================================
# Accident Retrieval
# =====================================================

def retrieve_accident_cases(
    query,
    top_k=10
):

    query_embedding = get_embedding(query)

    return accident_collection.query(

        query_embeddings=[
            query_embedding
        ],

        n_results=top_k
    )


# =====================================================
# Law Retrieval
# =====================================================

def retrieve_laws(
    query,
    top_k=2
):

    query_embedding = get_embedding(query)

    return kosha_collection.query(

        query_embeddings=[
            query_embedding
        ],

        n_results=top_k,

        where={
            "source": "law"
        }
    )

# =====================================================
# Accident Reranking
# =====================================================

def rerank_accident_cases(

    vision_output,

    accident_candidates,

    top_k=3

):

    candidates_text = []

    for idx, (doc, meta) in enumerate(

        zip(

            accident_candidates["documents"][0],

            accident_candidates["metadatas"][0]

        ),

        start=1

    ):

        candidates_text.append(
            f"""
[{idx}]

파일명:
{meta.get("filename", "")}

산업군:
{meta.get("industry", "")}

내용:
{doc[:800]}
"""
        )

    prompt = f"""
당신은 산업안전 전문가이다.

현재 이미지 위험정보:

{json.dumps(
    vision_output,
    ensure_ascii=False,
    indent=2
)}

후보 사고사례:

{''.join(candidates_text)}

현재 위험상황과 가장 유사한 사고사례 {top_k}개를 선택하라.

판단 기준:

1. 사고유형 일치
2. 위험설비 일치
3. 위험행동 일치
4. 재해형태(추락, 끼임, 충돌 등) 일치

반드시 JSON만 출력

예시:

{{
  "selected": [3, 8, 10]
}}
"""

    response = vision_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt

    )

    response_text = response.text.strip()

    response_text = response_text.replace(
        "```json",
        ""
    )

    response_text = response_text.replace(
        "```",
        ""
    )

    result = json.loads(
        response_text
    )

    selected = result["selected"]

    reranked_docs = []
    reranked_meta = []

    for idx in selected:

        reranked_docs.append(

            accident_candidates["documents"][0][idx - 1]

        )

        reranked_meta.append(

            accident_candidates["metadatas"][0][idx - 1]

        )

    return {

        "documents": [reranked_docs],

        "metadatas": [reranked_meta]

    }

# =====================================================
# Context Builder
# =====================================================

def build_context(
    accident_results,
    law_results
):

    contexts = []

    # =============================================
    # Accident Cases (Full Case)
    # =============================================

    for doc, meta in zip(
        accident_results["documents"][0],
        accident_results["metadatas"][0]
    ):

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

    for doc, meta in zip(
        law_results["documents"][0],
        law_results["metadatas"][0]
    ):

        context = f"""
[관련 법령]

조항:
{meta.get("article", "")}

내용:
{doc}
"""

        contexts.append(context)

    return "\n\n".join(contexts)


# =====================================================
# Final Generation
# =====================================================

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


# =====================================================
# Pipeline
# =====================================================

def run_pipeline(image_path):

    print("=" * 50)
    print("STEP 1: VISION")
    print("=" * 50)

    vision_output = analyze_image(
        image_path
    )

    print(
        json.dumps(
            vision_output,
            ensure_ascii=False,
            indent=2
        )
    )

    print("\n")
    print("=" * 50)
    print("STEP 2: QUERY")
    print("=" * 50)

    query = build_query(
        vision_output
    )

    print(query)

    print("\n")
    print("=" * 50)
    print("STEP 3: RETRIEVAL")
    print("=" * 50)

    accident_candidates = retrieve_accident_cases(    
        query,
        top_k=10
    )
    
    accident_results = rerank_accident_cases(
        vision_output,
        accident_candidates,
        top_k=3
    
    )
    
    law_results = retrieve_laws(
        query
    )

    print("\n[RERANKED ACCIDENT CASES]")

    print("\n")
    print("=" * 50)
    print("STEP 3-1: RERANK")
    print("=" * 50)

    for i, doc in enumerate(
        accident_results["documents"][0]
    ):

        print(f"\nTOP {i+1}")

        print(
            accident_results["metadatas"][0][i]
        )

        print(doc[:1000])

    print("\n[LAWS]")

    for i, doc in enumerate(
        law_results["documents"][0]
    ):

        print(f"\nTOP {i+1}")

        print(
            law_results["metadatas"][0][i]
        )

        print(doc[:1000])

    print("\n")
    print("=" * 50)
    print("STEP 4: CONTEXT")
    print("=" * 50)

    context = build_context(
        accident_results,
        law_results
    )

    print(context[:3000])

    print("\n")
    print("=" * 50)
    print("STEP 5: FINAL GENERATION")
    print("=" * 50)

    return generate_final_response(
        image_path,
        vision_output,
        context
    )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    response = run_pipeline(
        IMAGE_PATH
    )

    print("\n")
    print("=" * 50)
    print("FINAL RESPONSE")
    print("=" * 50)

    print(response)