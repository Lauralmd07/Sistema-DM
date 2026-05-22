from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
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

# ==================== APP ====================

app = FastAPI()

api_router = APIRouter(prefix="/api")

# ==================== MONGODB ====================

mongo_url = os.getenv("MONGO_URL")

if not mongo_url:
    raise Exception("MONGO_URL não encontrada")

client = AsyncIOMotorClient(
    mongo_url,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=30000
)

db = client["legal_system"]

# ==================== JWT ====================

JWT_ALGORITHM = "HS256"

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    secrets.token_urlsafe(64)
)

# ==================== PASSWORD ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ==================== TOKENS ====================

def create_access_token(user_id: str, email: str):
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(days=1)
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
            detail="Não autenticado"
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
                detail="Usuário não encontrado"
            )

        user.pop("_id", None)
        user.pop("password_hash", None)

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expirado"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
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


class Process(BaseModel):
    title: str
    client: str
    status: str
    number: Optional[str] = None


class Appointment(BaseModel):
    title: str
    date: str
    description: Optional[str] = None


class Document(BaseModel):
    title: str
    type: Optional[str] = None


class Folder(BaseModel):
    name: str


class Invoice(BaseModel):
    title: str
    amount: float
    status: str

# ==================== ADMIN ====================

async def seed_admin():
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        return

    existing = await db.users.find_one({
        "email": admin_email
    })

    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Administrador",
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc)
        })

        logger.info("Admin criado com sucesso")

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):

    existing = await db.users.find_one({
        "email": user_data.email.lower()
    })

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado"
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
        secure=True,
        samesite="none",
        max_age=86400
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800
    )

    return User(
        id=user_doc["id"],
        name=user_doc["name"],
        email=user_doc["email"],
        role=user_doc["role"],
        created_at=user_doc["created_at"]
    )

@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):

    user = await db.users.find_one({
        "email": credentials.email.lower()
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
        )

    if not verify_password(
        credentials.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
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
        secure=True,
        samesite="none",
        max_age=86400
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800
    )

    return User(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )

@api_router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(response: Response):

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {
        "message": "Logout realizado"
    }

# ==================== APPOINTMENTS ====================

@api_router.get("/appointments")
async def get_appointments(
    current_user: dict = Depends(get_current_user)
):
    appointments = await db.appointments.find().to_list(100)

    for appointment in appointments:
        appointment["_id"] = str(appointment["_id"])

    return appointments

@api_router.post("/appointments")
async def create_appointment(
    appointment: Appointment,
    current_user: dict = Depends(get_current_user)
):
    appointment_doc = {
        "id": str(uuid.uuid4()),
        **appointment.dict(),
        "created_at": datetime.now(timezone.utc)
    }

    await db.appointments.insert_one(appointment_doc)

    return appointment_doc

# ==================== FINANCIAL ====================

@api_router.get("/financial")
async def get_financial(
    current_user: dict = Depends(get_current_user)
):
    records = await db.financial.find().to_list(100)

    for record in records:
        record["_id"] = str(record["_id"])

    return records

# ==================== TRUST ACCOUNTS ====================

@api_router.get("/trust-accounts")
async def trust_accounts(
    current_user: dict = Depends(get_current_user)
):
    return []

# ==================== ANALYTICS ====================

@api_router.get("/analytics/dashboard")
async def dashboard(
    current_user: dict = Depends(get_current_user)
):
    financial = await db.financial.find().to_list(100)

    total_revenue = sum(
        item.get("amount", 0)
        for item in financial
        if item.get("type") == "income"
    )

    total_expenses = sum(
        item.get("amount", 0)
        for item in financial
        if item.get("type") == "expense"
    )

    net_profit = total_revenue - total_expenses

    return {
        "kpis": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": (
                (net_profit / total_revenue) * 100
                if total_revenue > 0 else 0
            )
        },
        "monthly_trend": [],
        "alerts": {
            "overdue_invoices": 0,
            "trust_reconciliation_pending": 0
        }
    }

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {
        "message": "Sistema Jurídico API funcionando"
    }

# ==================== HEALTH ====================

@api_router.get("/health")
async def health():
    return {
        "ok": True
    }

# ==================== ROUTER ====================

app.include_router(api_router)

# ==================== CORS ====================

frontend_url = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "https://sistema-dm.vercel.app"
    ],
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
