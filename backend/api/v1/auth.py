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
        # force=1  # uncomment to force re‑consent during dev
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
        raise HTTPException(status_code=400, detail="Invalid state parameter")

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

    # you could redirect to front‑end with token in fragment:
    redirect_url = f"{str(settings.API_BASE_URL).rstrip('/')}/login/success?token={jwt_token}"
    return RedirectResponse(redirect_url)


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
