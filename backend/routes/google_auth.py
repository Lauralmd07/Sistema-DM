from datetime import datetime, timezone
from typing import Callable, Optional
import uuid

from fastapi import APIRouter, HTTPException, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel


google_router = APIRouter(prefix="/auth", tags=["auth"])
_db = None
_create_access_token: Optional[Callable] = None
_create_refresh_token: Optional[Callable] = None
_google_client_id: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    credential: str


def configure_google_auth(db, create_access_token, create_refresh_token, google_client_id: str):
    global _db, _create_access_token, _create_refresh_token, _google_client_id
    _db = db
    _create_access_token = create_access_token
    _create_refresh_token = create_refresh_token
    _google_client_id = google_client_id


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=900,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
        path="/",
    )


@google_router.post("/google")
async def google_login(payload: GoogleLoginRequest, response: Response):
    if not _db or not _create_access_token or not _create_refresh_token or not _google_client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured")

    try:
        claims = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            _google_client_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    email = (claims.get("email") or "").strip().lower()
    google_sub = claims.get("sub")
    name = (claims.get("name") or email.split("@")[0]).strip()

    if not email or not google_sub or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    user = await _db.users.find_one({"google_sub": google_sub})

    if not user:
        user = await _db.users.find_one({"email": email})

        if user:
            await _db.users.update_one(
                {"id": user["id"]},
                {"$set": {"google_sub": google_sub, "auth_provider": "google"}},
            )
            user["google_sub"] = google_sub
            user["auth_provider"] = "google"
        else:
            user = {
                "id": str(uuid.uuid4()),
                "name": name,
                "email": email,
                "password_hash": None,
                "role": "lawyer",
                "google_sub": google_sub,
                "auth_provider": "google",
                "created_at": datetime.now(timezone.utc),
            }
            await _db.users.insert_one(user)

    access_token = _create_access_token(user["id"], user["email"])
    refresh_token = _create_refresh_token(user["id"])
    _set_auth_cookies(response, access_token, refresh_token)

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "lawyer"),
        "created_at": user["created_at"],
    }
