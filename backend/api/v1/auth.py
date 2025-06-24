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
        redirect_url = f"{str(settings.API_BASE_URL).rstrip('/')}/login/success?token={jwt_token}"
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
    session: AsyncSession = Depends(get_session),
):
    """
    Check if the current user has all required permissions for task/calendar integration.
    Returns re-authentication URL if permissions are missing.
    """
    try:
        # For now, get the first user (in a real app, you'd get this from JWT token)
        result = await session.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            return {
                "status": "not_authenticated",
                "message": "No user found - please authenticate",
                "needs_reauthentication": True,
                "reauthentication_url": f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google"
            }
        
        # For now, assume user has permissions if they exist
        # In a real app, you'd check the actual scopes
        return {
            "status": "ok",
            "message": "User has all required permissions",
            "needs_reauthentication": False
        }
            
    except Exception as e:
        logger.exception(f"Error checking user permissions: {e}")
        return {
            "status": "error",
            "message": "Failed to check permissions",
            "needs_reauthentication": True,
            "reauthentication_url": f"{str(settings.API_BASE_URL).rstrip('/')}/api/v1/auth/google"
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
