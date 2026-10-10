# Intelligent Product Returns & Recovery Engine — Reverse Logistics & Optimization

High-performance, explainable REST API backend and reverse logistics decision engine for managing product returns, condition assessments, probabilistic repair modeling, and capacity-constrained batch optimization.

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

3. **Demonstration Dataset (`POST /demo/seed`, `GET /demo/dataset`):**
   - Pre-configured 10 synthetic electronic devices showcasing diverse real-world edge cases:
     - Devices with strong positive repair incremental benefits.
     - Devices where repair is feasible but economically unattractive.
     - Units where cosmetic refurbishment beats repair.
     - Structural write-offs where modular parts harvesting beats scrap recycling.
     - Units where verified manufacturer warranty claim beats internal rework.
     - Policy escalations for counterfeit detection and swollen lithium batteries.

4. **Intake, Assessments, & Analytics:**
   - Validated return creation (`POST /returns`, `GET /returns`).
   - Technical physical assessments (`POST /assessment`).
   - Executive operational analytics (`GET /analytics`).

---

## 🛠️ Technology Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Validation & Schemas:** Pydantic v2
- **Persistence Layer:** SQLAlchemy 2.0 (SQLite by default; supports PostgreSQL / MySQL)
- **ASGI Server:** Uvicorn
- **Testing:** Pytest with HTTPX TestClient (22 automated test suites)

---

## 📦 Setup & Installation

```bash
pip install -r requirements.txt
cp .env.example .env
```

---

## 🏃 Running the Application

Start the local server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Demonstration & Testing

Run all 22 automated tests:
```bash
python -m pytest -v
```

Seed the 10 demonstration devices and run the batch optimizer via curl / API:
```bash
# 1. Seed the 10 synthetic devices
curl -X POST http://localhost:8000/demo/seed

# 2. Run the 4-slot batch optimizer
curl -X POST http://localhost:8000/optimize -H "Content-Type: application/json" -d '{"repair_capacity_slots": 4}'
```
