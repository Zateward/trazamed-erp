"""Pharmacy module endpoints."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import Product, StorageLocation, UserRole
from app.schemas.schemas import (
    ProductCreate, ProductResponse,
    InventoryItemCreate, InventoryItemResponse,
    InventoryMovementCreate, InventoryMovementResponse,
    GS1ScanRequest, UnitDoseSplitRequest,
    TemperatureLogCreate, TemperatureLogResponse,
    StorageLocationCreate, StorageLocationResponse,
)
from app.services.pharmacy_service import (
    create_inventory_item, get_inventory_item, list_inventory_items,
    process_gs1_scan, record_movement, split_unit_dose, log_temperature,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/pharmacy", tags=["pharmacy"])


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    await log_action(db, current_user.id, "CREATE", "product", str(product.id))
    return product


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


# ---------------------------------------------------------------------------
# Storage Locations
# ---------------------------------------------------------------------------

@router.post("/locations", response_model=StorageLocationResponse, status_code=201)
async def create_location(
    body: StorageLocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    location = StorageLocation(**body.model_dump())
    db.add(location)
    await db.flush()
    return location


@router.get("/locations", response_model=List[StorageLocationResponse])
async def list_locations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(StorageLocation))
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Inventory Items
# ---------------------------------------------------------------------------

@router.post("/inventory", response_model=InventoryItemResponse, status_code=201)
async def add_inventory_item(
    body: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await create_inventory_item(db, body)
    await log_action(db, current_user.id, "CREATE", "inventory_item", str(item.id))
    return item


@router.get("/inventory", response_model=List[InventoryItemResponse])
async def get_inventory(
    location_id: Optional[int] = None,
    product_id: Optional[int] = None,
    expiring_before: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = await list_inventory_items(db, location_id, product_id, expiring_before, skip, limit)
    return [
        InventoryItemResponse(
            **{
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name if i.product else None,
                "batch_number": i.batch_number,
                "serial_number": i.serial_number,
                "expiry_date": i.expiry_date,
                "quantity": i.quantity,
                "location_id": i.location_id,
                "gs1_datamatrix": i.gs1_datamatrix,
                "is_active": i.is_active,
                "created_at": i.created_at,
            }
        )
        for i in items
    ]


@router.get("/inventory/{item_id}", response_model=InventoryItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await get_inventory_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return item


# ---------------------------------------------------------------------------
# GS1 Scanner
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=InventoryItemResponse)
async def scan_gs1(
    body: GS1ScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Process a GS1 DataMatrix scan from a handheld or fixed scanner."""
    try:
        item = await process_gs1_scan(db, body, current_user.id)
        await log_action(
            db, current_user.id, "SCAN", "inventory_item",
            str(item.id), new_values={"gs1": body.raw_datamatrix}
        )
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Inventory Movements
# ---------------------------------------------------------------------------

@router.post("/movements", response_model=InventoryMovementResponse, status_code=201)
async def create_movement(
    body: InventoryMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    movement = await record_movement(
        db,
        item_id=body.item_id,
        movement_type=body.movement_type,
        quantity_delta=body.quantity_delta,
        performed_by=current_user.id,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        patient_id=body.patient_id,
        notes=body.notes,
        surgery_id=body.surgery_id,
    )
    return movement


# ---------------------------------------------------------------------------
# Unit-Dose Split
# ---------------------------------------------------------------------------

@router.post("/unit-dose/split", response_model=List[InventoryItemResponse], status_code=201)
async def split_doses(
    body: UnitDoseSplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Split a bulk medication into individual unit-dose packages."""
    try:
        items = await split_unit_dose(db, body, current_user.id)
        await log_action(
            db, current_user.id, "SPLIT", "inventory_item",
            str(body.source_item_id),
            new_values={"doses": body.doses}
        )
        return items
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Cold Chain / Temperature Monitoring
# ---------------------------------------------------------------------------

@router.post("/temperature", response_model=TemperatureLogResponse, status_code=201)
async def log_temp(
    body: TemperatureLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Receive and store IoT cold-chain temperature reading."""
    log = await log_temperature(db, body)
    return log


@router.get("/temperature/{location_id}", response_model=List[TemperatureLogResponse])
async def get_temp_history(
    location_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.models import TemperatureLog
    result = await db.execute(
        select(TemperatureLog)
        .where(TemperatureLog.location_id == location_id)
        .order_by(TemperatureLog.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
