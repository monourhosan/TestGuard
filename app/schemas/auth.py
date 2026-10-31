from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="User login email address")
    password: str = Field(min_length=1, max_length=128, description="User password")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    tenant_id: int
    role: str
    iat: int
    exp: int
