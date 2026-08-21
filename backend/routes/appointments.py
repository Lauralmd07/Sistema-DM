from datetime import datetime, timezone
import uuid
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .dependencies import get_current_user

router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentBase(BaseModel):
    type: Literal["lead", "return", "hearing"] = "lead"
    client_name: str = Field(min_length=1, max_length=120)
    phone: str = ""
    subject: str = Field(min_length=1, max_length=200)
    date: str
    time: str
    color: str = "#D4AF37"
    cpf: str = ""
    rg: str = ""
    address: str = ""
    process_number: str = ""
    court: str = ""


class AppointmentUpdate(BaseModel):
    type: Optional[Literal["lead", "return", "hearing"]] = None
    client_name: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    color: Optional[str] = None
    cpf: Optional[str] = None
    rg: Optional[str] = None
    address: Optional[str] = None
    process_number: Optional[str] = None
    court: Optional[str] = None


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _db(request: Request):
    return request.app.state.db


def _scope(user: dict) -> dict:
    return {} if user.get("role") == "admin" else {"owner_id": user["id"]}


@router.get("")
@router.get("/")
async def list_appointments(request: Request):
    user = await get_current_user(request)
    cursor = _db(request).appointments.find(_scope(user)).sort([("date", 1), ("time", 1)])
    return [_clean(doc) async for doc in cursor]


@router.post("")
@router.post("/")
async def create_appointment(data: AppointmentBase, request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc)
    appointment = data.model_dump()
    appointment.update({"id": str(uuid.uuid4()), "owner_id": user["id"], "created_at": now, "updated_at": now})
    await _db(request).appointments.insert_one(appointment)
    return _clean(appointment)


@router.put("/{appointment_id}")
async def update_appointment(appointment_id: str, data: AppointmentUpdate, request: Request):
    user = await get_current_user(request)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No changes supplied")
    updates["updated_at"] = datetime.now(timezone.utc)
    selector = {"id": appointment_id, **_scope(user)}
    result = await _db(request).appointments.update_one(selector, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _clean(await _db(request).appointments.find_one(selector))


@router.delete("/{appointment_id}")
async def delete_appointment(appointment_id: str, request: Request):
    user = await get_current_user(request)
    result = await _db(request).appointments.delete_one({"id": appointment_id, **_scope(user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"success": True}
