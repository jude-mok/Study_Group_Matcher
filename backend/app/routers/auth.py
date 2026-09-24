from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from supabase_auth.errors import AuthApiError

from app.database import get_supabase, get_supabase_admin
from app.dependencies import get_current_user, get_auth_identity, security
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas.user import UserResponse
from app.schemas.auth import (
    UserCreate,
    TokenResponse,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    RefreshTokenRequest
)
from app.services.user_service import (
    get_user_by_email,
    get_user_by_id,
    check_user_exists_by_email,
    check_user_exists_by_nyu_id,
    create_user_in_db
)
from app.services.utils import handle_route_errors
import logging


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@handle_route_errors
async def signup(
    user: UserCreate,
    supabase_admin: Client = Depends(get_supabase_admin)
) -> UserResponse:
    _ensure_user_not_exist(user, supabase_admin)
    auth_response = _create_user_credential(user, supabase_admin)

    user_data = {
        "id": auth_response.user.id,
        "nyu_email": user.nyu_email,
        "nyu_id": user.nyu_id,
        "name": user.name,
        "major": user.major,
        "minor": user.minor,
        "academic_standing": user.academic_standing,
        "work_willingness": user.work_willingness,
        "preferred_location": user.preferred_location,
        "time_preference": user.time_preference,
        "avg_gpa": user.avg_gpa
    }

    try:
        return create_user_in_db(supabase_admin, user_data)
    except Exception as e:
        _rollback_auth_user(supabase_admin, auth_response.user.id)
        if isinstance(e, HTTPException):
            logger.error("signup.profile_save_failed status=%s", e.status_code)
        raise


def _ensure_user_not_exist(user: UserCreate, supabase_admin : Client):
    if check_user_exists_by_email(supabase_admin, user.nyu_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email exists"
        )

    if check_user_exists_by_nyu_id(supabase_admin, user.nyu_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this NYU id exists"
        )

def _create_user_credential(user: UserCreate, supabase_admin : Client):
    auth_response = supabase_admin.auth.admin.create_user({
        "email": user.nyu_email,
        "password": user.password,
        "email_confirm": True,
        "user_metadata": {
            "name": user.name
        }
    })

    if not auth_response.user:
        logger.error("signup.auth_response_missing_user")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to complete signup. Please try again."
        )

    return auth_response

def _rollback_auth_user(supabase_admin: Client, user_id: str) -> None:
    try:
        supabase_admin.auth.admin.delete_user(user_id)
    except Exception as e:
        logger.error(
            "signup.rollback_failed error_type=%s", type(e).__name__,
        )


@router.post("/login", response_model=TokenResponse)
@handle_route_errors
async def login(
    credentials: LoginRequest,
    supabase: Client = Depends(get_supabase),
    supabase_admin: Client = Depends(get_supabase_admin),
) -> TokenResponse:
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.nyu_email,
            "password": credentials.password
        })
    except AuthApiError as e:
        if e.code != "invalid_credentials":
            raise  # leading unexpected error to hanlder.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        ) from e

    if not auth_response.session:
        logger.error("login.auth_response_missing_session")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to complete login. Please try again."
        )

    user_data = get_user_by_email(supabase_admin, credentials.nyu_email)

    return {
        "access_token": auth_response.session.access_token,
        "refresh_token": auth_response.session.refresh_token,
        "expires_at": auth_response.session.expires_at,
        "token_type": "bearer",
        "user": user_data
    }



@router.post("/logout", status_code=status.HTTP_200_OK)
@handle_route_errors
async def logout(
    _current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_admin),
):
    supabase.auth.admin.sign_out(credentials.credentials)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
@handle_route_errors
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    supabase: Client = Depends(get_supabase),
    supabase_admin: Client = Depends(get_supabase_admin),
) -> TokenResponse:
    auth_response = supabase.auth.refresh_session(refresh_request.refresh_token)

    if not auth_response.session or not auth_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_data = get_user_by_id(supabase_admin, auth_response.user.id)

    return {
        "access_token": auth_response.session.access_token,
        "refresh_token": auth_response.session.refresh_token,
        "expires_at": auth_response.session.expires_at,
        "token_type": "bearer",
        "user": user_data
    }


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
@handle_route_errors
async def request_password_reset(
    reset_request: PasswordResetRequest,
    supabase: Client = Depends(get_supabase)
):
    supabase.auth.reset_password_email(reset_request.email)
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
@handle_route_errors
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    identity = Depends(get_auth_identity),
    supabase: Client = Depends(get_supabase_admin)
):
    supabase.auth.admin.update_user_by_id(identity.id, {"password": reset_confirm.new_password})
    return {"message": "Password updated successfully"}


@router.get("/verify-email-status", status_code=status.HTTP_200_OK)
@handle_route_errors
async def check_email_verification(
    identity = Depends(get_auth_identity),
):
    return {
        "email_verified": identity.email_confirmed_at is not None,
        "email": identity.email
    }
