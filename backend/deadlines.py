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


def normalize_deadline(data: dict, user_id: str, deadline_id: str | None = None) -> dict:
    title = str(data.get("title") or "").strip()
    date = str(data.get("date") or "").strip()
    time = str(data.get("time") or "23:59").strip()
    deadline_type = str(data.get("type") or "prazo").strip().lower()
    priority = str(data.get("priority") or "normal").strip().lower()
    client_name = str(data.get("client_name") or "").strip()
    process_number = str(data.get("process_number") or "").strip()
    notes = str(data.get("notes") or "").strip()
    status = str(data.get("status") or "pending").strip().lower()

    if not title:
        raise HTTPException(status_code=422, detail="Descrição do prazo é obrigatória")
    if not DATE_RE.fullmatch(date):
        raise HTTPException(status_code=422, detail="Data inválida. Use AAAA-MM-DD")
    if not TIME_RE.fullmatch(time):
        raise HTTPException(status_code=422, detail="Hora inválida. Use HH:MM")
    if deadline_type not in {"prazo", "peticao", "contestacao", "recurso", "outro"}:
        raise HTTPException(status_code=422, detail="Tipo de prazo inválido")
    if priority not in {"baixa", "normal", "alta", "urgente"}:
        raise HTTPException(status_code=422, detail="Prioridade inválida")
    if status not in {"pending", "completed", "cancelled"}:
        raise HTTPException(status_code=422, detail="Status inválido")

    return {
        "id": deadline_id or str(uuid.uuid4()),
        "owner_id": user_id,
        "title": title,
        "date": date,
        "time": time,
        "type": deadline_type,
        "priority": priority,
        "client_name": client_name,
        "process_number": process_number,
        "notes": notes,
        "status": status,
    }


def remove_existing_deadline_routes():
    app.router.routes[:] = [
        route for route in app.router.routes
        if getattr(route, "path", "") == "/api/deadlines" or getattr(route, "path", "").startswith("/api/deadlines/")
    ]


# The project imports this module after server.py; no duplicate routes are expected.


@app.get("/api/deadlines")
async def list_deadlines(current_user: dict = Depends(get_current_user)):
    cursor = db.deadlines.find({"owner_id": current_user["id"]}, {"_id": 0}).sort([("date", 1), ("time", 1)])
    return await cursor.to_list(length=5000)


@app.post("/api/deadlines")
async def create_deadline(request: Request, current_user: dict = Depends(get_current_user)):
    doc = normalize_deadline(await json_body(request), current_user["id"])
    doc["created_at"] = datetime.now(timezone.utc)
    await db.deadlines.insert_one(doc)
    return clean(dict(doc))


@app.put("/api/deadlines/{deadline_id}")
async def update_deadline(deadline_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    existing = await db.deadlines.find_one({"id": deadline_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    doc = normalize_deadline(await json_body(request), current_user["id"], deadline_id)
    doc["created_at"] = existing.get("created_at", datetime.now(timezone.utc))
    doc["updated_at"] = datetime.now(timezone.utc)
    await db.deadlines.replace_one({"id": deadline_id, "owner_id": current_user["id"]}, doc)
    return clean(dict(doc))


@app.delete("/api/deadlines/{deadline_id}")
async def delete_deadline(deadline_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.deadlines.delete_one({"id": deadline_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Prazo não encontrado")
    return {"success": True}
