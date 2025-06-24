from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union

from core.config import settings
from core.crypto import encrypt
from core.security import create_access_token
from core.database import get_session
from models.user import User
from services.google_oauth import build_flow, get_user_info
from services.drive_client import ensure_drive_watch
from services import drive_client
from core.logging import logger
from core.security import get_current_user
from googleapiclient.discovery import build
# from services.auth_helper import check_user_has_required_scopes, get_missing_scopes, force_reauthentication_url

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/google")
async def auth_google() -> RedirectResponse:
    """
    Start the OAuth consent screen.  The generated `state` param protects
    against CSRF – Google stores it and echoes it back.
    """
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    response = RedirectResponse(auth_url)
    response.set_cookie("oauth_state", state, httponly=True, secure=False)
    return response


@router.get("/google/callback")
async def auth_google_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Handles Google's redirect - exchanges `code` for tokens,
    stores/updates the user, returns an app JWT you can place
    in localStorage / Authorization header.
    """
    stored_state = request.cookies.get("oauth_state")
    incoming_state = request.query_params.get("state")
    
    if stored_state != incoming_state:
        logger.error(f"State parameter mismatch. Stored: {stored_state}, Incoming: {incoming_state}")
        # Return a more helpful error page instead of just 400
        return RedirectResponse(
            url=f"{str(settings.API_BASE_URL).rstrip('/')}/auth/error?reason=state_mismatch",
            status_code=302
        )

    try:
        flow = build_flow(state=incoming_state)
        flow.fetch_token(code=request.query_params.get("code"))

        credentials = flow.credentials
        email, name, pic = get_user_info(credentials)

        user = None
        try:
            user = await _upsert_user(
                session,
                email=email,
                full_name=name,
                picture=pic,
                refresh_token=credentials.refresh_token,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        jwt_token = create_access_token({"sub": str(user.id), "email": email})

        folder_id = drive_client.find_meet_folder_id(credentials)
        if folder_id:
            user.meet_folder_id = folder_id
        else:
            # Edge-case: folder doesn't exist yet (user never recorded a Meet)
            # Keep field = None; we'll skip processing until it appears.
            logger.warning("Meet Recordings folder not found for {}", email)

        # you could redirect to front‑end with token in fragment:
        redirect_url = f"{str(settings.FRONTEND_URL).rstrip('/')}/dashboard?token={jwt_token}"
        await ensure_drive_watch(user)
        await session.commit()
        return RedirectResponse(redirect_url)
        
    except Exception as e:
        logger.exception(f"Error during OAuth callback: {e}")
        return RedirectResponse(
            url=f"{str(settings.API_BASE_URL).rstrip('/')}/auth/error?reason=callback_error",
            status_code=302
        )


@router.get("/check-permissions")
async def check_user_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Check if the user has proper Google API permissions.
    If not, return reauthentication URL.
    """
    try:
        creds = drive_client._credentials_from_user(current_user)
        # Test the credentials by making a simple API call
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        service.about().get(fields="user").execute()
        
        return {
            "status": "ok",
            "message": "User has proper permissions"
        }
    except Exception as e:
        logger.warning("User {} needs reauthentication: {}", current_user.email, e)
        
        # Generate reauthentication URL
        auth_url = _build_google_auth_url(request.base_url)
        
        return {
            "status": "error",
            "message": "Authentication required",
            "needs_reauthentication": True,
            "missing_scopes": ["drive", "tasks", "calendar"],
            "reauthentication_url": auth_url
        }


@router.get("/user")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get the current user's profile information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "picture": current_user.picture,
        "created_at": current_user.created_at
    }


@router.get("/error")
async def auth_error(reason: str = "unknown"):
    """
    Handle OAuth errors and provide helpful information.
    """
    error_messages = {
        "state_mismatch": "The authentication session expired or was invalid. Please try again.",
        "callback_error": "There was an error processing your authentication. Please try again.",
        "unknown": "An unknown error occurred during authentication."
    }
    
    message = error_messages.get(reason, error_messages["unknown"])
    
    return {
        "error": "Authentication Failed",
        "reason": reason,
        "message": message,
        "restart_url": f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google"
    }

@router.get("/restart")
async def restart_auth():
    """
    Restart the OAuth flow with a fresh state.
    """
    return RedirectResponse(url=f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google")


# ──────────────────────────────────────────────────────────────────────────────
# helpers


async def _upsert_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: Union[str, None],
    picture: Union[str, None],
    refresh_token: Union[str, None],
) -> User:
    """
    Create new or update existing user row.
    """
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            picture=picture,
            refresh_token_enc=encrypt(refresh_token or ""),
        )
        session.add(user)
    else:
        user.full_name = full_name or user.full_name
        user.picture = picture or user.picture
        if refresh_token:
            user.refresh_token_enc = encrypt(refresh_token)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)  # populate ID if new
    return user
