"""Pydantic schemas for request/response validation."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.models import (
    UserRole, MovementType, SterilizationStatus,
    InstrumentStatus, SurgeryStatus, AlertSeverity,
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER
    professional_id: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    professional_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    gtin: str = Field(..., min_length=8, max_length=14)
    name: str = Field(..., min_length=1, max_length=255)
    generic_name: Optional[str] = None
    manufacturer: Optional[str] = None
    concentration: Optional[str] = None
    pharmaceutical_form: Optional[str] = None
    unit_of_measure: str = "piece"
    requires_cold_chain: bool = False
    cold_chain_min_temp: Optional[float] = None
    cold_chain_max_temp: Optional[float] = None
    controlled_substance: bool = False
    requires_prescription: bool = True
    atc_code: Optional[str] = None


class ProductResponse(ProductCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventoryItemCreate(BaseModel):
    product_id: int
    batch_number: str = Field(..., min_length=1, max_length=50)
    serial_number: Optional[str] = None
    expiry_date: datetime
    quantity: Decimal = Field(..., gt=0)
    unit_price: Optional[Decimal] = None
    location_id: Optional[int] = None
    gs1_datamatrix: Optional[str] = None


class GS1ScanRequest(BaseModel):
    """Payload from a GS1 DataMatrix scanner."""
    raw_datamatrix: str = Field(..., description="Raw GS1 DataMatrix string from scanner")
    location_id: int
    movement_type: MovementType = MovementType.ENTRY


class GS1ParsedData(BaseModel):
    gtin: Optional[str] = None
    batch: Optional[str] = None
    serial: Optional[str] = None
    expiry: Optional[str] = None
    raw: str


class InventoryItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    batch_number: str
    serial_number: Optional[str] = None
    expiry_date: datetime
    quantity: Decimal
    location_id: Optional[int] = None
    gs1_datamatrix: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryMovementCreate(BaseModel):
    item_id: int
    movement_type: MovementType
    quantity_delta: Decimal
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    patient_id: Optional[str] = None
    notes: Optional[str] = None
    surgery_id: Optional[int] = None


class InventoryMovementResponse(BaseModel):
    id: int
    item_id: int
    movement_type: MovementType
    quantity_delta: Decimal
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    patient_id: Optional[str] = None
    notes: Optional[str] = None
    signature: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UnitDoseSplitRequest(BaseModel):
    """Split a bulk item into unit-dose packages."""
    source_item_id: int
    doses: int = Field(..., gt=0, le=10000)
    target_location_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Temperature / Cold Chain
# ---------------------------------------------------------------------------

class TemperatureLogCreate(BaseModel):
    location_id: int
    sensor_id: str
    temperature_c: float
    humidity_pct: Optional[float] = None
    mqtt_topic: Optional[str] = None


class TemperatureLogResponse(BaseModel):
    id: int
    location_id: int
    sensor_id: str
    temperature_c: float
    humidity_pct: Optional[float] = None
    is_alert: bool
    alert_severity: Optional[AlertSeverity] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Storage Locations
# ---------------------------------------------------------------------------

class StorageLocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    location_type: Optional[str] = None
    temperature_monitored: bool = False
    hospital_area: Optional[str] = None


class StorageLocationResponse(StorageLocationCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# CEyE / Sterilization
# ---------------------------------------------------------------------------

class SterilizationCycleCreate(BaseModel):
    autoclave_id: str
    cycle_number: str
    temperature_c: Optional[float] = None
    pressure_kpa: Optional[float] = None
    duration_minutes: Optional[int] = None
    instrument_ids: List[int] = []
    notes: Optional[str] = None


class SterilizationStageUpdate(BaseModel):
    stage: str = Field(..., description="washing|inspection|packaging|sterilization|delivery")
    biological_indicator_result: Optional[str] = None
    chemical_indicator_result: Optional[str] = None
    bowie_dick_result: Optional[str] = None
    notes: Optional[str] = None


class SterilizationCycleResponse(BaseModel):
    id: int
    autoclave_id: str
    cycle_number: str
    status: SterilizationStatus
    washing_started_at: Optional[datetime] = None
    washing_completed_at: Optional[datetime] = None
    inspection_completed_at: Optional[datetime] = None
    packaging_completed_at: Optional[datetime] = None
    sterilization_started_at: Optional[datetime] = None
    sterilization_completed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    temperature_c: Optional[float] = None
    pressure_kpa: Optional[float] = None
    duration_minutes: Optional[int] = None
    biological_indicator_result: Optional[str] = None
    chemical_indicator_result: Optional[str] = None
    bowie_dick_result: Optional[str] = None
    operator_id: int
    notes: Optional[str] = None
    signature: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Surgical Instruments
# ---------------------------------------------------------------------------

class SurgicalInstrumentCreate(BaseModel):
    rfid_tag: str
    name: str
    code: str
    instrument_type: Optional[str] = None
    manufacturer: Optional[str] = None
    max_sterilization_cycles: int = 500
    max_usage_cycles: int = 200


class SurgicalInstrumentResponse(BaseModel):
    id: int
    rfid_tag: str
    name: str
    code: str
    instrument_type: Optional[str] = None
    status: InstrumentStatus
    total_sterilization_cycles: int
    total_usage_cycles: int
    max_sterilization_cycles: int
    max_usage_cycles: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Surgery / Operating Room
# ---------------------------------------------------------------------------

class SurgeryCreate(BaseModel):
    surgery_code: str
    patient_id: str
    surgeon_id: int
    procedure_name: str
    operating_room: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    diagnosis_code: Optional[str] = None
    notes: Optional[str] = None
    surgical_set_ids: List[int] = []


class SurgeryResponse(BaseModel):
    id: int
    surgery_code: str
    patient_id: str
    surgeon_id: int
    procedure_name: str
    operating_room: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: SurgeryStatus
    diagnosis_code: Optional[str] = None
    notes: Optional[str] = None
    signature: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AI / NLQ
# ---------------------------------------------------------------------------

class NLQRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)
    context_limit: int = Field(default=5, ge=1, le=20)


class NLQResponse(BaseModel):
    query: str
    answer: str
    sources: List[dict] = []
    model_used: str
    tokens_used: Optional[int] = None


class ClinicalSummaryRequest(BaseModel):
    patient_id: str
    include_medications: bool = True
    include_surgeries: bool = True
    include_sterilization: bool = False
