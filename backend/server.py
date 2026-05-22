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


# ==================== ADMIN SEED ====================

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

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
        secure=True,
        samesite="none"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none"
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
        secure=True,
        samesite="none"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none"
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

# ==================== PROCESSOS ====================

@api_router.get("/processes")
async def get_processes(
    current_user: dict = Depends(get_current_user)
):
    processes = await db.processes.find().to_list(100)

    for process in processes:
        process["_id"] = str(process["_id"])

    return processes


@api_router.post("/processes")
async def create_process(
    process: Process,
    current_user: dict = Depends(get_current_user)
):
    process_doc = {
        "id": str(uuid.uuid4()),
        **process.dict(),
        "created_at": datetime.now(timezone.utc)
    }

    await db.processes.insert_one(process_doc)

    return process_doc

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

# ==================== DOCUMENTS ====================

@api_router.get("/documents")
async def get_documents(
    current_user: dict = Depends(get_current_user)
):
    documents = await db.documents.find().to_list(100)

    for document in documents:
        document["_id"] = str(document["_id"])

    return documents


@api_router.post("/documents")
async def create_document(
    document: Document,
    current_user: dict = Depends(get_current_user)
):
    document_doc = {
        "id": str(uuid.uuid4()),
        **document.dict(),
        "created_at": datetime.now(timezone.utc)
    }

    await db.documents.insert_one(document_doc)

    return document_doc

# ==================== FOLDERS ====================

@api_router.get("/folders")
async def get_folders(
    current_user: dict = Depends(get_current_user)
):
    folders = await db.folders.find().to_list(100)

    for folder in folders:
        folder["_id"] = str(folder["_id"])

    return folders


@api_router.post("/folders")
async def create_folder(
    folder: Folder,
    current_user: dict = Depends(get_current_user)
):
    folder_doc = {
        "id": str(uuid.uuid4()),
        **folder.dict(),
        "created_at": datetime.now(timezone.utc)
    }

    await db.folders.insert_one(folder_doc)

    return folder_doc

# ==================== INVOICES ====================

@api_router.get("/invoices")
async def get_invoices(
    current_user: dict = Depends(get_current_user)
):
    invoices = await db.invoices.find().to_list(100)

    for invoice in invoices:
        invoice["_id"] = str(invoice["_id"])

    return invoices


@api_router.post("/invoices")
async def create_invoice(
    invoice: Invoice,
    current_user: dict = Depends(get_current_user)
):
    invoice_doc = {
        "id": str(uuid.uuid4()),
        **invoice.dict(),
        "created_at": datetime.now(timezone.utc)
    }

    await db.invoices.insert_one(invoice_doc)

    return invoice_doc

# ==================== FINANCIAL ====================

@api_router.get("/financial")
async def get_financial(
    current_user: dict = Depends(get_current_user)
):
    invoices = await db.invoices.find().to_list(100)

    total_income = sum(
        invoice.get("amount", 0)
        for invoice in invoices
        if invoice.get("status") == "paid"
    )

    pending = sum(
        invoice.get("amount", 0)
        for invoice in invoices
        if invoice.get("status") != "paid"
    )

    return {
        "income": total_income,
        "pending": pending,
        "totalInvoices": len(invoices)
    }

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
    users_count = await db.users.count_documents({})
    processes_count = await db.processes.count_documents({})
    documents_count = await db.documents.count_documents({})
    appointments_count = await db.appointments.count_documents({})

    return {
        "users": users_count,
        "processes": processes_count,
        "documents": documents_count,
        "appointments": appointments_count
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

# ==================== INCLUDE ROUTER ====================

app.include_router(api_router)

# ==================== CORS ====================

frontend_url = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:3000"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url
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
