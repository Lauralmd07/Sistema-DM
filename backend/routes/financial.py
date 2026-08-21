from datetime import datetime, timezone
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .dependencies import get_current_user, require_admin

router = APIRouter(tags=["financial"])


class FinancialCreate(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=300)
    category: str = Field(min_length=1, max_length=120)
    date: str


class FinancialUpdate(BaseModel):
    type: Optional[Literal["income", "expense"]] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None


def _db(request: Request):
    return request.app.state.db


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/financial")
async def list_financial(request: Request):
    await get_current_user(request)
    cursor = _db(request).financial.find({}).sort("date", -1)
    return [_clean(doc) async for doc in cursor]


@router.post("/financial")
async def create_financial(data: FinancialCreate, request: Request):
    user = await require_admin(request)
    now = datetime.now(timezone.utc)
    record = data.model_dump()
    record.update({
        "id": str(uuid.uuid4()),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    })
    await _db(request).financial.insert_one(record)
    return _clean(record)


@router.put("/financial/{record_id}")
async def update_financial(record_id: str, data: FinancialUpdate, request: Request):
    await require_admin(request)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No changes supplied")
    updates["updated_at"] = datetime.now(timezone.utc)
    result = await _db(request).financial.update_one({"id": record_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Financial record not found")
    return _clean(await _db(request).financial.find_one({"id": record_id}))


@router.delete("/financial/{record_id}")
async def delete_financial(record_id: str, request: Request):
    await require_admin(request)
    result = await _db(request).financial.delete_one({"id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Financial record not found")
    return {"success": True}


@router.get("/analytics/dashboard")
async def analytics_dashboard(request: Request):
    await get_current_user(request)
    records = [doc async for doc in _db(request).financial.find({})]
    total_revenue = sum(float(r.get("amount", 0)) for r in records if r.get("type") == "income")
    total_expenses = sum(float(r.get("amount", 0)) for r in records if r.get("type") == "expense")
    net_profit = total_revenue - total_expenses
    profit_margin = (net_profit / total_revenue * 100) if total_revenue else 0

    months = {}
    for record in records:
        month = str(record.get("date", ""))[:7]
        if len(month) != 7:
            continue
        bucket = months.setdefault(month, {"revenue": 0, "expenses": 0})
        amount = float(record.get("amount", 0))
        if record.get("type") == "income":
            bucket["revenue"] += amount
        else:
            bucket["expenses"] += amount

    monthly_trend = [
        {"month": month, **values, "profit": values["revenue"] - values["expenses"]}
        for month, values in sorted(months.items())
    ]
    return {
        "kpis": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "profit_margin": profit_margin,
        },
        "monthly_trend": monthly_trend,
        "alerts": {"overdue_financial": 0, "trust_reconciliation_pending": 0},
    }


@router.get("/trust-accounts")
async def list_trust_accounts(request: Request):
    await get_current_user(request)
    cursor = _db(request).trust_accounts.find({}).sort("created_at", -1)
    return [_clean(doc) async for doc in cursor]
