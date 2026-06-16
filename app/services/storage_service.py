from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError, NotFound


GCS_BUCKET_NAME = "team-4ward-analysis-images"


def _get_storage_client() -> storage.Client:
    return storage.Client(project="kun-kgp-mytnt831")


def _parse_gs_url(gs_url: str) -> tuple[str, str]:
    if not gs_url.startswith("gs://"):
        raise ValueError("GCS URL 형식이 아닙니다.")

    path = gs_url.removeprefix("gs://")
    bucket_name, _, object_name = path.partition("/")
    if not bucket_name or not object_name:
        raise ValueError("GCS URL 형식이 아닙니다.")

    return bucket_name, object_name


def upload_analysis_image(
    image_bytes: bytes,
    *,
    user_id: int,
    content_type: str,
    suffix: str,
) -> str:
    now = datetime.utcnow()
    object_name = (
        f"analysis-images/user-{user_id}/"
        f"{now:%Y/%m/%d}/"
        f"{uuid4().hex}{suffix}"
    )

    try:
        client = _get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.upload_from_string(
            image_bytes,
            content_type=content_type,
        )
    except GoogleAPIError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 저장 중 오류가 발생했습니다: {exc}",
        ) from exc

    return f"gs://{GCS_BUCKET_NAME}/{object_name}"


def download_analysis_image(gs_url: str) -> tuple[bytes, str]:
    try:
        bucket_name, object_name = _parse_gs_url(gs_url)
        client = _get_storage_client()
        blob = client.bucket(bucket_name).blob(object_name)
        image_bytes = blob.download_as_bytes()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.") from exc
    except GoogleAPIError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"이미지를 불러오는 중 오류가 발생했습니다: {exc}",
        ) from exc

    content_type = blob.content_type or "application/octet-stream"
    return image_bytes, content_type


def content_type_from_suffix(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
