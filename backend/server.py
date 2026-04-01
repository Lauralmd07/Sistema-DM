from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import secrets
import base64

# Load environment variables FIRST
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'legal_system')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(64))

# ==================== PASSWORD HASHING ====================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ==================== JWT TOKEN MANAGEMENT ====================
def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ==================== AUTH HELPER ====================
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user.pop("password_hash", None)
        user.pop("_id", None)
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
    email: str
    role: Literal["admin", "lawyer"]
    created_at: datetime

class AppointmentCreate(BaseModel):
    type: Literal["lead", "return"]
    client_name: str
    phone: str
    subject: str
    date: str
    time: str
    color: Optional[str] = "#D4AF37"
    # Return fields (optional)
    cpf: Optional[str] = None
    rg: Optional[str] = None
    address: Optional[str] = None

class Appointment(AppointmentCreate):
    id: str
    lawyer_id: str
    status: str = "scheduled"
    created_at: datetime

class ProcessCreate(BaseModel):
    client_number: str
    cpf: str
    action_type: str
    description: str

class TimelineUpdate(BaseModel):
    date: str
    description: str

class Process(BaseModel):
    id: str
    client_number: str
    cpf: str
    action_type: str
    description: str
    status: Literal["new", "in_progress", "finished"] = "new"
    lawyer_id: str
    timeline: List[TimelineUpdate] = []
    judge_sentence: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProcessUpdate(BaseModel):
    status: Optional[Literal["new", "in_progress", "finished"]] = None
    timeline: Optional[List[TimelineUpdate]] = None
    judge_sentence: Optional[str] = None

class FolderCreate(BaseModel):
    name: str
    type: Literal["client", "process"]
    reference_id: str  # client_id or process_id

class Folder(BaseModel):
    id: str
    name: str
    type: Literal["client", "process"]
    reference_id: str
    created_by: str
    created_at: datetime

class Document(BaseModel):
    id: str
    folder_id: str
    filename: str
    file_type: str
    file_data: str  # base64 encoded
    uploaded_by: str
    created_at: datetime

class FinancialRecordCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float
    description: str
    category: str
    lawyer_id: Optional[str] = None
    date: str

class FinancialRecord(FinancialRecordCreate):
    id: str
    created_by: str
    created_at: datetime

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# ==================== ADMIN SEEDING ====================
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@legal.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    existing = await db.users.find_one({"email": admin_email})
    
    if existing is None:
        admin_id = str(uuid.uuid4())
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "id": admin_id,
            "email": admin_email,
            "password_hash": hashed,
            "name": "Administrador",
            "role": "admin",
            "created_at": datetime.now(timezone.utc)
        })
        logger.info(f"✅ Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
        logger.info(f"✅ Admin password updated")
    
    # Write credentials
    creds_path = Path("/app/memory/test_credentials.md")
    creds_path.parent.mkdir(exist_ok=True)
    creds_path.write_text(f"""# Test Credentials

## Admin Account
- Email: {admin_email}
- Password: {admin_password}
- Role: admin

## Auth Endpoints
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/refresh
- POST /api/auth/forgot-password
- POST /api/auth/reset-password
""")

# ==================== AUTH ENDPOINTS ====================
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, response: Response):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed = hash_password(user_data.password)
    
    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email.lower(),
        "password_hash": hashed,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.users.insert_one(user_doc)
    
    # Create tokens
    access_token = create_access_token(user_id, user_data.email)
    refresh_token = create_refresh_token(user_id)
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
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

@api_router.post("/auth/login", response_model=User)
async def login(credentials: UserLogin, response: Response, request: Request):
    # Find user
    user = await db.users.find_one({"email": credentials.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
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

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(**current_user)

# ==================== USER ENDPOINTS ====================
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

# ==================== APPOINTMENT ENDPOINTS ====================
@api_router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    appointment_id = str(uuid.uuid4())
    
    appointment_doc = {
        "id": appointment_id,
        **appointment.model_dump(),
        "lawyer_id": current_user["id"],
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.appointments.insert_one(appointment_doc)
    return Appointment(**appointment_doc)

@api_router.get("/appointments", response_model=List[Appointment])
async def get_appointments(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] != "admin":
        query["lawyer_id"] = current_user["id"]
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(1000)
    return appointments

@api_router.get("/appointments/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if current_user["role"] != "admin" and appointment["lawyer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return appointment

@api_router.put("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment_data: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if current_user["role"] != "admin" and appointment["lawyer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": appointment_data.model_dump()}
    )
    
    updated = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    return updated

@api_router.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if current_user["role"] != "admin" and appointment["lawyer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.appointments.delete_one({"id": appointment_id})
    return {"message": "Appointment deleted"}

# ==================== PROCESS ENDPOINTS ====================
@api_router.post("/processes", response_model=Process)
async def create_process(process: ProcessCreate, current_user: dict = Depends(get_current_user)):
    process_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    process_doc = {
        "id": process_id,
        **process.model_dump(),
        "status": "new",
        "lawyer_id": current_user["id"],
        "timeline": [],
        "judge_sentence": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.processes.insert_one(process_doc)
    return Process(**process_doc)

@api_router.get("/processes", response_model=List[Process])
async def get_processes(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] != "admin":
        query["lawyer_id"] = current_user["id"]
    
    processes = await db.processes.find(query, {"_id": 0}).to_list(1000)
    return processes

@api_router.get("/processes/{process_id}", response_model=Process)
async def get_process(process_id: str, current_user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    if current_user["role"] != "admin" and process["lawyer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return process

@api_router.put("/processes/{process_id}", response_model=Process)
async def update_process(process_id: str, process_data: ProcessUpdate, current_user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    if current_user["role"] != "admin" and process["lawyer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_fields = {k: v for k, v in process_data.model_dump().items() if v is not None}
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    await db.processes.update_one(
        {"id": process_id},
        {"$set": update_fields}
    )
    
    updated = await db.processes.find_one({"id": process_id}, {"_id": 0})
    return updated

@api_router.delete("/processes/{process_id}")
async def delete_process(process_id: str, current_user: dict = Depends(get_current_user)):
    process = await db.processes.find_one({"id": process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.processes.delete_one({"id": process_id})
    return {"message": "Process deleted"}

# ==================== FOLDER ENDPOINTS ====================
@api_router.post("/folders", response_model=Folder)
async def create_folder(folder: FolderCreate, current_user: dict = Depends(get_current_user)):
    folder_id = str(uuid.uuid4())
    
    folder_doc = {
        "id": folder_id,
        **folder.model_dump(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.folders.insert_one(folder_doc)
    return Folder(**folder_doc)

@api_router.get("/folders", response_model=List[Folder])
async def get_folders(current_user: dict = Depends(get_current_user)):
    folders = await db.folders.find({}, {"_id": 0}).to_list(1000)
    return folders

@api_router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: dict = Depends(get_current_user)):
    folder = await db.folders.find_one({"id": folder_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    await db.folders.delete_one({"id": folder_id})
    await db.documents.delete_many({"folder_id": folder_id})
    return {"message": "Folder and documents deleted"}

# ==================== DOCUMENT ENDPOINTS ====================
@api_router.post("/documents/upload", response_model=Document)
async def upload_document(
    folder_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Check folder exists
    folder = await db.folders.find_one({"id": folder_id})
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Read file and encode to base64
    content = await file.read()
    file_data = base64.b64encode(content).decode('utf-8')
    
    document_id = str(uuid.uuid4())
    document_doc = {
        "id": document_id,
        "folder_id": folder_id,
        "filename": file.filename,
        "file_type": file.content_type,
        "file_data": file_data,
        "uploaded_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.documents.insert_one(document_doc)
    return Document(**document_doc)

@api_router.get("/documents", response_model=List[Document])
async def get_documents(folder_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if folder_id:
        query["folder_id"] = folder_id
    
    documents = await db.documents.find(query, {"_id": 0}).to_list(1000)
    return documents

@api_router.get("/documents/{document_id}")
async def get_document(document_id: str, current_user: dict = Depends(get_current_user)):
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    document = await db.documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if current_user["role"] != "admin" and document["uploaded_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.documents.delete_one({"id": document_id})
    return {"message": "Document deleted"}

# ==================== FINANCIAL ENDPOINTS ====================
@api_router.post("/financial", response_model=FinancialRecord)
async def create_financial_record(record: FinancialRecordCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    record_id = str(uuid.uuid4())
    record_doc = {
        "id": record_id,
        **record.model_dump(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.financial_records.insert_one(record_doc)
    return FinancialRecord(**record_doc)

@api_router.get("/financial", response_model=List[FinancialRecord])
async def get_financial_records(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    records = await db.financial_records.find({}, {"_id": 0}).to_list(1000)
    return records

@api_router.get("/financial/stats")
async def get_financial_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    records = await db.financial_records.find({}, {"_id": 0}).to_list(10000)
    
    total_income = sum(r["amount"] for r in records if r["type"] == "income")
    total_expense = sum(r["amount"] for r in records if r["type"] == "expense")
    profit = total_income - total_expense
    
    # Monthly breakdown
    monthly_data = {}
    for record in records:
        month = record["date"][:7]  # YYYY-MM
        if month not in monthly_data:
            monthly_data[month] = {"income": 0, "expense": 0}
        monthly_data[month][record["type"]] += record["amount"]
    
    monthly_stats = [
        {
            "month": month,
            "income": data["income"],
            "expense": data["expense"],
            "profit": data["income"] - data["expense"]
        }
        for month, data in sorted(monthly_data.items())
    ]
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": profit,
        "monthly_stats": monthly_stats
    }

@api_router.delete("/financial/{record_id}")
async def delete_financial_record(record_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await db.financial_records.delete_one({"id": record_id})
    return {"message": "Financial record deleted"}

# Include the router in the main app
app.include_router(api_router)

# CORS Configuration
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Startup event
@app.on_event("startup")
async def startup_event():
    await seed_admin()
    # Create indexes
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("id", unique=True)
        logger.info("✅ Database indexes created")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
