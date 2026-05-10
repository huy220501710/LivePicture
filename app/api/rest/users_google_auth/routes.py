import uuid
import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import insert, select

from app.api.rest.dependencies import db
from app.api.rest.utils import create_access_token, create_refresh_token, save_file_bytes
from app.config import settings
from app.httpx.app import get_httpx_client
from app.postgresql.models import UsersOrm

router = APIRouter(prefix="/users/google/auth", tags=["users-google-auth"])


@router.get("/login/")
async def login_google():
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH2_REDIRECT_URI.strip(),
        "scope": "openid profile email",
        "access_type": "offline",
        "prompt": "consent",
    }
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    }


@router.get("/")
async def auth_google(code: str, db: db):
    client = get_httpx_client()
    redirect_uri = settings.GOOGLE_OAUTH2_REDIRECT_URI.strip()

    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    response = await client.post(token_url, data=data)
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Google token exchange failed")

    access_token = response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Google access token not found")

    user_info = await client.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if user_info.status_code >= 400:
        raise HTTPException(status_code=400, detail="Google user info request failed")

    user_data = user_info.json()
    if "id" not in user_data or "email" not in user_data:
        raise HTTPException(status_code=400, detail="Google user info is incomplete")

    user_by_google_id = await db.scalar(
        select(UsersOrm).where(UsersOrm.google_id == user_data["id"])
    )

    register = False
    if not user_by_google_id:
        username = user_data["email"].split("@")[0]
        user_by_username = await db.scalar(select(UsersOrm).where(UsersOrm.username == username))
        if user_by_username:
            username = f"{username}_{uuid.uuid4().hex[:6]}"

        response = await client.get(user_data["picture"])

        unique_filename = f"{uuid.uuid4()}.jpg"
        image_path = os.path.join(settings.MEDIA_PATH, "users", unique_filename)

        await save_file_bytes(response.content, image_path)

        user_by_google_id = await db.scalar(
            insert(UsersOrm)
            .values(
                google_id=user_data["id"],
                username=username,
                email=user_data["email"],
                verified=True,
                image=image_path,
            )
            .returning(UsersOrm)
        )
        register = True
        await db.commit()

    access_token = create_access_token({"user_id": user_by_google_id.id})
    refresh_token = create_refresh_token({"user_id": user_by_google_id.id})

    if not register:
        response_frontend = RedirectResponse(url=settings.FRONTEND_DOMAIN, status_code=302)
    else:
        response_frontend = RedirectResponse(
            url=f"{settings.FRONTEND_DOMAIN}?register=true", status_code=302
        )

    response_frontend.set_cookie("access_token", access_token, httponly=True, samesite="lax")
    response_frontend.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax")

    return response_frontend
