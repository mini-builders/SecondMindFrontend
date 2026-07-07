from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.auth import ChangePasswordRequest, LoginRequest, SignupRequest, TokenResponse
from app.services.auth_service import change_password, login_user, signup_user

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


@router.patch("/password", status_code=status.HTTP_200_OK)
async def change_password_route(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        await change_password(
            user_id=str(current_user["_id"]),
            current_password=request.current_password,
            new_password=request.new_password,
        )
        return {"ok": True, "message": "Password changed successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

