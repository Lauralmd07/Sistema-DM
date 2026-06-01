```python
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

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# ==================== PASSWORD ====================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()

    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        salt
    )

    return hashed.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ==================== TOKEN ====================
def create_access_token(
    user_id: str,
    email: str
):
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
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

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
    role: Literal["admin", "lawyer"]
    created_at: datetime

# ==================== REGISTER ====================
@api_router.post("/auth/register", response_model=User)
async def register(
    user_data: UserCreate,
    response: Response
):
    existing_user = await db.users.find_one({
        "email": user_data.email.lower()
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_id = str(uuid.uuid4())

    hashed_password = hash_password(user_data.password)

    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email.lower(),
        "password_hash": hashed_password,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc)
    }

    await db.users.insert_one(user_doc)

    access_token = create_access_token(
        user_id,
        user_data.email
    )

    refresh_token = create_refresh_token(user_id)

    # COOKIE ACCESS TOKEN
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=900,
        path="/"
    )

    # COOKIE REFRESH TOKEN
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
        path="/"
    )

    return User(
        id=user_id,
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        created_at=user_doc["created_at"]
    )

# ==================== LOGIN ====================
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

    valid_password = verify_password(
        credentials.password,
        user["password_hash"]
    )

    if not valid_password:
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

    # ACCESS TOKEN
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=900,
        path="/"
    )

    # REFRESH TOKEN
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
        path="/"
    )

    return User(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )

# ==================== ME ====================
@api_router.get("/auth/me")
async def me(
    current_user: dict = Depends(get_current_user)
):
    return current_user

# ==================== LOGOUT ====================
@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/"
    )

    response.delete_cookie(
        key="refresh_token",
        path="/"
    )

    return {
        "message": "Logout successful"
    }

# ==================== ROOT ====================
@api_router.get("/")
async def root():
    return {
        "message": "API Online"
    }

# ==================== HEALTH ====================
@api_router.get("/health")
async def health():
    return {
        "status": "healthy"
    }

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
        await db.users.create_index(
            "email",
            unique=True
        )

        await db.users.create_index(
            "id",
            unique=True
        )

        logger.info("Indexes criados")

    except Exception as e:
        logger.warning(str(e))
```
