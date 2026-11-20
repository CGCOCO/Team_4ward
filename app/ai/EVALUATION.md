# 사진 분석 평가

이미 저장된 서비스 결과를 사진과 공식 조문에 대조합니다. 이 도구는 기존 웹 API와 별도로 실행합니다. 실행 시 평가 대상 사진과 결과를 지정한 Vertex AI 프로젝트로 전송하므로, 실제 테스트에서는 마스킹을 거친 사진이나 검증에 사용해도 되는 사진을 입력합니다.

## 실행

저장소 루트에서 프로젝트 의존성을 설치하고 GCP 인증을 설정한 후 다음처럼 실행합니다.

```powershell
python -m app.ai.evaluate cases.json --output evaluation.json
```

기본 평가 모델은 `gemini-4-neon`이며 `--model` 또는 `EVALUATION_MODEL`로 바꿀 수 있습니다. `--project`로 테스트용 GCP 프로젝트를 지정할 수 있습니다. 결과 파일은 각 사례가 끝날 때마다 갱신됩니다. 실패 사례는 이유와 함께 남고 종료 코드는 1입니다.

## 평가 입력

아래는 형식을 설명하는 예시입니다. 사진과 결과 파일 경로는 `cases.json`을 기준으로 해석합니다. `result`에는 분석 API가 반환한 JSON 또는 이력 API의 `ai_result`를 포함한 JSON을 저장합니다.

```json
[
  {
    "id": "excavator-01",
    "image": "photos/34-masked.jpg",
    "result": "analyses/34.json",
    "expected_hazards": [
      {"text": "굴착기 작업반경의 충돌 위험", "critical": true}
    ],
    "unverifiable_facts": ["사진 밖까지 포함한 현장의 신호수 배치 여부"],
    "reference_ids": ["007363-199"],
    "expected_law_ids": ["007363-221-2"]
  }
]
```

- `expected_hazards`에는 사진에서 관찰할 수 있는 위험이나, 사진의 상황에서 충분히 추론 가능한 위험을 사전에 기록합니다. 중대 위험은 `critical`로 표시합니다.
- `unverifiable_facts`에는 화면 밖 인원 배치처럼 사진만으로 확정할 수 없는 사실을 적습니다. 해당 사실을 단정한 결과는 사람이 재검토합니다.
- `reference_ids`는 판단에 참고할 공식 원문입니다. `expected_law_ids`는 그중 검색이 반드시 찾아야 할 조문입니다. 두 필드는 현재 프로젝트에서 조회 가능한 조문 ID를 사용합니다. 예를 들어 `007363-221-2`는 안전보건기준에 관한 규칙 제221조의2입니다. 평가 근거는 서비스의 검색 결과를 보기 전에 정합니다.
- 이미 실제 검색 로그를 보존했다면 `retrieval`에 `candidates`와 `reranked` 배열을 넣습니다. 저장된 최종 결과만 있으면 검색 점수는 미측정(`null`)으로 남습니다.
- `result`를 생략한 사례는 `--generate-missing`을 명시하면 기존 사진 분석기로 결과를 생성합니다. 기존 분석기용 사고사례 Chroma DB가 필요합니다. 이 모드는 업로드 마스킹을 거치지 않으므로 전처리된 사진을 넣습니다. 실제 BM25 후보와 재선정 ID를 보고서에 남깁니다.

## 평가 결과 해석

- **사진 판단**은 분석 항목마다 관찰 가능 여부와 이유를 기록합니다. 예상 사고는 실제로 발생했다고 가정하지 않고, 사진에서 개연성이 있는 시나리오인지 확인합니다. 핵심 위험 재현율의 분모는 사전에 정한 위험 전체입니다. AI가 확인 불가로 판단한 기준도 분모에 남고 검토 대상으로 표시됩니다. 사전 위험이 없으면 재현율은 미측정입니다.
- **법령 검색**은 사전 지정 조문과 실제 후보, 재선정 결과의 ID를 직접 비교합니다. 검색 기록 없이 생성 결과의 인용으로 검색 성능을 추정하지 않습니다.
- **법령 근거**는 출력에 적힌 조문 번호로 공식 원문을 조회하고 주장과 대조합니다. AI가 인용한 문구가 해당 공식 원문에 실제로 있어야 근거가 검증된 것으로 집계합니다. 조회 실패나 확인되지 않는 인용문은 근거 부족으로 남깁니다.

보고서에는 판정 이유, 인용 원문 구절, 출처 링크와 해시, 모델 버전, 토큰 사용량을 남깁니다. 중대한 오류·누락과 확인할 수 없는 인용은 `needs_review`로 표시합니다.

## 1~5점 채점표

`--score`로 사진별 네 항목의 정수 점수와 채점 이유를 추가합니다. AI와 전문가는 동일한 사진과 저장된 분석 결과를 아래 기준으로 평가합니다. 전문가는 AI의 점수와 채점 이유를 보기 전에 채점합니다.

| 항목 | 기준 |
| --- | --- |
| Hazard | 사진에서 관찰되거나 합리적으로 추론되는 핵심 위험을 짚었는지, 중요한 위험 누락이나 근거 없는 단정이 있는지 |
| Accident | 감지한 위험에서 이어질 수 있는 아차사고 과정이 사진의 상황에서 구체적이고 개연성이 있는지 |
| Prevention | 위험과 직접 연결되는 구체적이고 실행 가능한 대책인지, 권고가 추가 위험을 만드는지 |
| Law | 인용 조문의 공식 원문과 설명이 맞는지, 조문이 현장 위험과 관련 있는지, 확인된 사실과 법령 적용 조건을 구분했는지 |

| 점수 | 판단 기준 |
| --- | --- |
| 5점 매우 적절함 | 핵심 내용을 충족하고 중요한 누락이나 오류가 없다. |
| 4점 적절함 | 핵심 내용을 충족하고 경미한 보완이 필요하다. |
| 3점 보통 | 타당한 내용이 있으나 중요한 보완이 필요하다. |
| 2점 부적절함 | 핵심 판단에 큰 오류나 누락이 있다. |
| 1점 매우 부적절함 | 평가할 결과가 없거나, 대부분 부적절하거나, 중대한 오류가 있다. |

## 전문가 평균으로 전체 점수 보정

사진 100장과 분석 결과를 고정한 뒤 전문가가 볼 20장을 무작위 추출합니다. 예시 시드 42는 추출 전에 정합니다. AI는 전문가 표본을 포함한 100장 모두를 평가합니다.

```powershell
python -m app.ai.calibrate_evaluation sample cases.json --size 20 --seed 42 --output expert-sample.json
python -m app.ai.evaluate cases.json --score --output scored-evaluation.json
```

전문가에게는 `expert-sample.json`의 ID에 해당하는 사진과 분석 결과, 채점표를 제공합니다. 전문가가 준 항목별 평균 네 개를 `expert-sample.json`의 `means`에 채웁니다. 가능하면 반올림 전 평균을 사용합니다. 다음 값은 형식 예시입니다.

```json
"means": {"hazard": 3.90, "accident": 4.10, "prevention": 4.20, "law": 3.70}
```

```powershell
python -m app.ai.calibrate_evaluation correct scored-evaluation.json expert-sample.json --output corrected-evaluation.json
```

항목별로 **보정 평균 = AI 전체 100장 평균 + (전문가 표본 20장 평균 − 같은 20장의 AI 평균)**을 계산합니다. 보고서에 세 평균과 보정량, 최종 평균을 기록합니다. 예를 들어 AI 전체 4.18, 표본 AI 4.10, 표본 전문가 3.90이면 보정 평균은 3.98입니다. 평균만 받은 경우 보정 평균의 점 추정치를 보고하며 사진별 차이에 기반한 신뢰구간과 일치도는 산출하지 않습니다. 결과가 1~5 범위를 벗어나면 계산값을 그대로 두고 표시합니다. 이 보정은 [Prediction-Powered Inference의 유한 모집단 평균 추정](https://www.stat.ubc.ca/~john/papers/AngelopoulosScience2023.pdf#page=28)에 쓰이는 평균 차이를 적용합니다.

## 방법론 참고

방법론은 RAGChecker의 검색·생성 분리, RAGAS의 주장별 근거 검증, POPE의 이미지에 근거한 사실 검증 아이디어를 적용했습니다. 사진을 바탕으로 위험 가능성과 확인된 사실을 구분하도록 팀 평가 기준을 추가했습니다.

- [RAGChecker, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/27245589131d17368cccdfa990cbf16e-Abstract.html)
- [RAGAS, EACL 2024](https://aclanthology.org/2024.eacl-demo.16/)
- [POPE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.20/)
