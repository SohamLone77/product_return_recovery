# Intelligent Product Returns & Recovery Engine

High-performance, explainable REST API backend and reverse logistics decision engine for managing product returns, condition assessments, probabilistic repair modeling, device intelligence, and capacity-constrained batch optimization.

---

## 🚀 Key Reverse Logistics Capabilities

1. **Probabilistic Economic Decision Engine (`POST /decision`):**
   - Evaluates all 7 disposition routes: Restock, Repair, Refurbish, Return to Supplier, Harvest Parts, Recycle, Dispose.
   - Computes expected net recovery:
     $$\text{Expected Net Repair Recovery} = p_{success} \times V_{success} + (1 - p_{success}) \times C_{failure} - C_{repair} - C_{test} - C_{logistics} - C_{liability}$$
   - Calculates **Incremental Repair Benefit** over best non-repair fallback.
   - Enforces policy guardrails for safety hazards (e.g. swollen lithium batteries) and counterfeit risks.

2. **Batch Capacity Optimizer (`POST /optimize`):**
   - Solves the reverse logistics knapsack problem for $N$ devices across $K$ technician bench slots (default: 4 slots).
   - Allocates slots exclusively to devices with positive incremental benefit ($\Delta > 0$).
   - Avoids wasteful naive strategies: leaves slots open if repairs are economically unattractive.
   - Computes rigorous financial uplifts against **FIFO (Arrival-Order)** and **Cheapest-Repair** baselines.

3. **Return Assessment & Intake Pipeline (`POST /assessment`):**
   - Multi-step intake flow to evaluate returned merchandise and classify physical conditions (`New / unopened`, `Like new`, `Used`, `Damaged`, `Non-functional`).
   - Technical defect categorization, image attachments, and warranty entitlement checks.
   - Preliminary disposition heuristic calculations with explainable rationale.

4. **AI Device Intelligence & Authenticity Engine:**
   - Authenticity screening (genuine vs. counterfeit risk scoring).
   - Repairability and component defect scoring.
   - 10 synthetic real-world edge case demonstration records.

5. **Operations & Financial Analytics (`GET /analytics`):**
   - Real-time metrics for conditions, warranties, disposition actions, and net recovery totals.

---

## 🛠️ Technology Stack & Architecture

```text
product_return_recovery/
├── app/                        # Modular FastAPI Backend Engine
│   ├── main.py                 # FastAPI application, OpenAPI docs, and static routes
│   ├── config.py               # Pydantic environment configuration
│   ├── database.py             # SQLAlchemy 2.0 SQLite persistence
│   ├── models.py               # Database ORM models
│   ├── schemas.py              # Pydantic v2 schemas
│   ├── decision_engine.py      # Probabilistic recovery & batch capacity knapsack
│   ├── analytics_service.py    # Aggregate financial & operational reporting
│   └── routers/                # Endpoints for returns, assessment, decision, analytics
├── app.py                      # Flask Device Assessment & Intake Engine
├── run_demo.py                 # 10-fixture terminal demo runner
├── requirements.txt            # Unified project dependencies
├── static/                     # Frontend Web Dashboards
│   ├── index.html              # Interactive Reverse Logistics Executive Dashboard
│   ├── assessment-wizard.html  # Multi-step Return Assessment Intake Wizard
│   ├── device-assessment.html  # AI Device Intelligence Console
│   ├── css/                    # Stylesheets
│   └── js/                     # Modular frontend logic & API clients
└── tests/                      # Automated Test Suites (75 tests across pytest & unittest)
```

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

---

## 🏃 Running the Application

### Option A: ReverseLogix AI Executive Dashboard & FastAPI Engine (Port 8000)
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Web Dashboard:** [http://localhost:8000/](http://localhost:8000/)
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Option B: Return Assessment & Device Intelligence Console (Port 5001)
```bash
python app.py
```
- **Intake Wizard:** [http://localhost:5001/](http://localhost:5001/)
- **Device Intelligence:** [http://localhost:5001/device-assessment](http://localhost:5001/device-assessment)

### Option C: Run 10-Fixture Demo CLI
```bash
python run_demo.py
```

---

## 🧪 Automated Testing

Run the full automated test suite (75 tests passing):
```bash
python -m pytest -v
```
Or run standard unit tests:
```bash
python -m unittest discover tests
```
