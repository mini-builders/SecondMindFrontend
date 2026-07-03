from fastapi import APIRouter, HTTPException, status

from app.models.auth import LoginRequest, SignupRequest, TokenResponse
from app.services.auth_service import login_user, signup_user

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest) -> TokenResponse:
    try:
        result = await signup_user(request.name, request.mobile, request.password)
        return TokenResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    try:
        result = await login_user(request.mobile, request.password)
        return TokenResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
