"""CEyE sterilization endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import SurgicalInstrument, SurgicalSet, SterilizationStatus, InstrumentStatus
from app.schemas.schemas import (
    SterilizationCycleCreate, SterilizationCycleResponse,
    SterilizationStageUpdate,
    SurgicalInstrumentCreate, SurgicalInstrumentResponse,
)
from app.services.ceye_service import (
    create_sterilization_cycle, advance_cycle_stage,
    get_cycle, list_cycles,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/ceye", tags=["ceye"])


# ---------------------------------------------------------------------------
# Surgical Instruments
# ---------------------------------------------------------------------------

@router.post("/instruments", response_model=SurgicalInstrumentResponse, status_code=201)
async def register_instrument(
    body: SurgicalInstrumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    instrument = SurgicalInstrument(**body.model_dump())
    db.add(instrument)
    await db.flush()
    await log_action(db, current_user.id, "CREATE", "instrument", str(instrument.id))
    return instrument


@router.get("/instruments", response_model=List[SurgicalInstrumentResponse])
async def list_instruments(
    status: Optional[InstrumentStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(SurgicalInstrument)
    if status:
        query = query.where(SurgicalInstrument.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/instruments/{rfid_tag}/by-rfid", response_model=SurgicalInstrumentResponse)
async def get_instrument_by_rfid(
    rfid_tag: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Lookup instrument by RFID rice-bead tag."""
    result = await db.execute(
        select(SurgicalInstrument).where(SurgicalInstrument.rfid_tag == rfid_tag)
    )
    instrument = result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrumento no encontrado")
    return instrument


# ---------------------------------------------------------------------------
# Sterilization Cycles
# ---------------------------------------------------------------------------

@router.post("/cycles", response_model=SterilizationCycleResponse, status_code=201)
async def start_cycle(
    body: SterilizationCycleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        cycle = await create_sterilization_cycle(db, body, current_user.id)
        await log_action(db, current_user.id, "CREATE", "sterilization_cycle", str(cycle.id))
        return cycle
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/cycles", response_model=List[SterilizationCycleResponse])
async def get_cycles(
    autoclave_id: Optional[str] = None,
    status: Optional[SterilizationStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_cycles(db, autoclave_id, status, skip, limit)


@router.get("/cycles/{cycle_id}", response_model=SterilizationCycleResponse)
async def get_cycle_detail(
    cycle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cycle = await get_cycle(db, cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")
    return cycle


@router.patch("/cycles/{cycle_id}/advance", response_model=SterilizationCycleResponse)
async def advance_stage(
    cycle_id: int,
    body: SterilizationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Advance the cycle through the CEyE workflow stages."""
    try:
        cycle = await advance_cycle_stage(db, cycle_id, body, current_user.id)
        await log_action(
            db, current_user.id, "UPDATE", "sterilization_cycle",
            str(cycle_id), new_values={"stage": body.stage}
        )
        return cycle
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
