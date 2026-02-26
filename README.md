# Hospitraze ERP — Sistema de Trazabilidad Hospitalaria de Alta Precisión

[![Backend Tests](https://img.shields.io/badge/tests-18%20passed-brightgreen)](backend/tests)
[![NOM-024](https://img.shields.io/badge/NOM--024--SSA3-2012-blue)](https://dof.gob.mx)
[![NOM-241](https://img.shields.io/badge/NOM--241--SSA1-2025-blue)](https://dof.gob.mx)

A modular, full-stack ERP for hospital traceability (Pharmacy, CEyE, and Operating Room) with AI-powered natural language queries. Compliant with Mexican regulations **NOM-024-SSA3-2012** (Electronic Health Records) and **NOM-241-SSA1-2025** (Software as Medical Device/SaMD).

---

## 🏥 Modules

| Module | Features |
|--------|----------|
| **Farmacia** | GS1 DataMatrix scanning (GTIN/Batch/Serial/Expiry), unit-dose splitting, cold-chain IoT monitoring, inventory movements |
| **CEyE** | Full sterilization workflow (Washing→Inspection→Packaging→Sterilization→Delivery), Autoclave cycle logging, biological/chemical indicator results, RFID instrument tracking |
| **Quirófano** | Trans-operative registry, patient-surgeon association, surgical set tracking, real-time inventory deduction, FEA digital signature |
| **IA (RAG)** | Natural language queries ("What Propofol expires in March?"), clinical summaries via Gemini 2.0 Flash or GPT-4o |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15 + React 19 + Tailwind CSS (PWA, mobile-optimized) |
| **Backend** | Python FastAPI (async, microservices-ready) |
| **Database** | PostgreSQL 16 (SQLAlchemy ORM + Alembic migrations) |
| **Vector DB** | ChromaDB (for RAG embeddings) |
| **Cache/Queue** | Redis + Celery |
| **IoT** | MQTT (Eclipse Mosquitto) for cold-chain sensors and RFID readers |
| **AI** | Google Gemini 2.0 Flash / OpenAI GPT-4o |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Google AI or OpenAI API key for AI features

### 1. Clone & Configure
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set:
# SECRET_KEY=<your-256-bit-random-key>
# GOOGLE_API_KEY=<your-gemini-api-key>  # for AI features
```

### 2. Run All Services
```bash
docker-compose up -d
```

Services started:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **ChromaDB**: localhost:8001

### 3. Initialize Database
```bash
docker-compose exec backend alembic upgrade head
```

---

## 📋 API Reference

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

### Key Endpoints

```
POST   /api/v1/auth/login           Login
POST   /api/v1/auth/register        Register user

POST   /api/v1/pharmacy/scan        GS1 DataMatrix scan
GET    /api/v1/pharmacy/inventory   List inventory
POST   /api/v1/pharmacy/movements   Record movement
POST   /api/v1/pharmacy/unit-dose/split  Split unit doses
POST   /api/v1/pharmacy/temperature Log cold-chain temperature

POST   /api/v1/ceye/cycles          Create sterilization cycle
PATCH  /api/v1/ceye/cycles/{id}/advance  Advance to next stage
GET    /api/v1/ceye/instruments     List instruments by RFID

POST   /api/v1/or/surgeries         Register surgery
PATCH  /api/v1/or/surgeries/{id}/start    Start surgery
PATCH  /api/v1/or/surgeries/{id}/complete Complete + FEA sign

POST   /api/v1/ai/query             Natural language query
POST   /api/v1/ai/clinical-summary  Patient clinical summary
```

---

## 🧪 Running Tests

```bash
cd backend
pip install -r requirements.txt aiosqlite
pytest tests/test_api.py -v
```

All 18 tests cover: auth, pharmacy (products, inventory, GS1 scanning, locations), CEyE (cycle lifecycle, indicator results), OR (surgery lifecycle, FEA signatures), and compliance (FEA signing/verification).

---

## 🔒 Compliance Features

| Requirement | Implementation |
|-------------|----------------|
| **FEA (Firma Electrónica Avanzada)** | HMAC-SHA256 signature on every clinical record (inventory movements, sterilization cycles, surgeries) |
| **Audit Trail** | Immutable `audit_logs` table: who, when, what, IP, user-agent, signed |
| **RBAC** | Roles: `admin`, `pharmacist`, `nurse`, `surgeon`, `sterilization_tech`, `viewer` |
| **PHI Privacy** | Patient IDs are pseudonymized; patient name stored as SHA-256 hash only |
| **Data Retention** | 10-year audit log retention configured (NOM-024 requirement) |
| **Traceability** | Complete lineage: GTIN → Batch → Serial → Expiry → Movement → Patient → Surgery |

---

## 🏗 Project Structure

```
hospitraze-erp/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # REST endpoints (auth, pharmacy, ceye, or, ai)
│   │   ├── ai/                  # RAG service (Gemini/GPT-4o)
│   │   ├── core/                # Config, security, FEA signing
│   │   ├── db/                  # SQLAlchemy session
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Pydantic schemas
│   │   └── services/            # Business logic
│   ├── alembic/                 # DB migrations
│   └── tests/                   # pytest test suite
├── frontend/
│   └── src/app/
│       ├── dashboard/           # Main ERP UI
│       │   ├── pharmacy/        # Pharmacy module
│       │   ├── ceye/            # Sterilization module
│       │   ├── or/              # Operating Room module
│       │   └── ai/              # AI assistant
│       └── login/               # Authentication
├── mosquitto/config/            # MQTT broker config
└── docker-compose.yml           # Full-stack deployment
```

---

## 📦 GS1 DataMatrix Format

The scanner endpoint accepts both FNC1-separated and concatenated GS1 formats:

```
FNC1:         01<GTIN(14)>  ␝  17<YYMMDD>  ␝  10<BATCH>  ␝  21<SERIAL>
Concatenated: 01<GTIN(14)>17<YYMMDD>10<BATCH>21<SERIAL>
```

---

## 🤖 AI Natural Language Queries

With a valid API key configured, you can ask questions like:

- *"¿Cuál es nuestro stock actual de Propofol que vence en marzo?"*
- *"Lista todas las cirugías donde se usaron instrumentos del Autoclave #2 hoy."*
- *"¿Qué medicamentos controlados tenemos con menos de 10 unidades?"*

The RAG pipeline gathers relevant database records as context and sends them to the LLM.
