# Setup

팀원이 이 브랜치를 로컬에서 실행하기 위한 최소 절차입니다.

## 1. 브랜치 받기

```bash
git fetch origin
git checkout <브랜치명>
git pull origin <브랜치명>
```

## 2. 백엔드 세팅

Python 3.12 기준입니다.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 프론트 세팅

```bash
cd frontend
npm install
cd ..
```

## 4. Git에 없는 필수 파일

아래 파일/폴더는 Git에 올리지 않으므로 별도로 받아서 같은 위치에 넣어야 합니다.

```text
app/models/face_yolo.pt
app/models/license_plate_yolo.pt
app/ai/scripts/chroma_db/
```

## 5. GCP 인증

실제 AI 분석, 이미지 저장, PDF 이미지 삽입에 필요합니다.

```bash
gcloud auth application-default login --no-launch-browser
gcloud auth application-default set-quota-project kun-kgp-mytnt831
```

필요 리소스:

```text
Project: kun-kgp-mytnt831
Bucket: team-4ward-analysis-images
```

## 6. 실행

백엔드:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

프론트:

```bash
cd frontend
npm run dev
```

접속:

```text
http://localhost:5173
```


```bash
rm app_data.sqlite3
uvicorn app.main:app --reload
```

## 7. 테스트 순서

1. 회원가입
2. 로그인
3. 이미지 업로드
4. 분석 결과 확인
5. 히스토리 확인
6. PDF 다운로드 확인

## 8. 어드바이저 법령 RAG

어드바이저 기능이 포함된 브랜치에서 저장소 루트 기준으로 실행합니다.

```powershell
$env:RAG_BACKEND = "app.rag.law_rag"
uvicorn app.main:app --reload
```

사진 분석과 어드바이저의 법령 검색은
`app/ai/scripts/forge_db/law/lawData.json`에서 같은 조문 인덱스를 불러옵니다.
현재 자료는 산업안전보건기준에 관한 규칙의 2025년 9월 1일 시행본입니다.
스냅샷을 교체한 뒤 서버를 재시작하면 법령 인덱스가 다시 만들어집니다.
사진 분석의 사고사례 검색에는 별도로 Chroma의 `accident_case_full` 컬렉션이 필요합니다.
