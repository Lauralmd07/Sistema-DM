from datetime import datetime, timezone
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .dependencies import get_current_user

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: Literal["client", "process"] = "client"
    reference_id: str = Field(min_length=1, max_length=200)


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[Literal["client", "process"]] = None
    reference_id: Optional[str] = None


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _db(request: Request):
    return request.app.state.db


def _scope(user: dict) -> dict:
    return {} if user.get("role") == "admin" else {"owner_id": user["id"]}


@router.get("")
@router.get("/")
async def list_folders(request: Request):
    user = await get_current_user(request)
    cursor = _db(request).folders.find(_scope(user)).sort("created_at", -1)
    return [_clean(doc) async for doc in cursor]


@router.post("")
@router.post("/")
async def create_folder(data: FolderCreate, request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc)
    folder = {
        "id": str(uuid.uuid4()),
        "owner_id": user["id"],
        "name": data.name.strip(),
        "type": data.type,
        "reference_id": data.reference_id.strip(),
        "created_at": now,
        "updated_at": now,
    }
    await _db(request).folders.insert_one(folder)
    return _clean(folder)


@router.put("/{folder_id}")
async def update_folder(folder_id: str, data: FolderUpdate, request: Request):
    user = await get_current_user(request)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No changes supplied")
    updates["updated_at"] = datetime.now(timezone.utc)
    selector = {"id": folder_id, **_scope(user)}
    result = await _db(request).folders.update_one(selector, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Folder not found")
    return _clean(await _db(request).folders.find_one(selector))


@router.delete("/{folder_id}")
async def delete_folder(folder_id: str, request: Request):
    user = await get_current_user(request)
    selector = {"id": folder_id, **_scope(user)}
    folder = await _db(request).folders.find_one(selector)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    document_scope = {"folder_id": folder_id}
    if user.get("role") != "admin":
        document_scope["owner_id"] = user["id"]
    await _db(request).documents.delete_many(document_scope)
    await _db(request).folders.delete_one(selector)
    return {"success": True}
