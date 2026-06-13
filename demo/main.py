import base64
import json
from openai import OpenAI

# 로컬에 띄운 vLLM 서버 엔드포인트 연결
client = OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:8000/v1"
)

def encode_image(image_path):
    """로컬 이미지를 Base64 포맷으로 인코딩합니다."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# 테스트할 아차사고 사진 경로 지정
image_path = "/home/xeong_oxx/test/image/bodo.jfif"
try:
    base64_image = encode_image(image_path)
except FileNotFoundError:
    print(f"❌ 오류: '{image_path}' 파일을 찾을 수 없습니다.")
    exit(1)

print("Qwen3.5-9B 모델에 이미지 분석을 요청합니다. (처리 중...)\n")

# API 호출
response = client.chat.completions.create(
    model="Qwen/Qwen3.5-9B",
    messages=[
        {
            "role": "system",
            "content": "너는 산업/생활 안전 분석 시스템 API야. 사용자의 요청에 대해 어떠한 인사말이나 부연 설명 없이, 오직 요청한 JSON 형식의 데이터만 출력해야 해."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": "첨부된 사진을 분석해서 보행자에게 발생할 수 있는 '아차사고' 요소를 모두 찾아내고, 각 요소의 원인과 예방책을 분석해 줘.\n\n다음 규칙을 반드시 지켜서 작성해:\n1. 모든 분석 내용, 원인, 예방책은 반드시 '한국어'로 작성할 것.\n2. JSON의 키(Key) 값은 영어를 사용하되, 값(Value)은 한국어로 작성할 것.\n3. 추가 설명 없이 완벽한 JSON 형식만 출력할 것."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    temperature=1.0,
    top_p=0.95,
    presence_penalty=1.5,
    max_tokens=32768,
    extra_body={
        "top_k": 20,
    }
)

raw_output = response.choices[0].message.content

# ---------------------------------------------------------
# [ 시스템 충돌 없는 안전한 JSON 파싱 로직 ]
# ---------------------------------------------------------
try:
    # 정규식 대신, 텍스트에서 첫 번째 '{' 부터 마지막 '}' 까지만 정확히 잘라냅니다.
    start_idx = raw_output.find('{')
    end_idx = raw_output.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        json_str = raw_output[start_idx:end_idx+1]
        
        # 추출한 문자열을 Python Dictionary로 변환
        parsed_data = json.loads(json_str)
        
        # 한글이 깨지지 않게 예쁘게 출력
        print("✅ [ 분석 완료: 깔끔한 한국어 JSON 추출 성공 ]")
        print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
    else:
        raise ValueError("출력 결과에서 JSON 형태를 찾을 수 없습니다.")

except Exception as e:
    # 만약 파싱에 실패하면 디버깅을 위해 원본을 그대로 출력
    print(f"\n❌ [ 파싱 에러 발생 ]: {e}")
    print("=== 원본 출력 ===")
    print(raw_output)