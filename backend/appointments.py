from datetime import datetime, timezone
import uuid
import re

from fastapi import Depends, HTTPException, Request

import server

app = server.app
db = server.db
get_current_user = server.get_current_user
json_body = server.json_body
clean = server.clean

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
VALID_TYPES = {"lead", "return", "hearing"}


def remove_existing_appointment_routes():
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (
            getattr(route, "path", "") == "/api/appointments"
            or getattr(route, "path", "").startswith("/api/appointments/")
        )
    ]


remove_existing_appointment_routes()


def normalize_appointment(data: dict, user_id: str, appointment_id: str | None = None) -> dict:
    appointment_type = str(data.get("type") or "lead").strip().lower()
    client_name = str(data.get("client_name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    subject = str(data.get("subject") or "Compromisso").strip() or "Compromisso"
    date = str(data.get("date") or "").strip()
    time = str(data.get("time") or "").strip()
    color = str(data.get("color") or "#D4AF37").strip()
    cpf = str(data.get("cpf") or "").strip()
    rg = str(data.get("rg") or "").strip()
    address = str(data.get("address") or "").strip()
    process_number = str(data.get("process_number") or "").strip()
    court = str(data.get("court") or "").strip()

    if appointment_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail="Tipo de compromisso inválido")
    if not client_name:
        raise HTTPException(status_code=422, detail="Nome do cliente é obrigatório")
    if not date or not DATE_RE.fullmatch(date):
        raise HTTPException(status_code=422, detail="Data inválida. Use AAAA-MM-DD")
    if not time or not TIME_RE.fullmatch(time):
        raise HTTPException(status_code=422, detail="Hora inválida. Use HH:MM")
    if appointment_type != "hearing" and not phone:
        raise HTTPException(status_code=422, detail="Telefone é obrigatório")
    if appointment_type == "hearing" and not process_number:
        raise HTTPException(status_code=422, detail="Número do processo é obrigatório para audiência")
    if appointment_type == "hearing" and not court:
        raise HTTPException(status_code=422, detail="Órgão julgador é obrigatório para audiência")

    doc = {
        "id": appointment_id or str(uuid.uuid4()),
        "owner_id": user_id,
        "type": appointment_type,
        "client_name": client_name,
        "phone": phone,
        "subject": subject,
        "date": date,
        "time": time,
        "color": color,
        "cpf": cpf,
        "rg": rg,
        "address": address,
        "process_number": process_number,
        "court": court,
    }
    return doc


@app.get("/api/appointments")
async def list_appointments(current_user: dict = Depends(get_current_user)):
    cursor = db.appointments.find(
        {"owner_id": current_user["id"]},
        {"_id": 0},
    ).sort([("date", 1), ("time", 1)])
    return await cursor.to_list(length=5000)


@app.post("/api/appointments")
async def create_appointment(request: Request, current_user: dict = Depends(get_current_user)):
    data = await json_body(request)
    doc = normalize_appointment(data, current_user["id"])
    doc["created_at"] = datetime.now(timezone.utc)
    await db.appointments.insert_one(doc)
    return clean(dict(doc))


@app.put("/api/appointments/{appointment_id}")
async def update_appointment(appointment_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    existing = await db.appointments.find_one({"id": appointment_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    data = await json_body(request)
    doc = normalize_appointment(data, current_user["id"], appointment_id)
    doc["created_at"] = existing.get("created_at", datetime.now(timezone.utc))
    doc["updated_at"] = datetime.now(timezone.utc)
    await db.appointments.replace_one(
        {"id": appointment_id, "owner_id": current_user["id"]},
        doc,
    )
    return clean(dict(doc))


@app.delete("/api/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.appointments.delete_one({"id": appointment_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    return {"success": True}
