import json
from google import genai
from google.genai.types import HttpOptions
from google.genai import types

client = genai.Client(
    vertexai=True,
    project="kun-kgp-mytnt831",
    location="global",
    http_options=HttpOptions(api_version="v1")
)

IMAGE_PATH = "bodo.jpg"

with open(IMAGE_PATH, "rb") as f:
    image_bytes = f.read()

PROMPT = """
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
- hazard_description:
  - 검색에 유리하도록 구체적으로 작성
  - 2~5개 생성
  - 산업안전 표현 사용

- hazard_keywords:
  - 핵심 위험 요소 keyword 추출
  - noun 중심
  - 5~15개 생성

- JSON 외 텍스트 출력 금지
"""

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=[
        PROMPT,
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg",
        ),
    ],
    config=types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
    ),
)

result = json.loads(response.text)
print(json.dumps(result, indent=2, ensure_ascii=False))