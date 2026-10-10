# Intelligent Product Returns & Recovery Engine — Backend Service

High-performance, explainable REST API backend for managing product returns, physical assessments, net recovery route optimization, and operational analytics.

---

## 🚀 Key Features

1. **Return Intake (`POST /returns`, `GET /returns`):** Validated ingestion with UUID tracking, status lifecycle, pagination, and multi-criteria filtering.
2. **Assessment Logging (`POST /assessment`):** Granular intake for condition, defect categories, verified vs. user-reported warranty status, and fraud risk detection.
3. **Deterministic Decision Engine (`POST /decision`):** Multi-route expected net recovery optimization across 9 disposition paths with explainable reason codes.
4. **Operations & Financial Analytics (`GET /analytics`):** Real-time deduplicated metrics for conditions, warranties, disposition actions, and net recovery totals.
5. **Interactive API Specs:** Auto-generated OpenAPI / Swagger UI at `/docs` and ReDoc at `/redoc`.

---

## 🛠️ Technology Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Validation & Schemas:** Pydantic v2
- **Persistence Layer:** SQLAlchemy 2.0 (SQLite by default; supports PostgreSQL / MySQL)
- **ASGI Server:** Uvicorn
- **Testing:** Pytest with HTTPX TestClient

---

## 📦 Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Default settings:
```ini
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./returns.db
LOG_LEVEL=INFO
DEBUG=True
```

---

## 🏃 Running the Backend Server

Start the development server with live reload:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started:
- API Root: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

---

## 🧪 Running Automated Tests

Run the full Pytest test suite:
```bash
python -m pytest -v
```

All 14 tests verify:
- Valid return creation and persistence
- Schema validation & invalid payload rejection
- Pagination and category filtering
- Foreign key integrity & 404 handling on invalid return IDs
- Decision engine formulas (`Net Recovery = Recovered Value - Costs`)
- Ambiguous data and fraud flagging (`manual_assessment`)
- Analytics accuracy and deduplication
- Persistence across application restarts
- Safe 500 error sanitization without stack trace leakage

---

## 🤝 Team Coordination & Integrations

- **Person 2 (Return Assessment Module):** Send `POST /assessment` payloads with physical condition, defect classification, and warranty eligibility.
- **Dashboard Developer:** Connect to `GET /returns` for return queues, `POST /decision` for recommendation cards, and `GET /analytics` for operational charts and financial metrics.
