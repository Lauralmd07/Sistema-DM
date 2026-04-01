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

# ==================== ADVANCED FINANCIAL MODELS ====================

# Time Entry Model
class TimeEntryCreate(BaseModel):
    client_id: str
    process_id: Optional[str] = None
    date: str
    duration: int  # minutes
    description: str
    billable: bool = True
    hourly_rate: float

class TimeEntry(TimeEntryCreate):
    id: str
    lawyer_id: str
    amount: float
    status: Literal["draft", "approved", "invoiced", "paid"] = "draft"
    created_at: datetime

# Invoice Models
class InvoiceLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class TaxBreakdown(BaseModel):
    name: str
    rate: float
    amount: float

class FiscalNotes(BaseModel):
    nfe_number: Optional[str] = None
    nfse_number: Optional[str] = None
    issued: bool = False

class InvoiceCreate(BaseModel):
    client_id: str
    issue_date: str
    due_date: str
    line_items: List[InvoiceLineItem]
    discount: Optional[float] = 0
    notes: Optional[str] = None

class Invoice(BaseModel):
    id: str
    invoice_number: str
    client_id: str
    client_name: str
    issue_date: str
    due_date: str
    line_items: List[InvoiceLineItem]
    subtotal: float
    taxes: List[TaxBreakdown]
    discount: float
    total: float
    status: Literal["draft", "sent", "viewed", "partial", "paid", "overdue", "cancelled"]
    paid_amount: float
    balance: float
    fiscal_notes: FiscalNotes
    created_at: datetime
    created_by: str

# Payment Models
class PaymentCreate(BaseModel):
    invoice_id: str
    date: str
    amount: float
    method: Literal["credit_card", "bank_transfer", "pix", "check", "cash"]
    payer_name: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

class Payment(PaymentCreate):
    id: str
    reconciled: bool = False
    reconciled_by: Optional[str] = None
    reconciled_date: Optional[datetime] = None
    created_at: datetime

# Trust Account Models
class TrustAccountBalance(BaseModel):
    available: float
    reserved: float
    interest: float

class TrustAccountReconciliation(BaseModel):
    last_date: Optional[str] = None
    status: Literal["matched", "discrepancy", "pending"] = "pending"
    next_due: str

class TrustAccountCreate(BaseModel):
    client_id: str
    account_number: str
    bank_name: str
    initial_balance: float = 0

class TrustAccount(BaseModel):
    id: str
    client_id: str
    client_name: str
    account_number: str
    bank_name: str
    balance: TrustAccountBalance
    reconciliation: TrustAccountReconciliation
    created_at: datetime
    created_by: str

class TrustTransactionCreate(BaseModel):
    trust_account_id: str
    type: Literal["deposit", "withdrawal", "interest", "fee"]
    amount: float
    description: str
    date: str
    reference: Optional[str] = None

class TrustTransaction(TrustTransactionCreate):
    id: str
    balance_after: float
    created_at: datetime
    created_by: str

# Enhanced Expense Model
class ExpenseCreate(BaseModel):
    date: str
    category: str
    description: str
    amount: float
    allocation_type: Literal["firm", "client", "process"]
    reference_id: Optional[str] = None
    billable: bool = False
    tax_deductible: bool = True
    receipt_file_id: Optional[str] = None

class Expense(ExpenseCreate):
    id: str
    status: Literal["pending", "approved", "rejected", "reimbursed"] = "pending"
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    created_by: str
    created_at: datetime

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

# ==================== TIME ENTRY ENDPOINTS ====================
@api_router.post("/time-entries", response_model=TimeEntry)
async def create_time_entry(entry: TimeEntryCreate, current_user: dict = Depends(get_current_user)):
    entry_id = str(uuid.uuid4())
    amount = (entry.duration / 60) * entry.hourly_rate
    
    entry_doc = {
        "id": entry_id,
        **entry.model_dump(),
        "lawyer_id": current_user["id"],
        "amount": amount,
        "status": "draft",
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.time_entries.insert_one(entry_doc)
    return TimeEntry(**entry_doc)

@api_router.get("/time-entries", response_model=List[TimeEntry])
async def get_time_entries(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if current_user["role"] != "admin":
        query["lawyer_id"] = current_user["id"]
    if client_id:
        query["client_id"] = client_id
    if status:
        query["status"] = status
    
    entries = await db.time_entries.find(query, {"_id": 0}).to_list(1000)
    return entries

@api_router.put("/time-entries/{entry_id}/status")
async def update_time_entry_status(
    entry_id: str,
    status: Literal["draft", "approved", "invoiced", "paid"],
    current_user: dict = Depends(get_current_user)
):
    entry = await db.time_entries.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    await db.time_entries.update_one(
        {"id": entry_id},
        {"$set": {"status": status}}
    )
    
    updated = await db.time_entries.find_one({"id": entry_id}, {"_id": 0})
    return updated

# ==================== INVOICE ENDPOINTS ====================
@api_router.post("/invoices", response_model=Invoice)
async def create_invoice(invoice_data: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    invoice_id = str(uuid.uuid4())
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Get client info
    client = await db.users.find_one({"id": invoice_data.client_id})
    client_name = client["name"] if client else "Cliente Desconhecido"
    
    # Calculate totals
    subtotal = sum(item.amount for item in invoice_data.line_items)
    
    # Calculate taxes (example: 5% ISS)
    taxes = [TaxBreakdown(name="ISS", rate=5.0, amount=subtotal * 0.05)]
    tax_total = sum(tax.amount for tax in taxes)
    
    total = subtotal + tax_total - invoice_data.discount
    
    invoice_doc = {
        "id": invoice_id,
        "invoice_number": invoice_number,
        "client_id": invoice_data.client_id,
        "client_name": client_name,
        "issue_date": invoice_data.issue_date,
        "due_date": invoice_data.due_date,
        "line_items": [item.model_dump() for item in invoice_data.line_items],
        "subtotal": subtotal,
        "taxes": [tax.model_dump() for tax in taxes],
        "discount": invoice_data.discount,
        "total": total,
        "status": "draft",
        "paid_amount": 0,
        "balance": total,
        "fiscal_notes": {"nfe_number": None, "nfse_number": None, "issued": False},
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"]
    }
    
    await db.invoices.insert_one(invoice_doc)
    return Invoice(**invoice_doc)

@api_router.get("/invoices", response_model=List[Invoice])
async def get_invoices(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(1000)
    return invoices

@api_router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@api_router.put("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    status: Literal["draft", "sent", "viewed", "partial", "paid", "overdue", "cancelled"],
    current_user: dict = Depends(get_current_user)
):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"status": status}}
    )
    
    updated = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    return updated

# ==================== PAYMENT ENDPOINTS ====================
@api_router.post("/payments", response_model=Payment)
async def create_payment(payment_data: PaymentCreate, current_user: dict = Depends(get_current_user)):
    payment_id = str(uuid.uuid4())
    
    # Update invoice
    invoice = await db.invoices.find_one({"id": payment_data.invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    new_paid_amount = invoice["paid_amount"] + payment_data.amount
    new_balance = invoice["total"] - new_paid_amount
    
    # Determine new status
    if new_balance <= 0:
        new_status = "paid"
    elif new_paid_amount > 0:
        new_status = "partial"
    else:
        new_status = invoice["status"]
    
    payment_doc = {
        "id": payment_id,
        **payment_data.model_dump(),
        "reconciled": False,
        "reconciled_by": None,
        "reconciled_date": None,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.payments.insert_one(payment_doc)
    
    await db.invoices.update_one(
        {"id": payment_data.invoice_id},
        {
            "$set": {
                "paid_amount": new_paid_amount,
                "balance": new_balance,
                "status": new_status
            }
        }
    )
    
    return Payment(**payment_doc)

@api_router.get("/payments")
async def get_payments(invoice_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    payments = await db.payments.find(query, {"_id": 0}).to_list(1000)
    return payments

# ==================== TRUST ACCOUNT ENDPOINTS ====================
@api_router.post("/trust-accounts", response_model=TrustAccount)
async def create_trust_account(account_data: TrustAccountCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    account_id = str(uuid.uuid4())
    
    # Get client info
    client = await db.users.find_one({"id": account_data.client_id})
    client_name = client["name"] if client else "Cliente Desconhecido"
    
    # Calculate next reconciliation date (30 days from now)
    next_due = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%d')
    
    account_doc = {
        "id": account_id,
        "client_id": account_data.client_id,
        "client_name": client_name,
        "account_number": account_data.account_number,
        "bank_name": account_data.bank_name,
        "balance": {
            "available": account_data.initial_balance,
            "reserved": 0,
            "interest": 0
        },
        "reconciliation": {
            "last_date": None,
            "status": "pending",
            "next_due": next_due
        },
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"]
    }
    
    await db.trust_accounts.insert_one(account_doc)
    return TrustAccount(**account_doc)

@api_router.get("/trust-accounts", response_model=List[TrustAccount])
async def get_trust_accounts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    accounts = await db.trust_accounts.find({}, {"_id": 0}).to_list(1000)
    return accounts

@api_router.get("/trust-accounts/{account_id}", response_model=TrustAccount)
async def get_trust_account(account_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    account = await db.trust_accounts.find_one({"id": account_id}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="Trust account not found")
    return account

@api_router.post("/trust-accounts/{account_id}/transactions", response_model=TrustTransaction)
async def create_trust_transaction(
    account_id: str,
    transaction_data: TrustTransactionCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    account = await db.trust_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Trust account not found")
    
    transaction_id = str(uuid.uuid4())
    
    # Calculate new balance
    current_balance = account["balance"]["available"]
    if transaction_data.type in ["deposit", "interest"]:
        new_balance = current_balance + transaction_data.amount
    else:  # withdrawal, fee
        new_balance = current_balance - transaction_data.amount
    
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    transaction_doc = {
        "id": transaction_id,
        **transaction_data.model_dump(),
        "balance_after": new_balance,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["id"]
    }
    
    await db.trust_transactions.insert_one(transaction_doc)
    
    # Update account balance
    await db.trust_accounts.update_one(
        {"id": account_id},
        {"$set": {"balance.available": new_balance}}
    )
    
    return TrustTransaction(**transaction_doc)

@api_router.get("/trust-accounts/{account_id}/transactions")
async def get_trust_transactions(account_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    transactions = await db.trust_transactions.find(
        {"trust_account_id": account_id},
        {"_id": 0}
    ).to_list(1000)
    return transactions

# ==================== EXPENSE ENDPOINTS (Enhanced) ====================
@api_router.post("/expenses", response_model=Expense)
async def create_expense(expense_data: ExpenseCreate, current_user: dict = Depends(get_current_user)):
    expense_id = str(uuid.uuid4())
    
    expense_doc = {
        "id": expense_id,
        **expense_data.model_dump(),
        "status": "pending",
        "approved_by": None,
        "approved_date": None,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.expenses.insert_one(expense_doc)
    return Expense(**expense_doc)

@api_router.get("/expenses", response_model=List[Expense])
async def get_expenses(
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    expenses = await db.expenses.find(query, {"_id": 0}).to_list(1000)
    return expenses

@api_router.put("/expenses/{expense_id}/approve")
async def approve_expense(expense_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    expense = await db.expenses.find_one({"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {
            "$set": {
                "status": "approved",
                "approved_by": current_user["id"],
                "approved_date": datetime.now(timezone.utc)
            }
        }
    )
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return updated

# ==================== ADVANCED FINANCIAL ANALYTICS ====================
@api_router.get("/analytics/dashboard")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all financial data
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    expenses = await db.expenses.find({"status": "approved"}, {"_id": 0}).to_list(10000)
    trust_accounts = await db.trust_accounts.find({}, {"_id": 0}).to_list(1000)
    time_entries = await db.time_entries.find({}, {"_id": 0}).to_list(10000)
    
    # Calculate KPIs
    total_revenue = sum(inv["paid_amount"] for inv in invoices)
    total_expenses = sum(exp["amount"] for exp in expenses)
    net_profit = total_revenue - total_expenses
    
    # Trust accounts total
    trust_total = sum(
        acc["balance"]["available"] + acc["balance"]["reserved"] + acc["balance"]["interest"]
        for acc in trust_accounts
    )
    
    # Receivables (unpaid invoices)
    receivables = sum(inv["balance"] for inv in invoices if inv["status"] != "paid")
    
    # Overdue invoices
    overdue_invoices = []
    for inv in invoices:
        if inv["status"] in ["sent", "viewed", "partial", "overdue"]:
            try:
                due_date_str = inv["due_date"]
                # Handle both date and datetime strings
                if 'T' in due_date_str:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                else:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                
                if due_date < datetime.now(timezone.utc):
                    overdue_invoices.append(inv)
            except:
                pass
    
    overdue_amount = sum(inv["balance"] for inv in overdue_invoices)
    
    # Billable hours not yet invoiced
    unbilled_entries = [e for e in time_entries if e["status"] in ["draft", "approved"] and e["billable"]]
    unbilled_amount = sum(e["amount"] for e in unbilled_entries)
    
    # Monthly revenue trend (last 6 months)
    monthly_revenue = {}
    for inv in invoices:
        if inv["paid_amount"] > 0:
            month = inv["issue_date"][:7]  # YYYY-MM
            monthly_revenue[month] = monthly_revenue.get(month, 0) + inv["paid_amount"]
    
    # Monthly expense trend
    monthly_expenses = {}
    for exp in expenses:
        month = exp["date"][:7]
        monthly_expenses[month] = monthly_expenses.get(month, 0) + exp["amount"]
    
    # Combine monthly data
    all_months = sorted(set(list(monthly_revenue.keys()) + list(monthly_expenses.keys())))[-6:]
    monthly_trend = [
        {
            "month": month,
            "revenue": monthly_revenue.get(month, 0),
            "expenses": monthly_expenses.get(month, 0),
            "profit": monthly_revenue.get(month, 0) - monthly_expenses.get(month, 0)
        }
        for month in all_months
    ]
    
    return {
        "kpis": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_revenue * 100) if total_revenue > 0 else 0,
            "trust_accounts_total": trust_total,
            "receivables": receivables,
            "overdue_amount": overdue_amount,
            "overdue_count": len(overdue_invoices),
            "unbilled_amount": unbilled_amount
        },
        "monthly_trend": monthly_trend,
        "alerts": {
            "overdue_invoices": len(overdue_invoices),
            "trust_reconciliation_pending": sum(
                1 for acc in trust_accounts
                if acc["reconciliation"]["status"] != "matched"
            )
        }
    }

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
