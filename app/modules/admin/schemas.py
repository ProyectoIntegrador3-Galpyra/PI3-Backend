from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.shared.enums import RolUsuario


class UsuarioAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    email: str
    rol: RolUsuario
    is_active: bool


class UsuarioCreateRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rol: RolUsuario = RolUsuario.PRODUCTOR


class UsuarioUpdateRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=150)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    rol: RolUsuario | None = None
