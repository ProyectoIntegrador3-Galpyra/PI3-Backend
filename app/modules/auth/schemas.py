from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.shared.enums import RolUsuario


class UsuarioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    email: EmailStr
    rol: RolUsuario
    is_active: bool


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UsuarioOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10)
