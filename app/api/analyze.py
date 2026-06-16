from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi import Depends
from app.dependencies import get_current_user
from app.services.analyze_service import (
    analyze_image_service,
    get_analysis_detail_service,
    get_analysis_history_service,
)
from app.services.report_service import create_analysis_report_pdf
from app.services.storage_service import download_analysis_image

router = APIRouter()

@router.post("")
async def analyze_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    업로드된 이미지를 분석하여 결과를 반환하는 API
    """
    return await analyze_image_service(file, current_user)


@router.get("/history")
def get_analysis_history(current_user: dict = Depends(get_current_user)):
    return get_analysis_history_service(current_user)


@router.get("/{analysis_id}")
def get_analysis_detail(
    analysis_id: int,
    current_user: dict = Depends(get_current_user),
):
    return get_analysis_detail_service(analysis_id, current_user)


@router.get("/{analysis_id}/image")
def get_analysis_image(
    analysis_id: int,
    current_user: dict = Depends(get_current_user),
):
    analysis = get_analysis_detail_service(analysis_id, current_user)
    image_url = analysis.get("image_url")
    if not image_url:
        raise HTTPException(status_code=404, detail="저장된 이미지가 없습니다.")

    image_bytes, content_type = download_analysis_image(image_url)
    return Response(content=image_bytes, media_type=content_type)


@router.get("/{analysis_id}/report")
def get_analysis_report(
    analysis_id: int,
    current_user: dict = Depends(get_current_user),
):
    analysis = get_analysis_detail_service(analysis_id, current_user)
    pdf_bytes = create_analysis_report_pdf(analysis)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="safety-report-{analysis_id}.pdf"'
        },
    )
