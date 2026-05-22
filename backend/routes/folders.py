from fastapi import APIRouter

router = APIRouter(
    prefix="/api/folders",
    tags=["folders"]
)

@router.get("/")
async def get_folders():
    return []

@router.post("/")
async def create_folder():
    return {"success": True}
