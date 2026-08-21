from base64 import b64encode, b64decode
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from .dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_FILE_SIZE = 6 * 1024 * 1024


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _db(request: Request):
    return request.app.state.db


def _scope(user: dict) -> dict:
    return {} if user.get("role") == "admin" else {"owner_id": user["id"]}


@router.get("")
@router.get("/")
async def list_documents(request: Request):
    user = await get_current_user(request)
    cursor = _db(request).documents.find(_scope(user)).sort("created_at", -1)
    return [_clean(doc) async for doc in cursor]


@router.post("/upload")
async def upload_document(request: Request, folder_id: str = Form(...), file: UploadFile = File(...)):
    user = await get_current_user(request)
    folder_selector = {"id": folder_id}
    if user.get("role") != "admin":
        folder_selector["owner_id"] = user["id"]
    folder = await _db(request).folders.find_one(folder_selector)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 6 MB limit")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    allowed_types = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    now = datetime.now(timezone.utc)
    document = {
        "id": str(uuid.uuid4()),
        "owner_id": user["id"] if user.get("role") != "admin" else folder.get("owner_id", user["id"]),
        "folder_id": folder_id,
        "filename": file.filename or "documento",
        "file_type": content_type,
        "size": len(content),
        "file_data": b64encode(content).decode("ascii"),
        "created_at": now,
        "updated_at": now,
    }
    await _db(request).documents.insert_one(document)
    document.pop("file_data", None)
    return _clean(document)


@router.get("/{document_id}/content")
async def get_document_content(document_id: str, request: Request):
    user = await get_current_user(request)
    document = await _db(request).documents.find_one({"id": document_id, **_scope(user)})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        content = b64decode(document["file_data"], validate=True)
    except (KeyError, ValueError):
        # Backward compatibility with documents created by the previous hex storage format.
        try:
            content = bytes.fromhex(document["file_data"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=500, detail="Stored document is corrupted")
    from fastapi.responses import Response
    return Response(content=content, media_type=document.get("file_type", "application/octet-stream"), headers={"Content-Disposition": f'inline; filename="{document.get("filename", "document")}"'})


@router.delete("/{document_id}")
async def delete_document(document_id: str, request: Request):
    user = await get_current_user(request)
    result = await _db(request).documents.delete_one({"id": document_id, **_scope(user)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}
