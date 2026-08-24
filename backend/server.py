from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal, Optional
import base64
import logging
import os
import secrets
import uuid
from urllib.parse import urlparse

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ.get("MONGO_URL", "").strip()
if not mongo_url:
    raise RuntimeError("MONGO_URL is not configured")

db_name = os.environ.get("DB_NAME", "legal_system").strip() or "legal_system"
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000, maxPoolSize=50, minPoolSize=1)
db = client[db_name]

JWT_SECRET = os.environ.get("JWT_SECRET", "").strip() or secrets.token_urlsafe(64)
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

app = FastAPI(title="Sistema DM API", version="1.3.1")
app.state.db = db
app.state.jwt_secret = JWT_SECRET
api_router = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str):
    return jwt.encode({"sub": user_id, "email": email, "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str):
    return jwt.encode({"sub": user_id, "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")


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
            raise HTTPException(status_code=401, detail="Invalid access token")
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


async def json_body(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError
        return body
    except Exception:
        raise HTTPException(status_code=422, detail="JSON inválido")


def clean(doc):
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=20)


class User(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "lawyer"]
    created_at: datetime


class ClientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    identification_number: str = Field(min_length=1, max_length=50)
    identification_type: str = "CPF"
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    process_number: Optional[str] = None
    notes: Optional[str] = None


@api_router.get("/config")
async def public_config():
    # OAuth client IDs are public browser configuration, not secrets.
    return {"google_client_id": GOOGLE_CLIENT_ID or None}


@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):
    email = str(user_data.email).lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    user_doc = {"id": user_id, "name": user_data.name.strip(), "email": email, "password_hash": hash_password(user_data.password), "role": "lawyer", "created_at": created_at, "auth_provider": "password"}
    await db.users.insert_one(user_doc)
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return User(id=user_id, name=user_doc["name"], email=email, role="lawyer", created_at=created_at)


@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):
    email = str(credentials.email).lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    set_auth_cookies(response, create_access_token(user["id"], user["email"]), create_refresh_token(user["id"]))
    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])


@api_router.post("/auth/google", response_model=User)
async def google_login(data: GoogleLogin, response: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Login com Google não está configurado no servidor")
    try:
        google_user = id_token.verify_oauth2_token(data.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido ou expirado")
    email = str(google_user.get("email", "")).lower()
    google_sub = google_user.get("sub")
    if not email or not google_sub or not google_user.get("email_verified", False):
        raise HTTPException(status_code=401, detail="A conta do Google não possui um e-mail verificado")
    user = await db.users.find_one({"google_sub": google_sub}) or await db.users.find_one({"email": email})
    if user:
        existing_google_sub = user.get("google_sub")
        if existing_google_sub and existing_google_sub != google_sub:
            raise HTTPException(status_code=409, detail="Esta conta já está vinculada a outra conta Google")
        await db.users.update_one({"id": user["id"]}, {"$set": {"google_sub": google_sub, "auth_provider": "google"}})
        user["google_sub"] = google_sub
    else:
        user = {"id": str(uuid.uuid4()), "name": google_user.get("name") or email.split("@")[0], "email": email, "google_sub": google_sub, "auth_provider": "google", "role": "lawyer", "created_at": datetime.now(timezone.utc)}
        await db.users.insert_one(user.copy())
    set_auth_cookies(response, create_access_token(user["id"], user["email"]), create_refresh_token(user["id"]))
    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])


@api_router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        response.set_cookie("access_token", create_access_token(user["id"], user["email"]), httponly=True, secure=True, samesite="none", max_age=900, path="/")
        return {"success": True}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token inválido")


@api_router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@api_router.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logout successful"}


@api_router.get("/clients")
async def list_clients(current_user: dict = Depends(get_current_user)):
    return [clean(x) async for x in db.clients.find({"owner_id": current_user["id"]}).sort("full_name", 1)]


@api_router.post("/clients")
async def create_client(data: ClientCreate, current_user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc.update({"id": str(uuid.uuid4()), "owner_id": current_user["id"], "created_at": datetime.now(timezone.utc)})
    await db.clients.insert_one(doc)
    return clean(doc)


@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientCreate, current_user: dict = Depends(get_current_user)):
    result = await db.clients.update_one({"id": client_id, "owner_id": current_user["id"]}, {"$set": data.model_dump()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return clean(await db.clients.find_one({"id": client_id, "owner_id": current_user["id"]}))


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    await db.client_documents.delete_many({"client_id": client_id, "owner_id": current_user["id"]})
    return {"success": True}


@api_router.get("/clients/{client_id}/documents")
async def list_client_documents(client_id: str, current_user: dict = Depends(get_current_user)):
    if not await db.clients.find_one({"id": client_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cursor = db.client_documents.find({"client_id": client_id, "owner_id": current_user["id"]}, {"_id": 0, "file_data": 0}).sort("created_at", -1)
    return await cursor.to_list(length=500)


@api_router.post("/clients/{client_id}/documents")
async def upload_client_document(client_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not await db.clients.find_one({"id": client_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Arquivo maior que 15 MB")
    doc = {"id": str(uuid.uuid4()), "client_id": client_id, "owner_id": current_user["id"], "filename": file.filename or "arquivo", "file_type": file.content_type or "application/octet-stream", "file_size": len(content), "file_data": base64.b64encode(content).decode("ascii"), "created_at": datetime.now(timezone.utc)}
    await db.client_documents.insert_one(doc)
    return {k: v for k, v in clean(dict(doc)).items() if k != "file_data"}


@api_router.get("/clients/{client_id}/documents/{document_id}")
async def get_client_document(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.client_documents.find_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc


@api_router.delete("/clients/{client_id}/documents/{document_id}")
async def delete_client_document(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.client_documents.delete_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"success": True}


@api_router.get("/appointments")
async def legacy_appointments_get(current_user: dict = Depends(get_current_user)):
    return [clean(x) async for x in db.appointments.find({"owner_id": current_user["id"]}).sort([("date", 1), ("time", 1)])]


@api_router.post("/appointments")
async def legacy_appointments_post(request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    required = ["type", "client_name", "subject", "date", "time"]
    missing = [x for x in required if not data.get(x)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Campos obrigatórios: {', '.join(missing)}")
    doc = {**data, "id": str(uuid.uuid4()), "owner_id": current_user["id"], "created_at": datetime.now(timezone.utc)}
    await db.appointments.insert_one(doc)
    return clean(doc)


@api_router.put("/appointments/{appointment_id}")
async def legacy_appointments_put(appointment_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    data.pop("id", None)
    data.pop("owner_id", None)
    data.pop("created_at", None)
    result = await db.appointments.update_one({"id": appointment_id, "owner_id": current_user["id"]}, {"$set": data})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    return clean(await db.appointments.find_one({"id": appointment_id, "owner_id": current_user["id"]}))


@api_router.delete("/appointments/{appointment_id}")
async def legacy_appointments_delete(appointment_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.appointments.delete_one({"id": appointment_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    return {"success": True}


@api_router.get("/processes")
async def legacy_processes_get(current_user: dict = Depends(get_current_user)):
    return [clean(x) async for x in db.processes.find({"owner_id": current_user["id"]}).sort("created_at", -1)]


@api_router.post("/processes")
async def legacy_processes_post(request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    required = ["client_number", "cpf", "action_type", "description"]
    missing = [x for x in required if not data.get(x)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Campos obrigatórios: {', '.join(missing)}")
    data["status"] = data.get("status") if data.get("status") in {"new", "in_progress", "finished"} else "new"
    data.setdefault("timeline", [])
    data.setdefault("judge_sentence", "")
    now = datetime.now(timezone.utc)
    doc = {**data, "id": str(uuid.uuid4()), "owner_id": current_user["id"], "created_at": now, "updated_at": now}
    await db.processes.insert_one(doc)
    return clean(doc)


@api_router.put("/processes/{process_id}")
async def legacy_processes_put(process_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    data.pop("id", None)
    data.pop("owner_id", None)
    data.pop("created_at", None)
    if "status" in data and data["status"] not in {"new", "in_progress", "finished"}:
        raise HTTPException(status_code=422, detail="Status de processo inválido")
    data["updated_at"] = datetime.now(timezone.utc)
    result = await db.processes.update_one({"id": process_id, "owner_id": current_user["id"]}, {"$set": data})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return clean(await db.processes.find_one({"id": process_id, "owner_id": current_user["id"]}))


@api_router.delete("/processes/{process_id}")
async def legacy_processes_delete(process_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.processes.delete_one({"id": process_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return {"success": True}


@api_router.get("/folders")
async def list_folders(current_user: dict = Depends(get_current_user)):
    return [clean(x) async for x in db.folders.find({"owner_id": current_user["id"]}).sort("created_at", -1)]


@api_router.post("/folders")
async def create_folder(request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    name = str(data.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nome da pasta é obrigatório")
    doc = {"id": str(uuid.uuid4()), "name": name, "owner_id": current_user["id"], "created_at": datetime.now(timezone.utc)}
    await db.folders.insert_one(doc)
    return clean(doc)


@api_router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.folders.delete_one({"id": folder_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    await db.documents.delete_many({"folder_id": folder_id, "owner_id": current_user["id"]})
    return {"success": True}


@api_router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    cursor = db.documents.find({"owner_id": current_user["id"]}, {"_id": 0, "file_data": 0}).sort("created_at", -1)
    return await cursor.to_list(length=1000)


@api_router.post("/documents/upload")
async def upload_document(folder_id: str = Form(...), file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not await db.folders.find_one({"id": folder_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Arquivo maior que 15 MB")
    doc = {"id": str(uuid.uuid4()), "folder_id": folder_id, "owner_id": current_user["id"], "filename": file.filename or "arquivo", "file_type": file.content_type or "application/octet-stream", "file_size": len(content), "file_data": base64.b64encode(content).decode("ascii"), "created_at": datetime.now(timezone.utc)}
    await db.documents.insert_one(doc)
    return {k: v for k, v in clean(dict(doc)).items() if k != "file_data"}


@api_router.get("/documents/{document_id}")
async def get_document(document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": document_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc


@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.documents.delete_one({"id": document_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"success": True}


async def financial_records():
    return await db.financial_records.find({}, {"_id": 0}).sort("date", -1).to_list(length=5000)


@api_router.get("/financial")
async def list_financial(current_user: dict = Depends(get_current_user)):
    return await financial_records()


@api_router.post("/financial")
async def create_financial(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Somente o administrador pode alterar o financeiro")
    data = await json_body(request)
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Valor financeiro inválido")
    if amount < 0:
        raise HTTPException(status_code=422, detail="Valor financeiro não pode ser negativo")
    if data.get("type") not in ("income", "expense") or not str(data.get("description", "")).strip() or not data.get("date"):
        raise HTTPException(status_code=422, detail="Tipo, descrição e data são obrigatórios")
    doc = {**data, "amount": amount, "id": str(uuid.uuid4()), "owner_id": current_user["id"], "created_at": datetime.now(timezone.utc)}
    await db.financial_records.insert_one(doc)
    return clean(doc)


@api_router.delete("/financial/{record_id}")
async def delete_financial(record_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Somente o administrador pode alterar o financeiro")
    result = await db.financial_records.delete_one({"id": record_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Registro financeiro não encontrado")
    return {"success": True}


@api_router.get("/trust-accounts")
async def list_trust_accounts(current_user: dict = Depends(get_current_user)):
    return await db.trust_accounts.find({}, {"_id": 0}).to_list(length=1000)


@api_router.get("/analytics/dashboard")
async def analytics_dashboard(current_user: dict = Depends(get_current_user)):
    records = await financial_records()
    income = sum(float(x.get("amount", 0) or 0) for x in records if x.get("type") == "income")
    expense = sum(float(x.get("amount", 0) or 0) for x in records if x.get("type") == "expense")
    profit = income - expense
    margin = (profit / income * 100) if income else 0
    by_month = {}
    for record in records:
        month = str(record.get("date", ""))[:7]
        if not month:
            continue
        bucket = by_month.setdefault(month, {"income": 0.0, "expense": 0.0})
        if record.get("type") in bucket:
            bucket[record["type"]] += float(record.get("amount", 0) or 0)
    monthly_trend = []
    for month, values in sorted(by_month.items()):
        month_profit = values["income"] - values["expense"]
        monthly_trend.append({"month": month, "income": values["income"], "expense": values["expense"], "revenue": values["income"], "expenses": values["expense"], "profit": month_profit})
    return {"kpis": {"total_income": income, "total_expenses": expense, "balance": profit, "income": income, "expenses": expense, "total_revenue": income, "net_profit": profit, "profit_margin": margin}, "monthly_trend": monthly_trend, "alerts": {"overdue_financial": 0, "trust_reconciliation_pending": 0}}


@api_router.get("/")
async def root():
    return {"message": "API Online", "version": "1.3.1"}


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"ok": True, "status": "healthy", "database": "connected"}
    except Exception as exc:
        logger.exception("Database health check failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc.__class__.__name__}")


app.include_router(api_router)

frontend_url = os.environ.get("FRONTEND_URL", "https://lauralmd07.github.io,https://sistema-dm.onrender.com,https://sistema-dm-1.onrender.com,http://localhost:3000,http://localhost:5173")

def normalize_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return value

allowed_origins = list(dict.fromkeys(normalize_origin(origin) for origin in frontend_url.split(",") if origin.strip()))
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization", "X-Requested-With"])


@app.on_event("startup")
async def startup_event():
    logger.info("Servidor iniciado")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.users.create_index("google_sub", unique=True, sparse=True)
    await db.clients.create_index([("owner_id", 1), ("full_name", 1)])
    await db.client_documents.create_index([("owner_id", 1), ("client_id", 1), ("created_at", -1)])
    await db.appointments.create_index([("owner_id", 1), ("date", 1), ("time", 1)])
    await db.processes.create_index([("owner_id", 1), ("status", 1)])
    await db.deadlines.create_index([("owner_id", 1), ("date", 1), ("time", 1)])
    await db.folders.create_index([("owner_id", 1), ("created_at", -1)])
    await db.documents.create_index([("owner_id", 1), ("folder_id", 1), ("created_at", -1)])
    await db.financial_records.create_index([("date", -1)])

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_password:
        if len(admin_password) < 8:
            logger.warning("ADMIN_PASSWORD is too short; admin bootstrap skipped")
        elif not await db.users.find_one({"email": admin_email}):
            admin = {"id": str(uuid.uuid4()), "name": os.environ.get("ADMIN_NAME", "Administrador").strip() or "Administrador", "email": admin_email, "password_hash": hash_password(admin_password), "role": "admin", "created_at": datetime.now(timezone.utc), "auth_provider": "password"}
            await db.users.insert_one(admin)
            logger.info("Admin account bootstrapped from environment")


@app.on_event("shutdown")
async def shutdown_event():
    client.close()
