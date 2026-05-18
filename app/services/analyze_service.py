# app/services/analyze_service.py

from fastapi import HTTPException, UploadFile

from app.ai.dummy_analyzer import dummy_analyze_risk
from app.privacy.image_masker import dummy_blur_image


MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


async def analyze_image_service(image: UploadFile) -> dict:
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
    masked_image_bytes = await dummy_blur_image(image_bytes)

    # 6. AI 위험 분석 실행
    result = await dummy_analyze_risk(masked_image_bytes)

    return result