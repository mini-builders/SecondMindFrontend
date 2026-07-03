from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=7, max_length=15)
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    mobile: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    user_id: str
