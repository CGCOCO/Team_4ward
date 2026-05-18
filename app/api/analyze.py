from fastapi import APIRouter, File, UploadFile
from app.services.analyze_service import analyze_image_service

router = APIRouter()

@router.post("")
async def analyze_image(file: UploadFile = File(...)):
    """
    업로드된 이미지를 분석하여 결과를 반환하는 API
    """
    return await analyze_image_service(file)
