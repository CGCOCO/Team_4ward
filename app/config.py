"""
애플리케이션 설정 (환경변수 한곳에서 읽기)

- 프로젝트 루트의 .env 가 있으면 먼저 읽는다 (python-dotenv 가 설치된 경우).
- 값 목록과 설명은 .env.example 참고.
"""
import logging
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:  # dotenv 없이도 OS 환경변수만으로 동작
    pass

logger = logging.getLogger(__name__)

# ---------- 실행 환경 ----------
APP_ENV = os.getenv("APP_ENV", "development")
IS_PRODUCTION = APP_ENV == "production"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------- 인증 ----------
_DEV_SECRET_KEY = "dev-secret-change-me"
SECRET_KEY = os.getenv("SECRET_KEY", "")

# ---------- Google Cloud ----------
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "kun-kgp-mytnt831")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "team-4ward-analysis-images")

# ---------- 모델 ----------
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gemini-4-hydrogen")  # 위험요소 탐지·재순위
ANALYSIS_FINAL_MODEL = os.getenv("ANALYSIS_FINAL_MODEL", "gemini-4-carbon")  # 최종 분석 결과
ADVISOR_MODEL = os.getenv("ADVISOR_MODEL", "gemini-4-hydrogen")
EVALUATION_MODEL = os.getenv("EVALUATION_MODEL", "gemini-4-neon")

# ---------- 법령 RAG ----------
RAG_BACKEND = os.getenv("RAG_BACKEND", "app.rag.law_rag")


def get_secret_key() -> str:
    """토큰 서명 키. 운영 환경에서 SECRET_KEY 가 없으면 개발용 키로 대체하지 않고 실패한다."""
    if SECRET_KEY:
        return SECRET_KEY
    if IS_PRODUCTION:
        raise RuntimeError("APP_ENV=production 에서는 SECRET_KEY 환경변수가 필요합니다.")
    return _DEV_SECRET_KEY


def validate_settings() -> None:
    """서버 시작 시 호출. 운영 환경에서 필수 값이 없으면 시작을 막는다."""
    get_secret_key()
    if not SECRET_KEY:
        logger.warning("SECRET_KEY 가 설정되지 않아 개발용 기본 키를 사용합니다. 운영 환경에서는 반드시 설정하세요.")
    if RAG_BACKEND == "mock":
        logger.warning("RAG_BACKEND=mock: AI 도우미가 샘플 조문으로 답변합니다.")


def configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
