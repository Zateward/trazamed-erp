"""CEyE sterilization service."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import (
    SterilizationCycle, InstrumentCycleLog, SurgicalInstrument,
    SterilizationStatus, InstrumentStatus,
)
from app.schemas.schemas import (
    SterilizationCycleCreate, SterilizationStageUpdate,
)
from app.core.fea import compute_record_signature


STAGE_PROGRESSION = [
    "washing",
    "inspection",
    "packaging",
    "sterilization",
    "delivery",
]


async def create_sterilization_cycle(
    db: AsyncSession,
    data: SterilizationCycleCreate,
    operator_id: int,
) -> SterilizationCycle:
    cycle = SterilizationCycle(
        autoclave_id=data.autoclave_id,
        cycle_number=data.cycle_number,
        temperature_c=data.temperature_c,
        pressure_kpa=data.pressure_kpa,
        duration_minutes=data.duration_minutes,
        operator_id=operator_id,
        notes=data.notes,
        status=SterilizationStatus.PENDING,
        washing_started_at=datetime.now(timezone.utc),
    )
    db.add(cycle)
    await db.flush()

    for inst_id in data.instrument_ids:
        log = InstrumentCycleLog(cycle_id=cycle.id, instrument_id=inst_id)
        db.add(log)
        # Update instrument status
        result = await db.execute(
            select(SurgicalInstrument).where(SurgicalInstrument.id == inst_id)
        )
        instrument = result.scalar_one_or_none()
        if instrument:
            instrument.status = InstrumentStatus.STERILIZING

    await db.flush()
    return cycle


async def advance_cycle_stage(
    db: AsyncSession,
    cycle_id: int,
    stage_data: SterilizationStageUpdate,
    operator_id: int,
) -> SterilizationCycle:
    result = await db.execute(
        select(SterilizationCycle).where(SterilizationCycle.id == cycle_id)
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise ValueError("Ciclo de esterilización no encontrado")

    now = datetime.now(timezone.utc)
    stage = stage_data.stage.lower()

    if stage == "washing":
        cycle.washing_completed_at = now
    elif stage == "inspection":
        cycle.inspection_completed_at = now
    elif stage == "packaging":
        cycle.packaging_completed_at = now
    elif stage == "sterilization":
        cycle.sterilization_started_at = cycle.sterilization_started_at or now
        cycle.sterilization_completed_at = now
        cycle.status = SterilizationStatus.IN_PROGRESS
        if stage_data.biological_indicator_result:
            cycle.biological_indicator_result = stage_data.biological_indicator_result
        if stage_data.chemical_indicator_result:
            cycle.chemical_indicator_result = stage_data.chemical_indicator_result
        if stage_data.bowie_dick_result:
            cycle.bowie_dick_result = stage_data.bowie_dick_result
        # Check for failure
        if (
            stage_data.biological_indicator_result == "fail"
            or stage_data.chemical_indicator_result == "fail"
        ):
            cycle.status = SterilizationStatus.FAILED
    elif stage == "delivery":
        cycle.delivered_at = now
        if cycle.status != SterilizationStatus.FAILED:
            cycle.status = SterilizationStatus.COMPLETED
        # Update instrument counts and status
        instr_logs_result = await db.execute(
            select(InstrumentCycleLog).where(InstrumentCycleLog.cycle_id == cycle_id)
        )
        for log in instr_logs_result.scalars().all():
            inst_result = await db.execute(
                select(SurgicalInstrument).where(SurgicalInstrument.id == log.instrument_id)
            )
            instrument = inst_result.scalar_one_or_none()
            if instrument:
                instrument.total_sterilization_cycles += 1
                if cycle.status == SterilizationStatus.COMPLETED:
                    instrument.status = InstrumentStatus.AVAILABLE
                else:
                    instrument.status = InstrumentStatus.MAINTENANCE
    else:
        raise ValueError(f"Etapa inválida: {stage}")

    # Sign the cycle update
    payload = f"{cycle_id}|{stage}|{operator_id}|{now.isoformat()}"
    cycle.signature = compute_record_signature(payload, now)

    await db.flush()
    return cycle


async def get_cycle(db: AsyncSession, cycle_id: int) -> Optional[SterilizationCycle]:
    result = await db.execute(
        select(SterilizationCycle)
        .options(selectinload(SterilizationCycle.instrument_cycles))
        .where(SterilizationCycle.id == cycle_id)
    )
    return result.scalar_one_or_none()


async def list_cycles(
    db: AsyncSession,
    autoclave_id: Optional[str] = None,
    status: Optional[SterilizationStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[SterilizationCycle]:
    query = select(SterilizationCycle)
    if autoclave_id:
        query = query.where(SterilizationCycle.autoclave_id == autoclave_id)
    if status:
        query = query.where(SterilizationCycle.status == status)
    query = query.order_by(SterilizationCycle.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
