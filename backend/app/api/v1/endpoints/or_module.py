"""Operating Room endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import SurgeryStatus
from app.schemas.schemas import SurgeryCreate, SurgeryResponse
from app.services.surgery_service import (
    create_surgery, get_surgery, list_surgeries,
    start_surgery, complete_surgery,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/or", tags=["operating-room"])


@router.post("/surgeries", response_model=SurgeryResponse, status_code=201)
async def create_surgery_endpoint(
    body: SurgeryCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        surgery = await create_surgery(db, body, current_user.id)
        await log_action(
            db, current_user.id, "CREATE", "surgery", str(surgery.id),
            new_values={"surgery_code": surgery.surgery_code}
        )
        return surgery
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/surgeries", response_model=List[SurgeryResponse])
async def get_surgeries(
    patient_id: Optional[str] = None,
    surgeon_id: Optional[int] = None,
    status: Optional[SurgeryStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_surgeries(db, patient_id, surgeon_id, status, skip, limit)


@router.get("/surgeries/{surgery_id}", response_model=SurgeryResponse)
async def get_surgery_detail(
    surgery_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    surgery = await get_surgery(db, surgery_id)
    if not surgery:
        raise HTTPException(status_code=404, detail="Cirugía no encontrada")
    return surgery


@router.patch("/surgeries/{surgery_id}/start", response_model=SurgeryResponse)
async def start_surgery_endpoint(
    surgery_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        surgery = await start_surgery(db, surgery_id, current_user.id)
        await log_action(db, current_user.id, "UPDATE", "surgery", str(surgery_id),
                         new_values={"status": "in_progress"})
        return surgery
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/surgeries/{surgery_id}/complete", response_model=SurgeryResponse)
async def complete_surgery_endpoint(
    surgery_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        surgery = await complete_surgery(db, surgery_id, current_user.id)
        await log_action(db, current_user.id, "UPDATE", "surgery", str(surgery_id),
                         new_values={"status": "completed"})
        return surgery
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
