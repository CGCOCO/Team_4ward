from pathlib import Path
import asyncio
import json
import tempfile

from fastapi import HTTPException, UploadFile

from app.db import get_connection
from app.privacy.image_masker import blur_sensitive_regions
from app.services.storage_service import upload_analysis_image


MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
DEBUG_BLURRED_IMAGE_PATH = Path("debug_blurred_latest.jpg")


def _get_temp_suffix(content_type: str | None) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type, ".jpg")


def _analyze_with_agent(image_path: Path) -> dict:
    from app.ai.scripts.main import run_analysis

    return run_analysis(image_path)


def _serialize_analysis_row(row) -> dict:
    ai_result = json.loads(row["ai_result"])
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "image_url": row["image_url"],
        "ai_result": ai_result,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def analyze_image_service(image: UploadFile, current_user: dict) -> dict:
    """
    업로드된 이미지 파일을 검증하고 AI 호출
    """

    # 1. 이미지 타입 검증
    if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 이미지 형식입니다. jpg, png, webp만 업로드할 수 있습니다.",
        )

    # 2. 이미지 파일 바이트 읽기
    image_bytes = await image.read()

    # 3. 빈 파일 검증
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="빈 이미지 파일입니다.",
        )

    # 4. 이미지 크기 제한
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="이미지 파일 크기는 최대 10MB까지 허용됩니다.",
        )

    # 5. 민감한 정보 블러 처리
    try:
        masked_image_bytes = await blur_sensitive_regions(image_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    DEBUG_BLURRED_IMAGE_PATH.write_bytes(masked_image_bytes)

    # 6. AI 위험 분석 실행
    suffix = _get_temp_suffix(image.content_type)
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_file.write(masked_image_bytes)
            temp_file_path = Path(temp_file.name)

        result = await asyncio.to_thread(
            _analyze_with_agent,
            temp_file_path,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI 분석 중 오류가 발생했습니다: {exc}",
        ) from exc
    finally:
        if temp_file_path is not None:
            temp_file_path.unlink(missing_ok=True)

    image_url = upload_analysis_image(
        masked_image_bytes,
        user_id=current_user["id"],
        content_type=image.content_type or "image/jpeg",
        suffix=suffix,
    )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_results (user_id, image_url, ai_result)
            VALUES (?, ?, ?)
            """,
            (
                current_user["id"],
                image_url,
                json.dumps(result, ensure_ascii=False),
            ),
        )
        analysis_id = cursor.lastrowid

    return {
        "id": analysis_id,
        "image_url": image_url,
        **result,
    }


def get_analysis_history_service(current_user: dict) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, image_url, ai_result, created_at, updated_at
            FROM analysis_results
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (current_user["id"],),
        ).fetchall()

    return [_serialize_analysis_row(row) for row in rows]


def get_analysis_detail_service(analysis_id: int, current_user: dict) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, image_url, ai_result, created_at, updated_at
            FROM analysis_results
            WHERE id = ? AND user_id = ?
            """,
            (analysis_id, current_user["id"]),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")

    return _serialize_analysis_row(row)
