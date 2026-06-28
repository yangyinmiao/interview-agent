from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class TenantLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TenantInfo(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
