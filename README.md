# Team_4ward
# Safe Guard AI

> Multimodal RAG-based Occupational Safety Risk Analysis System for Near-Miss Prevention

작업 현장 이미지를 기반으로 위험요소를 분석하고, 산업재해 사고사례 및 산업안전보건 법령 정보를 활용하여 아차사고 예방을 지원하는 멀티모달 RAG 기반 산업안전 위험 분석 시스템입니다.

[결과 예시 이미지]

---

## 📌 Overview

하인리히 법칙에 따르면 1건의 중대사고 발생 이전에는 29건의 경미사고와 300건의 아차사고(Near Miss)가 선행합니다.

본 프로젝트는 소규모 사업장 및 중소 건설현장과 같이 CCTV 기반 안전관리 시스템 구축이 어려운 환경을 대상으로, 사용자가 스마트폰으로 촬영한 작업 현장 이미지를 분석하여 위험요소와 잠재적 사고 상황을 식별하고 예방대책을 제공하는 것을 목표로 합니다.

---

## ✨ Features

- 개인정보 보호를 위한 얼굴 및 차량 번호판 마스킹
- Vision Language Model 기반 위험요소 분석
- 산업재해 사고사례 검색
- 산업안전보건 법령 검색
- LLM 기반 리랭킹
- 멀티모달 위험 분석
- 위험요소, 아차사고 시나리오, 예방대책 및 관련 법령 생성

---

## 🏗️ System Architecture

<p align="center">
  <img src="./assets/architecture.png" width="800">
</p>

```text
Input Image
      │
      ▼
Privacy Masking
      │
      ▼
Hazard Extraction
      │
      ▼
BM25 Retrieval
      │
      ▼
LLM Reranking
      │
      ▼
Multimodal Risk Analysis
      │
      ▼
Risk Analysis Report
```

---

## 🔄 Workflow

### 1. Privacy Masking

- YOLO 기반 얼굴 탐지
- YOLO 기반 차량 번호판 탐지
- OpenCV Gaussian Blur 적용

### 2. Hazard Extraction

- Gemini 3.5 Flash 활용
- 위험요소 키워드 생성
- 작업 환경 설명 생성

### 3. Retrieval

산업안전 관련 지식베이스를 구축하여 BM25 기반 검색 수행

#### Accident Case Database

- 산업재해 사고사례 665건

#### Safety Law Database

- 산업안전보건기준에 관한 규칙 670개 조문

#### Retrieval Results

- Accident Case Top-10
- Safety Law Top-10

### 4. LLM Reranking

입력 이미지와 검색 결과를 함께 고려하여 의미적 관련성을 평가

#### Inputs

- Input Image
- Hazard Keywords
- Situation Description
- Retrieved Documents

#### Outputs

- Accident Case Top-5
- Safety Law Top-5

### 5. Multimodal Risk Analysis

Gemini 3.1 Pro Preview 기반 멀티모달 추론 수행

#### Inputs

- Input Image
- Hazard Keywords
- Situation Description
- Retrieved Accident Cases
- Retrieved Safety Laws

#### Outputs

- Hazard Analysis
- Near-Miss Scenario
- Prevention Measures
- Related Safety Laws

---

## 📊 Dataset

### Accident Cases

- Source: KOSHA Industrial Accident Cases
- Total: 665 Cases

### Safety Laws

- Source: Occupational Safety and Health Standards
- Total: 670 Articles

### Evaluation Dataset

- AI Hub Construction Site Risk Assessment Dataset
- Total: 100 Images

---

## 📈 Evaluation Results

| Metric | Score |
|----------|----------|
| Hazard | 4.38 |
| Accident | 4.47 |
| Prevention | 4.68 |
| Law | 4.44 |
| Overall | **4.49** |

### Evaluation Criteria

| Metric | Description |
|----------|----------|
| Hazard | Hazard Detection Accuracy |
| Accident | Near-Miss Scenario Appropriateness |
| Prevention | Prevention Measure Appropriateness |
| Law | Safety Law Relevance |

### Evaluation Setup

- 100 construction site images
- 3 evaluators
- 5-point Likert scale
- Fall, Drop, Overturn, Crush, and Fire hazards

---

## 🛠️ Tech Stack

### Backend

- FastAPI
- Python

### Vision

- Gemini 3.5 Flash
- YOLO
- OpenCV

### Retrieval

- BM25
- Kiwi
- ChromaDB

### Multimodal Reasoning

- Gemini 3.1 Pro Preview

### Cloud

- Google Cloud Platform (GCP)
- Vertex AI

---

## 📚 Data Sources

### AI Hub

- Construction Site Risk Assessment Dataset
- https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71407

### KOSHA

- Industrial Accident Cases
- https://portal.kosha.or.kr/archive/disaster-case/accident-case/acccase-industry/manufac-industry

### Ministry of Employment and Labor

- Occupational Safety and Health Standards
- https://www.law.go.kr/법령/산업안전보건기준에관한규칙

---

## 📋 Project Planning

All team members participated in project planning, problem definition, and system requirement analysis.

The project was motivated by Heinrich’s Law, which emphasizes the importance of preventing Near-Miss incidents to reduce major industrial accidents. The team collaboratively defined the project scope and system requirements for supporting occupational safety in small-scale workplaces.

---
## 👥 Team Contributions

**Kangwon National University**

### 정성우

- Multimodal RAG 기반 위험 분석 파이프라인 설계
- 사고사례 및 법령 데이터베이스 구축
- BM25 검색 모듈 설계
- LLM 기반 리랭킹 모듈 설계
- 멀티모달 위험 분석 모듈 설계
- 실험 설계 및 성능 평가
- 논문 및 포스터 작성

### 김 온

- 개인정보 보호 모듈 개발
- FastAPI 기반 백엔드 개발
- API 연동 및 서버 구축

### 양찬규

- 프론트엔드 개발
- UI/UX 설계
- 서비스 화면 구현 및 연동

### 이재웅

- 프로젝트 지도 및 자문

---

## 🚀 Future Work

- 기업별 안전관리 지침 및 작업 표준서(SOP) 연계
- 사용자 업로드 데이터를 활용한 산업안전 데이터셋 확장
- 산업안전 특화 위험요소 탐지 모델 개발
- 아차사고 예측을 위한 산업안전 전용 AI 모델 연구
- 
---

로컬 실행 방법은 [SETUP.md](./SETUP.md)를 참고하세요.

