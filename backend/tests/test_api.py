"""
Tests for Hospitraze ERP backend.
Uses pytest with in-memory SQLite for fast execution.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.models.models import User, UserRole, Product
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Test Database Setup (SQLite in-memory)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def create_test_user(db: AsyncSession, role: UserRole = UserRole.PHARMACIST) -> User:
    user = User(
        email=f"test_{role.value}@hospitraze.mx",
        full_name=f"Test {role.value.title()}",
        hashed_password=get_password_hash("TestPassword123!"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_auth_token(client: AsyncClient, email: str, password: str = "TestPassword123!") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Hospitraze" in data["app"]


# ---------------------------------------------------------------------------
# Auth Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_and_login(client, db_session):
    # Register
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "pharmacist@hospitraze.mx",
        "full_name": "Test Pharmacist",
        "password": "SecurePass123!",
        "role": "pharmacist",
    })
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert data["email"] == "pharmacist@hospitraze.mx"
    assert data["role"] == "pharmacist"

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "pharmacist@hospitraze.mx",
        "password": "SecurePass123!",
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, db_session):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@hospitraze.mx",
        "password": "wrongpass",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client, db_session):
    payload = {
        "email": "dup@hospitraze.mx",
        "full_name": "Dup User",
        "password": "SecurePass123!",
        "role": "viewer",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_me(client, db_session):
    await client.post("/api/v1/auth/register", json={
        "email": "me@hospitraze.mx",
        "full_name": "Me User",
        "password": "TestPassword123!",
        "role": "pharmacist",
    })
    token = await get_auth_token(client, "me@hospitraze.mx")
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@hospitraze.mx"

# ---------------------------------------------------------------------------
# Pharmacy - Products
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_list_products(client, db_session):
    user = await create_test_user(db_session, UserRole.PHARMACIST)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    product_data = {
        "gtin": "07501234567890",
        "name": "Propofol 10mg/mL",
        "generic_name": "Propofol",
        "manufacturer": "AstraZeneca",
        "concentration": "10mg/mL",
        "pharmaceutical_form": "vial",
        "requires_cold_chain": False,
        "controlled_substance": True,
    }
    create_resp = await client.post("/api/v1/pharmacy/products", json=product_data, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["gtin"] == "07501234567890"
    assert created["name"] == "Propofol 10mg/mL"

    list_resp = await client.get("/api/v1/pharmacy/products", headers=headers)
    assert list_resp.status_code == 200
    products = list_resp.json()
    assert len(products) >= 1
    assert any(p["gtin"] == "07501234567890" for p in products)


@pytest.mark.asyncio
async def test_create_storage_location(client, db_session):
    user = await create_test_user(db_session, UserRole.PHARMACIST)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/pharmacy/locations", json={
        "name": "Refrigerador Farmacia A",
        "code": "RFRIG-A",
        "location_type": "refrigerator",
        "temperature_monitored": True,
        "hospital_area": "farmacia",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "RFRIG-A"
    assert data["temperature_monitored"] is True


@pytest.mark.asyncio
async def test_add_inventory_item(client, db_session):
    user = await create_test_user(db_session, UserRole.PHARMACIST)
    # Create product and location in DB first
    product = Product(
        gtin="07501234567891",
        name="Midazolam 5mg/mL",
        generic_name="Midazolam",
        manufacturer="Roche",
        pharmaceutical_form="vial",
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.commit()

    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/pharmacy/inventory", json={
        "product_id": product.id,
        "batch_number": "LT2024001",
        "serial_number": "SN-0001",
        "expiry_date": "2026-12-31T00:00:00Z",
        "quantity": "100",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["batch_number"] == "LT2024001"
    assert float(data["quantity"]) == 100.0


# ---------------------------------------------------------------------------
# GS1 Parser Tests (unit tests, no DB needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_gs1_datamatrix():
    from app.services.gs1_parser import parse_gs1_datamatrix

    # Standard GS1 with FNC1 separator
    raw = "0107501234567890\x1d17260331\x1d10LOT123\x1d21SER456"
    result = parse_gs1_datamatrix(raw)
    assert result.gtin == "07501234567890"
    assert result.expiry == "260331"
    assert result.batch == "LOT123"
    assert result.serial == "SER456"


@pytest.mark.asyncio
async def test_parse_gs1_concatenated():
    from app.services.gs1_parser import parse_gs1_datamatrix

    raw = "0107501234567890172603311010BATCH2"
    result = parse_gs1_datamatrix(raw)
    assert result.gtin == "07501234567890"
    assert result.expiry == "260331"


# ---------------------------------------------------------------------------
# CEyE - Sterilization Cycles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_sterilization_cycle(client, db_session):
    user = await create_test_user(db_session, UserRole.STERILIZATION_TECH)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/ceye/cycles", json={
        "autoclave_id": "AUT-01",
        "cycle_number": "C2024-001",
        "temperature_c": 134.0,
        "pressure_kpa": 206.0,
        "duration_minutes": 18,
        "instrument_ids": [],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["autoclave_id"] == "AUT-01"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_advance_sterilization_stage(client, db_session):
    user = await create_test_user(db_session, UserRole.STERILIZATION_TECH)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    # Create cycle
    create_resp = await client.post("/api/v1/ceye/cycles", json={
        "autoclave_id": "AUT-02",
        "cycle_number": "C2024-002",
        "instrument_ids": [],
    }, headers=headers)
    cycle_id = create_resp.json()["id"]

    # Advance to washing completion
    adv_resp = await client.patch(
        f"/api/v1/ceye/cycles/{cycle_id}/advance",
        json={"stage": "washing"},
        headers=headers,
    )
    assert adv_resp.status_code == 200
    data = adv_resp.json()
    assert data["washing_completed_at"] is not None

    # Advance to sterilization with indicators
    adv_resp2 = await client.patch(
        f"/api/v1/ceye/cycles/{cycle_id}/advance",
        json={
            "stage": "sterilization",
            "biological_indicator_result": "pass",
            "chemical_indicator_result": "pass",
        },
        headers=headers,
    )
    assert adv_resp2.status_code == 200
    data2 = adv_resp2.json()
    assert data2["biological_indicator_result"] == "pass"

    # Deliver
    adv_resp3 = await client.patch(
        f"/api/v1/ceye/cycles/{cycle_id}/advance",
        json={"stage": "delivery"},
        headers=headers,
    )
    assert adv_resp3.status_code == 200
    assert adv_resp3.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_sterilization_cycle_fail(client, db_session):
    user = await create_test_user(db_session, UserRole.STERILIZATION_TECH)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post("/api/v1/ceye/cycles", json={
        "autoclave_id": "AUT-03",
        "cycle_number": "C2024-003",
        "instrument_ids": [],
    }, headers=headers)
    cycle_id = create_resp.json()["id"]

    # Fail biological indicator
    adv_resp = await client.patch(
        f"/api/v1/ceye/cycles/{cycle_id}/advance",
        json={
            "stage": "sterilization",
            "biological_indicator_result": "fail",
        },
        headers=headers,
    )
    assert adv_resp.status_code == 200
    assert adv_resp.json()["status"] == "failed"


# ---------------------------------------------------------------------------
# Operating Room Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_surgery(client, db_session):
    surgeon = await create_test_user(db_session, UserRole.SURGEON)
    await db_session.commit()
    token = await get_auth_token(client, surgeon.email)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/or/surgeries", json={
        "surgery_code": "QX-2024-001",
        "patient_id": "PAT-123456",
        "surgeon_id": surgeon.id,
        "procedure_name": "Colecistectomía Laparoscópica",
        "operating_room": "QX-01",
        "diagnosis_code": "K80.20",
        "surgical_set_ids": [],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["surgery_code"] == "QX-2024-001"
    assert data["status"] == "scheduled"


@pytest.mark.asyncio
async def test_surgery_lifecycle(client, db_session):
    surgeon = await create_test_user(db_session, UserRole.SURGEON)
    await db_session.commit()
    token = await get_auth_token(client, surgeon.email)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_resp = await client.post("/api/v1/or/surgeries", json={
        "surgery_code": "QX-2024-002",
        "patient_id": "PAT-789012",
        "surgeon_id": surgeon.id,
        "procedure_name": "Apendicectomía",
        "surgical_set_ids": [],
    }, headers=headers)
    surgery_id = create_resp.json()["id"]

    # Start
    start_resp = await client.patch(f"/api/v1/or/surgeries/{surgery_id}/start", headers=headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    # Complete
    complete_resp = await client.patch(
        f"/api/v1/or/surgeries/{surgery_id}/complete", headers=headers
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"
    assert complete_resp.json()["signature"] is not None


# ---------------------------------------------------------------------------
# Cold Chain Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_temperature_log(client, db_session):
    user = await create_test_user(db_session, UserRole.PHARMACIST)
    await db_session.commit()
    token = await get_auth_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    # Create location first
    loc_resp = await client.post("/api/v1/pharmacy/locations", json={
        "name": "Refrigerador Bio",
        "code": "RFRIG-BIO",
        "location_type": "refrigerator",
        "temperature_monitored": True,
    }, headers=headers)
    location_id = loc_resp.json()["id"]

    # Log temperature within range (no alert)
    temp_resp = await client.post("/api/v1/pharmacy/temperature", json={
        "location_id": location_id,
        "sensor_id": "SENSOR-001",
        "temperature_c": 5.0,
        "humidity_pct": 60.0,
    }, headers=headers)
    assert temp_resp.status_code == 201
    data = temp_resp.json()
    assert data["temperature_c"] == 5.0
    assert data["is_alert"] is False


# ---------------------------------------------------------------------------
# FEA Signature Tests
# ---------------------------------------------------------------------------

def test_fea_signature():
    from app.core.fea import compute_record_signature, verify_record_signature
    from datetime import datetime, timezone

    data = "test_record|user_id:1|action:CREATE"
    ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    sig = compute_record_signature(data, ts)
    assert len(sig) == 64  # SHA-256 hex
    assert verify_record_signature(data, sig, ts)
    # Wrong signature should fail
    assert not verify_record_signature(data, "wrongsig", ts)


# ---------------------------------------------------------------------------
# RBAC Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthorized_without_token(client, db_session):
    resp = await client.get("/api/v1/pharmacy/products")
    assert resp.status_code in (401, 403)
