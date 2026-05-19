from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import Literal
from datetime import datetime, timezone, timedelta
import os
import logging
import bcrypt
import jwt
import uuid
import secrets
import certifi

# ==================== LOAD ENV ====================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ==================== MONGODB ====================

mongo_url = os.getenv("MONGO_URL")

client = AsyncIOMotorClient(
    mongo_url,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=30000
)

db = client["legal_system"]

# ==================== APP ====================

app = FastAPI()

api_router = APIRouter(prefix="/api")

# ==================== JWT ====================

JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    secrets.token_urlsafe(64)
)

# ==================== PASSWORD ====================

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
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

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def create_refresh_token(user_id: str):
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

# ==================== AUTH ====================

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        user = await db.users.find_one({
            "id": payload["sub"]
        })

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        user.pop("_id", None)
        user.pop("password_hash", None)

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

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
    role: str
    created_at: datetime

# ==================== ADMIN SEED ====================

async def seed_admin():
    admin_email = os.environ.get(
        "ADMIN_EMAIL",
        "lauralmd07@gmail.com"
    )

    admin_password = os.environ.get(
        "ADMIN_PASSWORD",
        "Ladm848407*"
    )

    existing = await db.users.find_one({
        "email": admin_email
    })

    if not existing:
        admin_id = str(uuid.uuid4())

        await db.users.insert_one({
            "id": admin_id,
            "name": "Administrador",
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc)
        })

        logger.info("Admin criado com sucesso")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=User)
async def register(
    user_data: UserCreate,
    response: Response
):
    existing = await db.users.find_one({
        "email": user_data.email.lower()
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_id = str(uuid.uuid4())

    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email.lower(),
        "password_hash": hash_password(user_data.password),
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc)
    }

    await db.users.insert_one(user_doc)

    access_token = create_access_token(
        user_id,
        user_data.email
    )

    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax"
    )

    return User(
        id=user_doc["id"],
        name=user_doc["name"],
        email=user_doc["email"],
        role=user_doc["role"],
        created_at=user_doc["created_at"]
    )


@api_router.post("/auth/login", response_model=User)
async def login(
    credentials: UserLogin,
    response: Response
):
    user = await db.users.find_one({
        "email": credentials.email.lower()
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        credentials.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        user["id"],
        user["email"]
    )

    refresh_token = create_refresh_token(
        user["id"]
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax"
    )

    return User(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )


@api_router.get("/auth/me")
async def me(
    current_user: dict = Depends(get_current_user)
):
    return current_user


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {
        "message": "Logout successful"
    }

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {
        "message": "Sistema Jurídico API funcionando"
    }

# ==================== INCLUDE ROUTER ====================

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
    allow_headers=["*"],
)

# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    try:
        await seed_admin()

        await db.users.create_index(
            "email",
            unique=True
        )

        await db.users.create_index(
            "id",
            unique=True
        )

        logger.info("Banco conectado com sucesso")

    except Exception as e:
        logger.error(f"Erro no startup: {e}")

# ==================== SHUTDOWN ====================

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
