from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal
import logging
import os
import uuid

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from routes.appointments import router as appointments_router
from routes.documents import router as documents_router
from routes.financial import router as financial_router
from routes.folders import router as folders_router
from routes.google_auth import configure_google_auth, google_router
from routes.processes import router as processes_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ.get("MONGO_URL", "").strip()
if not mongo_url:
    raise RuntimeError("MONGO_URL is not configured")

db_name = os.environ.get("DB_NAME", "legal_system").strip() or "legal_system"
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
    maxPoolSize=50,
    minPoolSize=1,
)
db = client[db_name]

JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not configured")
JWT_ALGORITHM = "HS256"

app = FastAPI(title="Sistema DM API", version="1.1.0")
app.state.db = db
app.state.jwt_secret = JWT_SECRET

api_router = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, email: str):
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str):
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=True,
        samesite="none", max_age=900, path="/"
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=True,
        samesite="none", max_age=604800, path="/"
    )


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "lawyer"]
    created_at: datetime


@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):
    email = user_data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    user_doc = {
        "id": user_id,
        "name": user_data.name.strip(),
        "email": email,
        "password_hash": hash_password(user_data.password),
        "role": "lawyer",
        "created_at": created_at,
        "auth_provider": "password",
    }
    await db.users.insert_one(user_doc)
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return User(id=user_id, name=user_doc["name"], email=email, role="lawyer", created_at=created_at)


@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):
    user = await db.users.find_one({"email": credentials.email.lower()})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        valid = verify_password(credentials.password, user["password_hash"])
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    set_auth_cookies(response, create_access_token(user["id"], user["email"]), create_refresh_token(user["id"]))
    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])


@api_router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["id"], user["email"])
        response.set_cookie(
            key="access_token", value=access, httponly=True, secure=True,
            samesite="none", max_age=900, path="/"
        )
        return {"success": True}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api_router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/", secure=True, samesite="none")
    response.delete_cookie(key="refresh_token", path="/", secure=True, samesite="none")
    return {"message": "Logout successful"}


@api_router.get("/")
async def root():
    return {"message": "API Online", "version": "1.1.0"}


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"ok": True, "status": "healthy", "database": "connected"}
    except Exception as exc:
        logger.exception("Database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database unavailable")


# Configure Google authentication with the same DB/JWT functions used by password login.
configure_google_auth(
    db,
    create_access_token,
    create_refresh_token,
    os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
)

app.include_router(api_router)
app.include_router(google_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(financial_router, prefix="/api")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip()
allowed_origins = [origin.strip().rstrip("/") for origin in frontend_url.split(",") if origin.strip()]
if not allowed_origins:
    raise RuntimeError("FRONTEND_URL is not configured")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("Servidor iniciado")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.users.create_index("google_sub", unique=True, sparse=True)
    await db.processes.create_index([("owner_id", 1), ("created_at", -1)])
    await db.appointments.create_index([("owner_id", 1), ("date", 1), ("time", 1)])
    await db.folders.create_index([("owner_id", 1), ("created_at", -1)])
    await db.documents.create_index([("owner_id", 1), ("folder_id", 1), ("created_at", -1)])
    await db.financial.create_index([("date", -1)])


@app.on_event("shutdown")
async def shutdown_event():
    client.close()
