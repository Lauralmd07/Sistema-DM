from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import Literal, Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
import uuid
import base64
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import secrets
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "legal_system")]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_urlsafe(64))
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, email: str):
    payload = {"sub": user_id, "email": email, "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str):
    payload = {"sub": user_id, "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, user_id: str, email: str):
    response.set_cookie(key="access_token", value=create_access_token(user_id, email), httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=create_refresh_token(user_id), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
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


class ClientCreate(BaseModel):
    full_name: str
    identification_number: str
    identification_type: str = "CPF"
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    process_number: Optional[str] = None
    notes: Optional[str] = None


@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):
    email = user_data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    user_doc = {"id": user_id, "name": user_data.name, "email": email, "password_hash": hash_password(user_data.password), "role": user_data.role, "created_at": created_at}
    await db.users.insert_one(user_doc)
    set_auth_cookies(response, user_id, email)
    return User(id=user_id, name=user_data.name, email=email, role=user_data.role, created_at=created_at)


@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response):
    email = credentials.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    password_hash = user.get("password_hash")
    if not password_hash:
        raise HTTPException(status_code=401, detail="Esta conta usa o login com Google. Entre com Google.")
    if not verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    set_auth_cookies(response, user["id"], user["email"])
    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])


@api_router.post("/auth/google", response_model=User)
async def google_login(data: GoogleLogin, response: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Login com Google não está configurado no servidor")
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
    set_auth_cookies(response, user["id"], user["email"])
    return User(id=user["id"], name=user["name"], email=user["email"], role=user["role"], created_at=user["created_at"])


@api_router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logout successful"}


# ==================== CLIENTES ====================
@api_router.get("/clients")
async def list_clients(current_user: dict = Depends(get_current_user)):
    cursor = db.clients.find({"owner_id": current_user["id"]}).sort("full_name", 1)
    clients = []
    async for item in cursor:
        item.pop("_id", None)
        clients.append(item)
    return clients


@api_router.post("/clients")
async def create_client(data: ClientCreate, current_user: dict = Depends(get_current_user)):
    client_doc = data.model_dump()
    client_doc.update({"id": str(uuid.uuid4()), "owner_id": current_user["id"], "created_at": datetime.now(timezone.utc)})
    await db.clients.insert_one(client_doc)
    client_doc.pop("_id", None)
    return client_doc


@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientCreate, current_user: dict = Depends(get_current_user)):
    result = await db.clients.update_one({"id": client_id, "owner_id": current_user["id"]}, {"$set": data.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return await db.clients.find_one({"id": client_id}, {"_id": 0})


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "owner_id": current_user["id"]})
    if result.deleted_count == 0:
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
    doc = {"id": str(uuid.uuid4()), "client_id": client_id, "owner_id": current_user["id"], "filename": file.filename, "file_type": file.content_type or "application/octet-stream", "file_size": len(content), "file_data": base64.b64encode(content).decode("ascii"), "created_at": datetime.now(timezone.utc)}
    await db.client_documents.insert_one(doc)
    result = dict(doc)
    result.pop("_id", None)
    result.pop("file_data", None)
    return result


@api_router.get("/clients/{client_id}/documents/{document_id}")
async def get_client_document(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.client_documents.find_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc


@api_router.delete("/clients/{client_id}/documents/{document_id}")
async def delete_client_document(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.client_documents.delete_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"success": True}


@api_router.get("/")
async def root():
    return {"message": "API Online"}


@api_router.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(api_router)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(CORSMiddleware, allow_origins=[frontend_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup_event():
    logger.info("Servidor iniciado")
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        await db.users.create_index("google_sub", unique=True, sparse=True)
        await db.clients.create_index([("owner_id", 1), ("full_name", 1)])
        await db.client_documents.create_index([("owner_id", 1), ("client_id", 1), ("created_at", -1)])
    except Exception as e:
        logger.warning(str(e))
