"""
SQLAlchemy ORM models for Hospitraze ERP.
Covers: Users/RBAC, Pharmacy, CEyE, Operating Room, Audit Trail.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, Float, JSON,
    BigInteger,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PHARMACIST = "pharmacist"
    NURSE = "nurse"
    SURGEON = "surgeon"
    STERILIZATION_TECH = "sterilization_tech"
    VIEWER = "viewer"


class MovementType(str, enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    SPLIT = "split"
    DISPENSATION = "dispensation"


class SterilizationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINE = "quarantine"


class InstrumentStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    STERILIZING = "sterilizing"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class SurgeryStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Users & RBAC
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True, nullable=False)
    professional_id = Column(String(100))  # Cédula profesional
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    audit_logs = relationship("AuditLog", back_populates="user", lazy="dynamic")
    inventory_movements = relationship("InventoryMovement", back_populates="performed_by_user")
    surgeries_as_surgeon = relationship("Surgery", back_populates="surgeon", foreign_keys="Surgery.surgeon_id")


# ---------------------------------------------------------------------------
# Pharmacy Module
# ---------------------------------------------------------------------------

class Product(Base):
    """Master catalog of pharmaceutical products with GS1 attributes."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    gtin = Column(String(14), unique=True, nullable=False, index=True)  # GS1 GTIN-14
    name = Column(String(255), nullable=False)
    generic_name = Column(String(255))
    manufacturer = Column(String(255))
    concentration = Column(String(100))
    pharmaceutical_form = Column(String(100))  # tablet, vial, ampoule, etc.
    unit_of_measure = Column(String(50), default="piece")
    requires_cold_chain = Column(Boolean, default=False)
    cold_chain_min_temp = Column(Float)  # °C
    cold_chain_max_temp = Column(Float)  # °C
    controlled_substance = Column(Boolean, default=False)
    requires_prescription = Column(Boolean, default=True)
    atc_code = Column(String(20))  # WHO ATC classification
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    inventory_items = relationship("InventoryItem", back_populates="product")


class InventoryItem(Base):
    """
    Represents a trackable unit or batch of a product.
    Supports GS1 DataMatrix: GTIN + Batch + Serial + Expiry.
    """
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(50), nullable=False)
    serial_number = Column(String(100), index=True)  # GS1 AI(21)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    unit_price = Column(Numeric(12, 2))
    location_id = Column(Integer, ForeignKey("storage_locations.id"))
    parent_item_id = Column(Integer, ForeignKey("inventory_items.id"))  # for unit-dose splits
    gs1_datamatrix = Column(String(500))  # raw scanned string
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "batch_number", "serial_number", name="uq_item_gs1"),
    )

    product = relationship("Product", back_populates="inventory_items")
    location = relationship("StorageLocation", back_populates="inventory_items")
    parent_item = relationship("InventoryItem", remote_side=[id], backref="split_children")
    movements = relationship("InventoryMovement", back_populates="item")


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    location_type = Column(String(50))  # pharmacy, refrigerator, ceye, or_storage
    temperature_monitored = Column(Boolean, default=False)
    hospital_area = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    inventory_items = relationship("InventoryItem", back_populates="location")
    temperature_logs = relationship("TemperatureLog", back_populates="location")


class InventoryMovement(Base):
    """Immutable ledger of every inventory transaction."""
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity_delta = Column(Numeric(12, 3), nullable=False)
    from_location_id = Column(Integer, ForeignKey("storage_locations.id"))
    to_location_id = Column(Integer, ForeignKey("storage_locations.id"))
    patient_id = Column(String(100))  # anonymized/pseudonymized
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text)
    signature = Column(String(256))  # FEA hash
    surgery_id = Column(Integer, ForeignKey("surgeries.id"))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    item = relationship("InventoryItem", back_populates="movements")
    performed_by_user = relationship("User", back_populates="inventory_movements")
    from_location = relationship("StorageLocation", foreign_keys=[from_location_id])
    to_location = relationship("StorageLocation", foreign_keys=[to_location_id])
    surgery = relationship("Surgery", back_populates="inventory_movements")


class TemperatureLog(Base):
    """IoT cold chain monitoring log."""
    __tablename__ = "temperature_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    location_id = Column(Integer, ForeignKey("storage_locations.id"), nullable=False)
    sensor_id = Column(String(100), nullable=False)
    temperature_c = Column(Float, nullable=False)
    humidity_pct = Column(Float)
    is_alert = Column(Boolean, default=False, nullable=False)
    alert_severity = Column(Enum(AlertSeverity))
    mqtt_topic = Column(String(255))
    recorded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    location = relationship("StorageLocation", back_populates="temperature_logs")


# ---------------------------------------------------------------------------
# CEyE Module (Central Sterilization)
# ---------------------------------------------------------------------------

class SurgicalInstrument(Base):
    """Individual surgical instrument with RFID rice-bead tracking."""
    __tablename__ = "surgical_instruments"

    id = Column(Integer, primary_key=True, index=True)
    rfid_tag = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    instrument_type = Column(String(100))
    manufacturer = Column(String(255))
    max_sterilization_cycles = Column(Integer, default=500)
    total_sterilization_cycles = Column(Integer, default=0)
    max_usage_cycles = Column(Integer, default=200)
    total_usage_cycles = Column(Integer, default=0)
    status = Column(Enum(InstrumentStatus), default=InstrumentStatus.AVAILABLE, nullable=False)
    next_maintenance_at_cycles = Column(Integer)
    last_maintenance_date = Column(DateTime(timezone=True))
    decommission_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sterilization_set_items = relationship("SurgicalSetItem", back_populates="instrument")


class SurgicalSet(Base):
    """A named set of instruments used together (e.g., 'Laparoscopy Basic Set')."""
    __tablename__ = "surgical_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    items = relationship("SurgicalSetItem", back_populates="surgical_set")
    surgery_sets = relationship("SurgerySet", back_populates="surgical_set")


class SurgicalSetItem(Base):
    __tablename__ = "surgical_set_items"

    id = Column(Integer, primary_key=True)
    surgical_set_id = Column(Integer, ForeignKey("surgical_sets.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("surgical_instruments.id"), nullable=False)
    quantity_required = Column(Integer, default=1, nullable=False)

    surgical_set = relationship("SurgicalSet", back_populates="items")
    instrument = relationship("SurgicalInstrument", back_populates="sterilization_set_items")


class SterilizationCycle(Base):
    """
    Autoclave sterilization cycle log per CEyE workflow:
    Washing → Inspection → Packaging → Sterilization → Delivery.
    """
    __tablename__ = "sterilization_cycles"

    id = Column(Integer, primary_key=True, index=True)
    autoclave_id = Column(String(100), nullable=False, index=True)
    cycle_number = Column(String(50), nullable=False)
    status = Column(Enum(SterilizationStatus), default=SterilizationStatus.PENDING, nullable=False)

    # Timestamps for each stage
    washing_started_at = Column(DateTime(timezone=True))
    washing_completed_at = Column(DateTime(timezone=True))
    inspection_completed_at = Column(DateTime(timezone=True))
    packaging_completed_at = Column(DateTime(timezone=True))
    sterilization_started_at = Column(DateTime(timezone=True))
    sterilization_completed_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    # Sterilization parameters
    temperature_c = Column(Float)
    pressure_kpa = Column(Float)
    duration_minutes = Column(Integer)

    # Indicator results
    biological_indicator_result = Column(String(50))  # pass/fail/pending
    chemical_indicator_result = Column(String(50))
    bowie_dick_result = Column(String(50))

    # Operator
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text)
    signature = Column(String(256))  # FEA
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    operator = relationship("User")
    instrument_cycles = relationship("InstrumentCycleLog", back_populates="cycle")

    __table_args__ = (
        UniqueConstraint("autoclave_id", "cycle_number", name="uq_autoclave_cycle"),
    )


class InstrumentCycleLog(Base):
    """Maps instruments to sterilization cycles."""
    __tablename__ = "instrument_cycle_logs"

    id = Column(Integer, primary_key=True)
    cycle_id = Column(Integer, ForeignKey("sterilization_cycles.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("surgical_instruments.id"), nullable=False)

    cycle = relationship("SterilizationCycle", back_populates="instrument_cycles")
    instrument = relationship("SurgicalInstrument")


# ---------------------------------------------------------------------------
# Operating Room Module
# ---------------------------------------------------------------------------

class Surgery(Base):
    """Trans-operative registry associating sets, medicines, patient, and surgeon."""
    __tablename__ = "surgeries"

    id = Column(Integer, primary_key=True, index=True)
    surgery_code = Column(String(100), unique=True, nullable=False, index=True)
    patient_id = Column(String(100), nullable=False, index=True)  # pseudonymized
    patient_name_hash = Column(String(256))  # SHA-256 of full name for verification
    surgeon_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    procedure_name = Column(String(255), nullable=False)
    operating_room = Column(String(50))
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    status = Column(Enum(SurgeryStatus), default=SurgeryStatus.SCHEDULED, nullable=False)
    diagnosis_code = Column(String(20))  # ICD-10
    notes = Column(Text)
    signature = Column(String(256))  # FEA
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    surgeon = relationship("User", back_populates="surgeries_as_surgeon", foreign_keys=[surgeon_id])
    surgery_sets = relationship("SurgerySet", back_populates="surgery")
    inventory_movements = relationship("InventoryMovement", back_populates="surgery")


class SurgerySet(Base):
    """Links a surgical set to a surgery with sterilization cycle reference."""
    __tablename__ = "surgery_sets"

    id = Column(Integer, primary_key=True)
    surgery_id = Column(Integer, ForeignKey("surgeries.id"), nullable=False)
    surgical_set_id = Column(Integer, ForeignKey("surgical_sets.id"), nullable=False)
    sterilization_cycle_id = Column(Integer, ForeignKey("sterilization_cycles.id"))
    notes = Column(Text)

    surgery = relationship("Surgery", back_populates="surgery_sets")
    surgical_set = relationship("SurgicalSet", back_populates="surgery_sets")
    sterilization_cycle = relationship("SterilizationCycle")


# ---------------------------------------------------------------------------
# Audit Trail (NOM-024 compliance)
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """
    Immutable audit trail of all data modifications.
    Implements NOM-024-SSA3-2012 § 7.3 audit requirements.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100))
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    signature = Column(String(256))  # FEA hash of the log entry
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")
