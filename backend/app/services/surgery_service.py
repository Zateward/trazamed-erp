"""Operating Room surgery service."""
import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import Surgery, SurgerySet, SurgeryStatus
from app.schemas.schemas import SurgeryCreate
from app.core.fea import compute_record_signature


async def create_surgery(
    db: AsyncSession,
    data: SurgeryCreate,
    created_by: int,
) -> Surgery:
    patient_hash = hashlib.sha256(data.patient_id.encode()).hexdigest()
    surgery = Surgery(
        surgery_code=data.surgery_code,
        patient_id=data.patient_id,
        patient_name_hash=patient_hash,
        surgeon_id=data.surgeon_id,
        procedure_name=data.procedure_name,
        operating_room=data.operating_room,
        scheduled_at=data.scheduled_at,
        diagnosis_code=data.diagnosis_code,
        notes=data.notes,
        status=SurgeryStatus.SCHEDULED,
    )
    db.add(surgery)
    await db.flush()

    for set_id in data.surgical_set_ids:
        ss = SurgerySet(surgery_id=surgery.id, surgical_set_id=set_id)
        db.add(ss)

    await db.flush()
    return surgery


async def start_surgery(db: AsyncSession, surgery_id: int, operator_id: int) -> Surgery:
    result = await db.execute(select(Surgery).where(Surgery.id == surgery_id))
    surgery = result.scalar_one_or_none()
    if not surgery:
        raise ValueError("Cirugía no encontrada")
    surgery.started_at = datetime.now(timezone.utc)
    surgery.status = SurgeryStatus.IN_PROGRESS
    await db.flush()
    return surgery


async def complete_surgery(db: AsyncSession, surgery_id: int, operator_id: int) -> Surgery:
    result = await db.execute(select(Surgery).where(Surgery.id == surgery_id))
    surgery = result.scalar_one_or_none()
    if not surgery:
        raise ValueError("Cirugía no encontrada")

    now = datetime.now(timezone.utc)
    surgery.completed_at = now
    surgery.status = SurgeryStatus.COMPLETED

    payload = f"{surgery_id}|{SurgeryStatus.COMPLETED}|{operator_id}|{now.isoformat()}"
    surgery.signature = compute_record_signature(payload, now)

    await db.flush()
    return surgery


async def get_surgery(db: AsyncSession, surgery_id: int) -> Optional[Surgery]:
    result = await db.execute(
        select(Surgery)
        .options(selectinload(Surgery.surgery_sets))
        .where(Surgery.id == surgery_id)
    )
    return result.scalar_one_or_none()


async def list_surgeries(
    db: AsyncSession,
    patient_id: Optional[str] = None,
    surgeon_id: Optional[int] = None,
    status: Optional[SurgeryStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Surgery]:
    query = select(Surgery)
    if patient_id:
        query = query.where(Surgery.patient_id == patient_id)
    if surgeon_id:
        query = query.where(Surgery.surgeon_id == surgeon_id)
    if status:
        query = query.where(Surgery.status == status)
    query = query.order_by(Surgery.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
