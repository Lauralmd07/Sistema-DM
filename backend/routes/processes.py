from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/processes", tags=["processes"])


class ProcessCreate(BaseModel):
    client_number: str
    cpf: str
    action_type: str
    description: str = ""


class ProcessUpdate(BaseModel):
    client_number: Optional[str] = None
    cpf: Optional[str] = None
    action_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    timeline: Optional[list[dict[str, Any]]] = None
    judge_sentence: Optional[str] = None


def _db(request: Request):
    return request.app.state.db


async def _current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        import jwt
        payload = jwt.decode(token, request.app.state.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await _db(request).users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _scope(user: dict) -> dict:
    return {} if user.get("role") == "admin" else {"owner_id": user["id"]}


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("")
@router.get("/")
async def get_processes(request: Request):
    user = await _current_user(request)
    cursor = _db(request).processes.find(_scope(user)).sort("created_at", -1)
    return [_clean(doc) async for doc in cursor]


@router.post("")
@router.post("/")
async def create_process(data: ProcessCreate, request: Request):
    user = await _current_user(request)
    now = datetime.now(timezone.utc)
    process = {
        "id": str(uuid.uuid4()),
        "owner_id": user["id"],
        "client_number": data.client_number.strip(),
        "cpf": data.cpf.strip(),
        "action_type": data.action_type.strip(),
        "description": data.description.strip(),
        "status": "new",
        "timeline": [],
        "judge_sentence": "",
        "created_at": now,
        "updated_at": now,
    }
    await _db(request).processes.insert_one(process)
    return _clean(process)


@router.put("/{process_id}")
async def update_process(process_id: str, data: ProcessUpdate, request: Request):
    user = await _current_user(request)
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in {"new", "in_progress", "finished"}:
        raise HTTPException(status_code=422, detail="Invalid process status")
    if not updates:
        raise HTTPException(status_code=400, detail="No changes supplied")
    updates["updated_at"] = datetime.now(timezone.utc)
    selector = {"id": process_id, **_scope(user)}
    result = await _db(request).processes.update_one(selector, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Process not found")
    return _clean(await _db(request).processes.find_one(selector))


@router.delete("/{process_id}")
async def delete_process(process_id: str, request: Request):
    user = await _current_user(request)
    result = await _db(request).processes.delete_one({"id": process_id, **_scope(user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"success": True}
