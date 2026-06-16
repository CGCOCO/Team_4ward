from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import get_connection
from app.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
    }
