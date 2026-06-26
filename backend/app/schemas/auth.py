from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class TeacherRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class TeacherLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeacherOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    model_config = {"from_attributes": True}
