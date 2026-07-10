from pydantic import BaseModel, EmailStr, Field


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegistrationResponse(BaseModel):
    id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
