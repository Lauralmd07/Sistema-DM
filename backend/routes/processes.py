from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

import server

router = APIRouter(prefix="/api/processes", tags=["processes"])
db = server.db
get_current_user = server.get_current_user
json_body = server.json_body
clean = server.clean
VALID_STATUSES = {"new", "in_progress", "finished"}


def normalize_process(data: dict, owner_id: str, process_id: str | None = None, existing: dict | None = None) -> dict:
    existing = existing or {}
    client_number = str(data.get("client_number", existing.get("client_number", "")) or "").strip()
    cpf = str(data.get("cpf", existing.get("cpf", "")) or "").strip()
    action_type = str(data.get("action_type", existing.get("action_type", "")) or "").strip()
    description = str(data.get("description", existing.get("description", "")) or "").strip()
    status = str(data.get("status", existing.get("status", "new")) or "new").strip().lower()
    timeline = data.get("timeline", existing.get("timeline", [])) or []
    judge_sentence = str(data.get("judge_sentence", existing.get("judge_sentence", "")) or "")

    if not client_number:
        raise HTTPException(status_code=422, detail="Número do cliente é obrigatório")
    if not cpf:
        raise HTTPException(status_code=422, detail="CPF é obrigatório")
    if not action_type:
        raise HTTPException(status_code=422, detail="Tipo de ação é obrigatório")
    if not description:
        raise HTTPException(status_code=422, detail="Descrição é obrigatória")
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Status de processo inválido")
    if not isinstance(timeline, list):
        raise HTTPException(status_code=422, detail="Linha do tempo inválida")

    return {
        "id": process_id or str(uuid.uuid4()),
        "owner_id": owner_id,
        "client_number": client_number,
        "cpf": cpf,
        "action_type": action_type,
        "description": description,
        "status": status,
        "timeline": timeline,
        "judge_sentence": judge_sentence,
        "created_at": existing.get("created_at", datetime.now(timezone.utc)),
        "updated_at": datetime.now(timezone.utc),
    }


@router.get("")
@router.get("/")
async def list_processes(current_user: dict = Depends(get_current_user)):
    cursor = db.processes.find({"owner_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=5000)


@router.post("")
@router.post("/")
async def create_process(request: Request, current_user: dict = Depends(get_current_user)):
    doc = normalize_process(await json_body(request), current_user["id"])
    await db.processes.insert_one(doc)
    return clean(dict(doc))


@router.put("/{process_id}")
async def update_process(process_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    existing = await db.processes.find_one({"id": process_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    doc = normalize_process(await json_body(request), current_user["id"], process_id, existing)
    await db.processes.replace_one({"id": process_id, "owner_id": current_user["id"]}, doc)
    return clean(dict(doc))


@router.delete("/{process_id}")
async def delete_process(process_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.processes.delete_one({"id": process_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return {"success": True}
