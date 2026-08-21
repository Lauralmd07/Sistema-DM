from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import Literal
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import secrets
import logging

# ==================== LOAD ENV ====================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ==================== DATABASE ====================
mongo_url = os.environ["MONGO_URL"]

client = AsyncIOMotorClient(mongo_url)

db = client[os.environ.get("DB_NAME", "legal_system")]

# ==================== APP ====================
app = FastAPI()

api_router = APIRouter(prefix="/api")

# ==================== JWT ====================
JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    secrets.token_urlsafe(64)
)

JWT_ALGORITHM = "HS256"

# ==================== GOOGLE ====================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PASSWORD ====================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ==================== TOKEN ====================
def create_access_token(user_id: str, email: str):
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str):
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, user_id: str, email: str):
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=900,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
        path="/"
    )

# ==================== AUTH ====================
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

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

# ==================== MODELS ====================
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["admin", "lawyer"] = "lawyer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    credential: str


class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "lawyer"]
    created_at: datetime

# ==================== REGISTER ====================
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):
    email = user_data.email.lower()

    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)

    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": email,
        "password_hash": hashed_password,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc)
    }

    await db.users.insert_one(user_doc)
    set_auth_cookies(response, user_id, email)

    return User(
        id=user_id,
        name=user_data.name,
        email=email,
        role=user_data.role,
        created_at=user_doc["created_at"]
    )

# ==================== LOGIN ====================
@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):
    email = credentials.email.lower()

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_hash = user.get("password_hash")
    if not password_hash:
        raise HTTPException(
            status_code=401,
            detail="Esta conta usa o login com Google. Entre com Google."
        )

    if not verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    set_auth_cookies(response, user["id"], user["email"])

    return User(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )

# ==================== GOOGLE LOGIN ====================
@api_router.post("/auth/google", response_model=User)
async def google_login(data: GoogleLogin, response: Response):
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID não configurado")
        raise HTTPException(
            status_code=500,
            detail="Login com Google não está configurado no servidor"
        )

    try:
        google_user = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Token do Google inválido ou expirado"
        )

    email = str(google_user.get("email", "")).lower()
    google_sub = google_user.get("sub")
    email_verified = google_user.get("email_verified", False)

    if not email or not google_sub or not email_verified:
        raise HTTPException(
            status_code=401,
            detail="A conta do Google não possui um e-mail verificado"
        )

    user = await db.users.find_one({"google_sub": google_sub})

    if not user:
        user = await db.users.find_one({"email": email})

    if user:
        existing_google_sub = user.get("google_sub")

        if existing_google_sub and existing_google_sub != google_sub:
            raise HTTPException(
                status_code=409,
                detail="Esta conta já está vinculada a outra conta Google"
            )

        await db.users.update_one(
            {"id": user["id"]},
            {
                "$set": {
                    "google_sub": google_sub,
                    "auth_provider": "google"
                }
            }
        )

        user["google_sub"] = google_sub
        user["auth_provider"] = "google"
    else:
        user_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        user = {
            "id": user_id,
            "name": google_user.get("name") or email.split("@")[0],
            "email": email,
            "google_sub": google_sub,
            "auth_provider": "google",
            "role": "lawyer",
            "created_at": created_at
        }

        await db.users.insert_one(user.copy())

    set_auth_cookies(response, user["id"], user["email"])

    return User(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )

# ==================== ME ====================
@api_router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== LOGOUT ====================
@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logout successful"}

# ==================== ROOT ====================
@api_router.get("/")
async def root():
    return {"message": "API Online"}

# ==================== HEALTH ====================
@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# ==================== ROUTER ====================
app.include_router(api_router)

# ==================== CORS ====================
frontend_url = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:3000"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==================== STARTUP ====================
@app.on_event("startup")
async def startup_event():
    logger.info("Servidor iniciado")

    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.users.create_index(
            "google_sub",
            unique=True,
            sparse=True
        )
        logger.info("Indexes criados")
    except Exception as e:
        logger.warning(str(e))
