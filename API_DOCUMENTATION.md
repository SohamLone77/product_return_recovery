# API Documentation: Intelligent Product Returns & Recovery Engine

**Base URL:** `http://localhost:8000`  
**Interactive Docs (Swagger UI):** `http://localhost:8000/docs`  
**ReDoc Specification:** `http://localhost:8000/redoc`  
**OpenAPI JSON:** `http://localhost:8000/openapi.json`  

---

## 1. Overview & Architecture

The Returns & Recovery Backend provides automated intake, physical condition assessment logging, algorithmic recovery decisioning, and real-time operational/financial analytics.

### Reverse Logistics Optimization
- **Single Decision (`POST /decision`):** Evaluates all 7 disposition routes using expected net recovery and determines the incremental repair benefit over the best non-repair fallback.
- **Batch Optimizer (`POST /optimize`):** Solves the reverse logistics knapsack problem across $N$ devices subject to repair bench capacity $K$ (e.g. 4 slots). Maximizes aggregate expected net recovery and compares against FIFO, cheapest-repair, and unconstrained baselines.
- **Demonstration Dataset (`POST /demo/seed`, `GET /demo/dataset`):** Provides 10 synthetic electronic devices with varied characteristics for immediate validation and demonstration.

---

## 2. Endpoints Summary

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/returns` | Create a new return record | `201 Created` |
| `GET` | `/returns` | Retrieve persisted returns with filters and pagination | `200 OK` |
| `POST` | `/assessment` | Submit return physical assessment | `201 Created` |
| `POST` | `/decision` | Compute deterministic recovery decision & alternative routes | `200 OK` |
| `POST` | `/optimize` | Batch optimize repair allocation under capacity constraints | `200 OK` |
| `POST` | `/demo/seed` | Seed 10 synthetic demonstration devices | `201 Created` |
| `GET` | `/demo/dataset` | Inspect synthetic demonstration devices specification | `200 OK` |
| `GET` | `/analytics` | Real-time aggregated financial and operational metrics | `200 OK` |
| `GET` | `/health` | Healthcheck and service metadata | `200 OK` |

---

## 3. Reverse Logistics Economic Model

### 3.1 Expected Net Recovery Formula
For each candidate route:
$$\text{Expected Net Recovery} = \text{Expected Proceeds} - \text{Expected Route Costs}$$

### 3.2 Probabilistic Repair Model
$$\text{Expected Net Repair Recovery} = p_{success} \times V_{success} + (1 - p_{success}) \times C_{failure} - C_{repair} - C_{test} - C_{logistics} - C_{liability}$$
Where:
- $p_{success}$: Estimated probability of successful repair ($0.0 \le p_{success} \le 1.0$).
- $V_{success}$: Resale proceeds post successful repair.
- $C_{failure}$: Fallback proceeds if repair fails (e.g., parts harvest or recycling minus fallback costs).
- $C_{repair}$: Direct parts and technician labor cost.
- $C_{test}$: Diagnostic and quality testing expense.
- $C_{logistics}$: Inward/outward handling and transport allocation.
- $C_{liability}$: Expected post-sale warranty reserve / return liability.

### 3.3 Incremental Repair Benefit
$$\text{Incremental Benefit}_i = \text{Net Repair Recovery}_i - \text{Best Feasible Non-Repair Net Recovery}_i$$
**Core Decision Rule:** A device is only considered for repair if $\text{Incremental Benefit}_i > 0$. Unprofitable repairs are rejected even if repair slots remain open.

---

## 4. Endpoint Specifications

### 4.1 `POST /decision`
Evaluates a single device return record.

#### Request Body
```json
{
  "return_id": "ret_a1b2c3d4e5f6",
  "custom_costs": {
    "repair": 50.0
  }
}
```

#### Response (`200 OK`)
```json
{
  "id": "dec_3c2b1a0f9e8d",
  "return_id": "ret_a1b2c3d4e5f6",
  "recommended_action": "repair",
  "recommended_route": "repair",
  "expected_recovered_value": 810.0,
  "estimated_costs": 155.0,
  "expected_net_recovery": 655.0,
  "best_non_repair_route": "harvest_parts",
  "best_non_repair_net_recovery": 265.0,
  "repair_incremental_benefit": 390.0,
  "incremental_value_vs_next_best_route": 390.0,
  "confidence_score": 0.95,
  "manual_review_required": false,
  "manual_review_reasons": [],
  "flags": [],
  "alternative_routes": [
    {
      "route": "repair",
      "feasible": true,
      "expected_recovered_value": 810.0,
      "route_costs": 155.0,
      "expected_net_recovery": 655.0,
      "cost_breakdown": {
        "repair_parts_labor": 120.0,
        "diagnostic_testing": 12.0,
        "handling_and_logistics": 10.0,
        "post_repair_warranty_liability": 13.0
      },
      "feasibility_note": "Feasible: Technician bench repairable with estimated success probability 95%."
    },
    {
      "route": "harvest_parts",
      "feasible": true,
      "expected_recovered_value": 280.0,
      "route_costs": 15.0,
      "expected_net_recovery": 265.0,
      "cost_breakdown": {"disassembly_labor": 15.0},
      "feasibility_note": "Feasible: High-value reusable modular components."
    }
  ],
  "reason_codes": ["RC_ECONOMIC_REPAIR_OPTIMAL"],
  "explanation": "Repair is economically optimal with positive incremental benefit of +$390.00 over next-best route (harvest_parts).",
  "created_at": "2026-10-10T05:25:00Z"
}
```

---

### 4.2 `POST /optimize`
Batch allocates repair bench slots to maximize total expected net recovery across returns.

#### Request Body
```json
{
  "return_ids": null,
  "repair_capacity_slots": 4,
  "max_repair_hours": null,
  "custom_costs": null
}
```

#### Response (`200 OK`)
```json
{
  "run_id": "opt_9a8b7c6d5e4f",
  "total_devices_evaluated": 10,
  "repair_capacity_slots": 4,
  "repair_slots_used": 4,
  "capacity_utilization_pct": 100.0,
  "optimized_total_net_recovery": 4642.50,
  "baseline_unconstrained_net_recovery": 4642.50,
  "baseline_fifo_net_recovery": 3915.20,
  "baseline_cheapest_repair_net_recovery": 3840.10,
  "dollar_uplift_vs_fifo": 727.30,
  "pct_uplift_vs_fifo": 18.6,
  "dollar_uplift_vs_cheapest": 802.40,
  "pct_uplift_vs_cheapest": 20.9,
  "allocations": [
    {
      "return_id": "ret_demo_01",
      "product_name": "[Synthetic Demo] Flagship Smartphone 15 Pro",
      "category": "Electronics",
      "assigned_route": "repair",
      "expected_proceeds": 811.0,
      "expected_cost": 165.0,
      "expected_net_recovery": 646.0,
      "was_repair_selected": true,
      "repair_feasible": true,
      "repair_incremental_benefit": 381.0,
      "best_non_repair_route": "harvest_parts",
      "best_non_repair_net_recovery": 265.0,
      "repair_hours": 1.5,
      "manual_review_required": false,
      "manual_review_reasons": [],
      "allocation_rationale": "Selected for repair bench slot. Delivers +$381.00 incremental net recovery over fallback 'harvest_parts'."
    }
  ],
  "batch_explanation": "Evaluated 10 returned devices against 4 repair bench slots. Allocated 4/4 slots (100.0% utilization) exclusively to devices delivering positive incremental net recovery. Achieved $4642.50 total expected net recovery, generating +$727.30 (+18.6%) financial uplift over FIFO arrival scheduling and +$802.40 (+20.9%) over naive cheapest-repair scheduling.",
  "comparison_summary": {
    "optimized": {"total_net_recovery": 4642.50, "repairs_selected": 4},
    "baseline_fifo": {"total_net_recovery": 3915.20, "dollar_difference": 727.30, "pct_uplift": 18.6},
    "baseline_cheapest_repair": {"total_net_recovery": 3840.10, "dollar_difference": 802.40, "pct_uplift": 20.9}
  },
  "created_at": "2026-10-10T05:28:00Z"
}
```

---

### 4.3 `POST /demo/seed`
Populates the database with 10 synthetic electronic devices representing:
1. High-value flagship smartphone (strong repair incremental benefit).
2. Ultra gaming laptop (highest repair incremental recovery).
3. Creator tablet (strong positive repair recovery).
4. 4K OLED TV (strong positive repair recovery).
5. Budget phone (repair economically unattractive; negative incremental benefit).
6. Smartwatch (refurbishment beats repair).
7. Crushed PC tower (parts harvesting beats scrap recycling).
8. Smart hub (verified manufacturer warranty claim beats internal rework).
9. Counterfeit earbuds (policy guardrail: manual review).
10. Swollen battery ultrabook (safety guardrail: hazmat manual review).

#### Response (`201 Created`)
```json
{
  "message": "Successfully seeded 10 synthetic demonstration devices.",
  "seeded_count": 10,
  "return_ids": ["ret_demo_...", "..."],
  "repair_capacity_slots": 4
}
```

---

### 4.4 `GET /demo/dataset`
Returns the raw specification of the 10 demonstration devices.
