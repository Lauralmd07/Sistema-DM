import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

import server
import appointments  # Registers the agenda API on the shared FastAPI app.

app = server.app
db = server.db
clean = server.clean
get_current_user = server.get_current_user
logger = logging.getLogger(__name__)

files_bucket = AsyncIOMotorGridFSBucket(db, bucket_name="legal_files")
MAX_FILE_SIZE = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def remove_routes(paths_and_methods):
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (
            getattr(route, "path", None) in paths_and_methods
            and getattr(route, "methods", set()).intersection(paths_and_methods[getattr(route, "path", None)])
        )
    ]


remove_routes({
    "/api/clients/{client_id}": {"DELETE"},
    "/api/clients/{client_id}/documents": {"GET", "POST"},
    "/api/clients/{client_id}/documents/{document_id}": {"GET", "DELETE"},
    "/api/folders/{folder_id}": {"DELETE"},
    "/api/documents": {"GET"},
    "/api/documents/upload": {"POST"},
    "/api/documents/{document_id}": {"GET", "DELETE"},
})


async def save_upload(file: UploadFile, metadata: dict):
    grid_in = await files_bucket.open_upload_stream(file.filename or "arquivo", metadata=metadata)
    total = 0
    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="Arquivo maior que 100 MB")
            await grid_in.write(chunk)
        await grid_in.close()
        return str(grid_in._id), total
    except Exception:
        try:
            await grid_in.abort()
        except Exception:
            pass
        raise


async def read_file(gridfs_id: str) -> bytes:
    try:
        grid_out = await files_bucket.open_download_stream(ObjectId(gridfs_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo armazenado não encontrado")
    chunks = []
    while True:
        chunk = await grid_out.read(CHUNK_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def delete_file(gridfs_id: Optional[str]):
    if not gridfs_id:
        return
    try:
        await files_bucket.delete(ObjectId(gridfs_id))
    except Exception:
        logger.warning("Falha ao excluir arquivo GridFS %s", gridfs_id, exc_info=True)


async def migrate_legacy(collection, doc):
    if doc.get("gridfs_id") or not doc.get("file_data"):
        return doc
    try:
        content = base64.b64decode(doc["file_data"])
        grid_in = await files_bucket.open_upload_stream(
            doc.get("filename") or "arquivo",
            metadata={"document_id": doc["id"], "owner_id": doc.get("owner_id"), "legacy_migration": True},
        )
        for start in range(0, len(content), CHUNK_SIZE):
            await grid_in.write(content[start:start + CHUNK_SIZE])
        await grid_in.close()
        await collection.update_one(
            {"id": doc["id"]},
            {"$set": {"gridfs_id": str(grid_in._id)}, "$unset": {"file_data": ""}},
        )
        doc["gridfs_id"] = str(grid_in._id)
        doc.pop("file_data", None)
    except Exception:
        logger.exception("Falha ao migrar arquivo legado %s", doc.get("id"))
    return doc


@app.delete("/api/clients/{client_id}")
async def delete_client_gridfs(client_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    docs = await db.client_documents.find({"client_id": client_id, "owner_id": current_user["id"]}, {"gridfs_id": 1, "_id": 0}).to_list(length=5000)
    for doc in docs:
        await delete_file(doc.get("gridfs_id"))
    await db.client_documents.delete_many({"client_id": client_id, "owner_id": current_user["id"]})
    return {"success": True}


@app.get("/api/clients/{client_id}/documents")
async def list_client_documents_gridfs(client_id: str, current_user: dict = Depends(get_current_user)):
    if not await db.clients.find_one({"id": client_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cursor = db.client_documents.find(
        {"client_id": client_id, "owner_id": current_user["id"]},
        {"_id": 0, "file_data": 0},
    ).sort("created_at", -1)
    return await cursor.to_list(length=500)


@app.post("/api/clients/{client_id}/documents")
async def upload_client_document_gridfs(client_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not await db.clients.find_one({"id": client_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    document_id = server.uuid.uuid4().__str__()
    gridfs_id, file_size = await save_upload(
        file,
        {"document_id": document_id, "owner_id": current_user["id"], "client_id": client_id, "kind": "client_document"},
    )
    doc = {
        "id": document_id,
        "client_id": client_id,
        "owner_id": current_user["id"],
        "filename": file.filename or "arquivo",
        "file_type": file.content_type or "application/octet-stream",
        "file_size": file_size,
        "gridfs_id": gridfs_id,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db.client_documents.insert_one(doc)
    except Exception:
        await delete_file(gridfs_id)
        raise
    return clean(dict(doc))


@app.get("/api/clients/{client_id}/documents/{document_id}")
async def get_client_document_gridfs(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.client_documents.find_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not doc.get("gridfs_id") and doc.get("file_data"):
        doc = await migrate_legacy(db.client_documents, doc)
    if doc.get("gridfs_id"):
        doc["file_data"] = base64.b64encode(await read_file(doc["gridfs_id"])).decode("ascii")
    elif not doc.get("file_data"):
        raise HTTPException(status_code=404, detail="Conteúdo do documento não encontrado")
    return doc


@app.delete("/api/clients/{client_id}/documents/{document_id}")
async def delete_client_document_gridfs(client_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.client_documents.find_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]}, {"gridfs_id": 1, "_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    await delete_file(doc.get("gridfs_id"))
    result = await db.client_documents.delete_one({"id": document_id, "client_id": client_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"success": True}


@app.delete("/api/folders/{folder_id}")
async def delete_folder_gridfs(folder_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.folders.delete_one({"id": folder_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    docs = await db.documents.find({"folder_id": folder_id, "owner_id": current_user["id"]}, {"gridfs_id": 1, "_id": 0}).to_list(length=5000)
    for doc in docs:
        await delete_file(doc.get("gridfs_id"))
    await db.documents.delete_many({"folder_id": folder_id, "owner_id": current_user["id"]})
    return {"success": True}


@app.get("/api/documents")
async def list_documents_gridfs(current_user: dict = Depends(get_current_user)):
    cursor = db.documents.find({"owner_id": current_user["id"]}, {"_id": 0, "file_data": 0}).sort("created_at", -1)
    return await cursor.to_list(length=1000)


@app.post("/api/documents/upload")
async def upload_document_gridfs(folder_id: str = Form(...), file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not await db.folders.find_one({"id": folder_id, "owner_id": current_user["id"]}):
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    document_id = server.uuid.uuid4().__str__()
    gridfs_id, file_size = await save_upload(
        file,
        {"document_id": document_id, "owner_id": current_user["id"], "folder_id": folder_id, "kind": "drive_document"},
    )
    doc = {
        "id": document_id,
        "folder_id": folder_id,
        "owner_id": current_user["id"],
        "filename": file.filename or "arquivo",
        "file_type": file.content_type or "application/octet-stream",
        "file_size": file_size,
        "gridfs_id": gridfs_id,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db.documents.insert_one(doc)
    except Exception:
        await delete_file(gridfs_id)
        raise
    return clean(dict(doc))


@app.get("/api/documents/{document_id}")
async def get_document_gridfs(document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": document_id, "owner_id": current_user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not doc.get("gridfs_id") and doc.get("file_data"):
        doc = await migrate_legacy(db.documents, doc)
    if doc.get("gridfs_id"):
        doc["file_data"] = base64.b64encode(await read_file(doc["gridfs_id"])).decode("ascii")
    elif not doc.get("file_data"):
        raise HTTPException(status_code=404, detail="Conteúdo do documento não encontrado")
    return doc


@app.delete("/api/documents/{document_id}")
async def delete_document_gridfs(document_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": document_id, "owner_id": current_user["id"]}, {"gridfs_id": 1, "_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    await delete_file(doc.get("gridfs_id"))
    result = await db.documents.delete_one({"id": document_id, "owner_id": current_user["id"]})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return {"success": True}
