from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.advisor.service import get_session, list_sessions, stream_chat
from app.dependencies import get_current_user
from app.rag.interface import get_rag

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: int | None = None
    context: str | None = Field(default=None, max_length=4000)  # 사진 분석 결과 등 현장 상황


@router.post("/chat")
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    return StreamingResponse(
        stream_chat(current_user, request.message.strip(), request.session_id, request.context),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/articles/{article_id}")
def get_article(article_id: str, current_user: dict = Depends(get_current_user)):
    article = get_rag().get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="조문을 찾을 수 없습니다.")
    return article


@router.get("/sessions")
def get_sessions(current_user: dict = Depends(get_current_user)):
    return list_sessions(current_user)


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: int, current_user: dict = Depends(get_current_user)):
    return get_session(session_id, current_user)
