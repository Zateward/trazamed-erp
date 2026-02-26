"""Pharmacy inventory service."""
import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.models import (
    InventoryItem, InventoryMovement, Product, StorageLocation,
    MovementType, TemperatureLog, AlertSeverity,
)
from app.schemas.schemas import (
    InventoryItemCreate, InventoryMovementCreate,
    GS1ScanRequest, TemperatureLogCreate, UnitDoseSplitRequest,
)
from app.services.gs1_parser import parse_gs1_datamatrix
from app.core.fea import compute_record_signature


async def create_inventory_item(db: AsyncSession, data: InventoryItemCreate) -> InventoryItem:
    item = InventoryItem(**data.model_dump())
    db.add(item)
    await db.flush()
    return item


async def get_inventory_item(db: AsyncSession, item_id: int) -> Optional[InventoryItem]:
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.product))
        .where(InventoryItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def list_inventory_items(
    db: AsyncSession,
    location_id: Optional[int] = None,
    product_id: Optional[int] = None,
    expiring_before: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[InventoryItem]:
    query = select(InventoryItem).options(selectinload(InventoryItem.product))
    filters = [InventoryItem.is_active.is_(True)]
    if location_id:
        filters.append(InventoryItem.location_id == location_id)
    if product_id:
        filters.append(InventoryItem.product_id == product_id)
    if expiring_before:
        filters.append(InventoryItem.expiry_date <= expiring_before)
    query = query.where(and_(*filters)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def process_gs1_scan(
    db: AsyncSession,
    scan: GS1ScanRequest,
    performed_by: int,
) -> InventoryItem:
    """Parse a GS1 DataMatrix scan and register the inventory movement."""
    parsed = parse_gs1_datamatrix(scan.raw_datamatrix)

    # Look up product by GTIN
    product = None
    if parsed.gtin:
        result = await db.execute(select(Product).where(Product.gtin == parsed.gtin))
        product = result.scalar_one_or_none()

    if not product:
        raise ValueError(f"Producto no encontrado para GTIN: {parsed.gtin}")

    # Parse expiry date
    expiry_dt = datetime.now(timezone.utc)
    if parsed.expiry and len(parsed.expiry) == 6:
        yy, mm, dd = parsed.expiry[:2], parsed.expiry[2:4], parsed.expiry[4:6]
        year = 2000 + int(yy)
        expiry_dt = datetime(year, int(mm), int(dd), tzinfo=timezone.utc)

    # Check if item already exists (same GTIN + batch + serial)
    existing_query = select(InventoryItem).where(
        and_(
            InventoryItem.product_id == product.id,
            InventoryItem.batch_number == (parsed.batch or "UNKNOWN"),
            InventoryItem.serial_number == parsed.serial,
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing and scan.movement_type == MovementType.ENTRY:
        existing.quantity += Decimal("1")
        await db.flush()
        item = existing
    else:
        item = InventoryItem(
            product_id=product.id,
            batch_number=parsed.batch or "UNKNOWN",
            serial_number=parsed.serial,
            expiry_date=expiry_dt,
            quantity=Decimal("1"),
            location_id=scan.location_id,
            gs1_datamatrix=scan.raw_datamatrix,
        )
        db.add(item)
        await db.flush()

    # Record movement
    await record_movement(
        db,
        item_id=item.id,
        movement_type=scan.movement_type,
        quantity_delta=Decimal("1"),
        to_location_id=scan.location_id,
        performed_by=performed_by,
    )
    return item


async def record_movement(
    db: AsyncSession,
    item_id: int,
    movement_type: MovementType,
    quantity_delta: Decimal,
    performed_by: int,
    from_location_id: Optional[int] = None,
    to_location_id: Optional[int] = None,
    patient_id: Optional[str] = None,
    notes: Optional[str] = None,
    surgery_id: Optional[int] = None,
) -> InventoryMovement:
    payload = f"{item_id}|{movement_type}|{quantity_delta}|{performed_by}"
    signature = compute_record_signature(payload)

    movement = InventoryMovement(
        item_id=item_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        patient_id=patient_id,
        performed_by=performed_by,
        notes=notes,
        signature=signature,
        surgery_id=surgery_id,
    )
    db.add(movement)
    await db.flush()

    # Update item quantity
    item = await get_inventory_item(db, item_id)
    if item:
        if movement_type in (MovementType.ENTRY, MovementType.TRANSFER):
            item.quantity += abs(quantity_delta)
        elif movement_type in (MovementType.EXIT, MovementType.DISPENSATION):
            item.quantity -= abs(quantity_delta)
        await db.flush()

    return movement


async def split_unit_dose(
    db: AsyncSession,
    request: UnitDoseSplitRequest,
    performed_by: int,
) -> List[InventoryItem]:
    """Split a bulk inventory item into individual unit-dose packages."""
    source = await get_inventory_item(db, request.source_item_id)
    if not source:
        raise ValueError("Artículo fuente no encontrado")
    if source.quantity < request.doses:
        raise ValueError(
            f"Stock insuficiente: disponible {source.quantity}, solicitado {request.doses}"
        )

    dose_qty = source.quantity / request.doses
    children = []
    for i in range(request.doses):
        child = InventoryItem(
            product_id=source.product_id,
            batch_number=source.batch_number,
            serial_number=f"{source.serial_number or source.id}-UD{i+1:04d}",
            expiry_date=source.expiry_date,
            quantity=dose_qty,
            location_id=request.target_location_id or source.location_id,
            parent_item_id=source.id,
        )
        db.add(child)
        children.append(child)

    # Deduct from source
    source.quantity = Decimal('0')  # fully consumed by split
    await db.flush()

    await record_movement(
        db,
        item_id=source.id,
        movement_type=MovementType.SPLIT,
        quantity_delta=-source.quantity,
        performed_by=performed_by,
        notes=f"Split into {request.doses} unit-doses",
    )
    return children


async def log_temperature(
    db: AsyncSession,
    data: TemperatureLogCreate,
) -> TemperatureLog:
    """Log IoT temperature reading and evaluate cold-chain compliance."""
    # Determine alert status based on product requirements in this location
    is_alert = False
    severity = None

    items_result = await db.execute(
        select(InventoryItem).where(
            and_(
                InventoryItem.location_id == data.location_id,
                InventoryItem.is_active.is_(True),
            )
        ).limit(1)
    )
    sample_item = items_result.scalar_one_or_none()

    if sample_item:
        product_result = await db.execute(
            select(Product).where(Product.id == sample_item.product_id)
        )
        product = product_result.scalar_one_or_none()
        if product and product.requires_cold_chain:
            min_t = product.cold_chain_min_temp or 2.0
            max_t = product.cold_chain_max_temp or 8.0
            if data.temperature_c < min_t - 2 or data.temperature_c > max_t + 5:
                is_alert = True
                severity = AlertSeverity.CRITICAL
            elif data.temperature_c < min_t or data.temperature_c > max_t:
                is_alert = True
                severity = AlertSeverity.HIGH

    log = TemperatureLog(
        location_id=data.location_id,
        sensor_id=data.sensor_id,
        temperature_c=data.temperature_c,
        humidity_pct=data.humidity_pct,
        is_alert=is_alert,
        alert_severity=severity,
        mqtt_topic=data.mqtt_topic,
    )
    db.add(log)
    await db.flush()
    return log
