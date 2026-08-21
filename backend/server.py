from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import Literal
import os
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import secrets
import logging

from routes.google_auth import configure_google_auth, google_router

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
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_urlsafe(64))
JWT_ALGORITHM = "HS256"

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PASSWORD ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ==================== TOKEN ====================
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

# ==================== GOOGLE AUTH ====================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
configure_google_auth(db, create_access_token, create_refresh_token, GOOGLE_CLIENT_ID)

# ==================== AUTH ====================
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
    created_at = datetime.now(timezone.utc)
    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": email,
        "password_hash": hash_password(user_data.password),
        "role": user_data.role,
        "created_at": created_at,
        "auth_provider": "password",
    }
    await db.users.insert_one(user_doc)

    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")

    return User(id=user_id, name=user_data.name, email=email, role=user_data.role, created_at=created_at)

# ==================== LOGIN ====================
@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):
    user = await db.users.find_one({"email": credentials.email.lower()})

    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")

    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])

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

# ==================== ROOT / HEALTH ====================
@api_router.get("/")
async def root():
    return {"message": "API Online"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# ==================== ROUTERS ====================
app.include_router(api_router)
app.include_router(google_router, prefix="/api")

# ==================== CORS ====================
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip()
allowed_origins = [origin.strip().rstrip("/") for origin in frontend_url.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STARTUP ====================
@app.on_event("startup")
async def startup_event():
    logger.info("Servidor iniciado")
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.users.create_index("google_sub", unique=True, sparse=True)
        logger.info("Indexes criados")
    except Exception as exc:
        logger.warning(str(exc))
