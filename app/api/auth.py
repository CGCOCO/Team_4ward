from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_current_user
from app.db import get_connection
from app.security import create_access_token, hash_password, verify_password


router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("올바른 이메일을 입력하세요.")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("올바른 이메일을 입력하세요.")
        return normalized


class ProfileUpdateRequest(BaseModel):
    email: str | None = None
    name: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("올바른 이메일을 입력하세요.")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


def serialize_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
    }


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest):
    password_hash = hash_password(payload.password)

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, name)
                VALUES (?, ?, ?)
                """,
                (payload.email.lower(), password_hash, payload.name),
            )
            user_id = cursor.lastrowid
            row = conn.execute(
                "SELECT id, email, name FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.") from exc
        raise

    token = create_access_token(user_id)
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(row)}


@router.post("/login")
def login(payload: LoginRequest):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = ?",
            (payload.email.lower(),),
        ).fetchone()

    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(row["id"])
    return {"access_token": token, "token_type": "bearer", "user": serialize_user(row)}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/me")
def update_me(
    payload: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

        email = payload.email if payload.email is not None else row["email"]
        name = payload.name if payload.name is not None else row["name"]
        password_hash = row["password_hash"]

        if payload.new_password:
            if not payload.current_password:
                raise HTTPException(status_code=400, detail="현재 비밀번호를 입력하세요.")
            if not verify_password(payload.current_password, row["password_hash"]):
                raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
            password_hash = hash_password(payload.new_password)

        try:
            conn.execute(
                """
                UPDATE users
                SET email = ?, name = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (email, name, password_hash, current_user["id"]),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.") from exc
            raise

        updated = conn.execute(
            "SELECT id, email, name FROM users WHERE id = ?",
            (current_user["id"],),
        ).fetchone()

    return serialize_user(updated)
