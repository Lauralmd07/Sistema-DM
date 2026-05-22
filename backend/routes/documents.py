from fastapi import APIRouter

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"]
)

@router.get("/")
async def get_documents():
    return []

@router.post("/")
async def create_document():
    return {"success": True}
