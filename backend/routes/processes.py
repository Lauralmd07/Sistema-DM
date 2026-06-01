from fastapi import APIRouter

router = APIRouter(
    prefix="processes",
    tags=["processes"]
)

@router.get("/")
async def get_processes():
    return []

@router.post("/")
async def create_process():
    return {"success": True}
