# API Documentation: Intelligent Product Returns & Recovery Engine

**Base URL:** `http://localhost:8000`  
**Interactive Docs (Swagger UI):** `http://localhost:8000/docs`  
**ReDoc Specification:** `http://localhost:8000/redoc`  
**OpenAPI JSON:** `http://localhost:8000/openapi.json`  

---

## 1. Overview & Architecture

The Returns & Recovery Backend provides automated intake, physical condition assessment logging, algorithmic recovery decisioning, and real-time operational/financial analytics.

### Persistence Layer
- **Engine:** SQLite (default) / PostgreSQL / MySQL via SQLAlchemy ORM.
- **Transactions:** Atomic commits on all write operations.
- **Integrity:** Foreign key constraints link assessments and decisions directly to return records with cascade rules.

---

## 2. Endpoints Summary

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/returns` | Create a new return record | `201 Created` |
| `GET` | `/returns` | Retrieve persisted returns with filters and pagination | `200 OK` |
| `POST` | `/assessment` | Submit return physical assessment | `201 Created` |
| `POST` | `/decision` | Compute deterministic recovery decision & alternative routes | `200 OK` |
| `GET` | `/analytics` | Real-time aggregated financial and operational metrics | `200 OK` |
| `GET` | `/health` | Healthcheck and service metadata | `200 OK` |

---

## 3. Endpoint Specifications

### 3.1 `POST /returns`
Create an initial return request.

#### Request Body
```json
{
  "product_id": "SKU-9921",
  "product_name": "Premium Noise-Cancelling Headphones",
  "category": "Electronics",
  "purchase_price": 299.99,
  "currency": "USD",
  "customer_id": "CUST-1001",
  "order_id": "ORD-55421",
  "return_reason": "Ear cup cushion loose on right side"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `product_id` | `string` | **Yes** | Unique product or SKU identifier |
| `product_name` | `string` | **Yes** | Full product title |
| `category` | `string` | **Yes** | Product category (e.g., Electronics, Appliances) |
| `purchase_price` | `float` | **Yes** | Value >= 0.0 |
| `currency` | `string` | No (default `"USD"`) | Currency code |
| `customer_id` | `string` | **Yes** | Unique customer identifier |
| `order_id` | `string` | No | Original sales order identifier |
| `return_reason` | `string` | **Yes** | Customer-reported return reason |

#### Response (`201 Created`)
```json
{
  "id": "ret_a1b2c3d4e5f6",
  "product_id": "SKU-9921",
  "product_name": "Premium Noise-Cancelling Headphones",
  "category": "Electronics",
  "purchase_price": 299.99,
  "currency": "USD",
  "customer_id": "CUST-1001",
  "order_id": "ORD-55421",
  "return_reason": "Ear cup cushion loose on right side",
  "status": "registered",
  "created_at": "2026-10-10T05:20:00Z",
  "updated_at": "2026-10-10T05:20:00Z"
}
```

---

### 3.2 `GET /returns`
Retrieve paginated return records with optional filters.

#### Query Parameters
- `limit` (int, default `50`, min `1`, max `200`): Maximum records to retrieve.
- `offset` (int, default `0`, min `0`): Pagination offset.
- `category` (string, optional): Case-insensitive category match.
- `status` (string, optional): Filter by `registered`, `assessed`, `decided`.

#### Response (`200 OK`)
```json
{
  "items": [
    {
      "id": "ret_a1b2c3d4e5f6",
      "product_id": "SKU-9921",
      "product_name": "Premium Noise-Cancelling Headphones",
      "category": "Electronics",
      "purchase_price": 299.99,
      "currency": "USD",
      "customer_id": "CUST-1001",
      "order_id": "ORD-55421",
      "return_reason": "Ear cup cushion loose on right side",
      "status": "registered",
      "created_at": "2026-10-10T05:20:00Z",
      "updated_at": "2026-10-10T05:20:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### 3.3 `POST /assessment`
Submitted by Person 2 (Return Assessment module) upon physical inspection.

#### Request Body
```json
{
  "return_id": "ret_a1b2c3d4e5f6",
  "product_condition": "minor_damage",
  "defect_category": "functional",
  "defect_description": "Right driver rattling; housing intact.",
  "visible_damage": false,
  "warranty_status": "active",
  "purchase_date": "2025-06-15",
  "warranty_expiry_date": "2026-06-15",
  "verified_warranty_eligible": true,
  "proof_of_purchase_metadata": {
    "receipt_id": "REC-882",
    "retailer": "Direct Store"
  },
  "image_reference": "https://storage.provider.com/returns/ret_a1b2c3d4e5f6.jpg",
  "fraud_risk_score": 0.1,
  "fraud_flags": [],
  "assessor_notes": "All accessories present in original box."
}
```

| Field | Type | Required | Allowed Values / Validation |
|---|---|---|---|
| `return_id` | `string` | **Yes** | Must exist in `returns` table (otherwise returns `404`) |
| `product_condition` | `string` | **Yes** | `unopened`, `like_new`, `minor_damage`, `major_damage`, `defective` |
| `defect_category` | `string` | **Yes** | `none`, `cosmetic`, `functional`, `missing_parts`, `electrical`, `other` |
| `defect_description` | `string` | No | Free-text defect description |
| `visible_damage` | `boolean` | No (default `false`) | Physical damage observed |
| `warranty_status` | `string` | **Yes** | `active`, `expired`, `unknown`, `none` (User-reported) |
| `verified_warranty_eligible` | `boolean` | No | Independently validated warranty eligibility |
| `purchase_date` | `string` | No | Purchase date string |
| `warranty_expiry_date` | `string` | No | Expiration date string |
| `proof_of_purchase_metadata` | `object` | No | Key-value receipt or proof metadata |
| `image_reference` | `string` | No | URL or file storage key |
| `fraud_risk_score` | `float` | No | `0.0` to `1.0` |
| `fraud_flags` | `list[str]`| No | List of detected anomaly codes |
| `assessor_notes` | `string` | No | Internal technician notes |

#### Response (`201 Created`)
```json
{
  "id": "asm_9f8e7d6c5b4a",
  "return_id": "ret_a1b2c3d4e5f6",
  "product_condition": "minor_damage",
  "defect_category": "functional",
  "defect_description": "Right driver rattling; housing intact.",
  "visible_damage": false,
  "warranty_status": "active",
  "purchase_date": "2025-06-15",
  "warranty_expiry_date": "2026-06-15",
  "verified_warranty_eligible": true,
  "proof_of_purchase_metadata": {
    "receipt_id": "REC-882",
    "retailer": "Direct Store"
  },
  "image_reference": "https://storage.provider.com/returns/ret_a1b2c3d4e5f6.jpg",
  "fraud_risk_score": 0.1,
  "fraud_flags": [],
  "assessor_notes": "All accessories present in original box.",
  "created_at": "2026-10-10T05:22:00Z"
}
```

---

### 3.4 `POST /decision`
Evaluates the return condition and computes the highest net recovery route with complete explanations.

#### Request Body
```json
{
  "return_id": "ret_a1b2c3d4e5f6",
  "custom_costs": {
    "inspection": 8.0,
    "repair": 45.0
  }
}
```

#### Response (`200 OK`)
```json
{
  "id": "dec_3c2b1a0f9e8d",
  "return_id": "ret_a1b2c3d4e5f6",
  "recommended_action": "return_to_supplier",
  "expected_recovered_value": 269.99,
  "estimated_costs": 26.0,
  "expected_net_recovery": 243.99,
  "cost_breakdown": {
    "inspection": 8.0,
    "shipping_and_handling": 12.0,
    "rma_processing": 6.0
  },
  "alternative_routes": [
    {
      "route": "restock",
      "feasible": false,
      "expected_recovered_value": 0.0,
      "route_costs": 0.0,
      "expected_net_recovery": -13.0,
      "cost_breakdown": {},
      "feasibility_note": "Infeasible: Product shows wear, damage, or functional defects."
    },
    {
      "route": "return_to_supplier",
      "feasible": true,
      "expected_recovered_value": 269.99,
      "route_costs": 26.0,
      "expected_net_recovery": 243.99,
      "cost_breakdown": {
        "inspection": 8.0,
        "shipping_and_handling": 12.0,
        "rma_processing": 6.0
      },
      "feasibility_note": "Feasible under active supplier warranty with authorized RMA."
    },
    {
      "route": "repair",
      "feasible": true,
      "expected_recovered_value": 239.99,
      "route_costs": 68.0,
      "expected_net_recovery": 171.99,
      "cost_breakdown": {
        "inspection": 8.0,
        "repair_parts_labor": 45.0,
        "testing": 10.0,
        "handling": 5.0
      },
      "feasibility_note": "Feasible for repairable components where recovery value exceeds technician & part costs."
    }
  ],
  "reason_codes": [
    "RC_SUPPLIER_WARRANTY_RECOVERY"
  ],
  "explanation": "Covered under warranty with defect in functional. RMA return to supplier provides highest net recovery of $243.99 with minimal internal costs.",
  "manual_review_required": false,
  "flags": [],
  "capacity_notes": "Single-device deterministic baseline evaluation. Repair bench capacity and technician batch scheduling ready for integration.",
  "created_at": "2026-10-10T05:25:00Z"
}
```

---

### 3.5 `GET /analytics`
Provides aggregated dashboard metrics for executive and operations teams.

#### Response (`200 OK`)
```json
{
  "total_returns": 120,
  "returns_by_condition": {
    "unopened": 45,
    "like_new": 30,
    "minor_damage": 25,
    "major_damage": 12,
    "defective": 8
  },
  "returns_by_warranty_status": {
    "active": 75,
    "expired": 35,
    "none": 10
  },
  "counts_by_recommended_action": {
    "restock": 45,
    "refurbish": 28,
    "return_to_supplier": 22,
    "repair": 15,
    "resell_secondary": 5,
    "manual_assessment": 5
  },
  "total_estimated_recovered_value": 18450.50,
  "total_estimated_processing_costs": 2410.00,
  "total_expected_net_recovery": 16040.50,
  "manual_physical_review_count": 5,
  "fraud_risk_flag_count": 2,
  "records_with_complete_economic_data": 115,
  "accounting_notes": "Financial aggregations calculated strictly across 115 returns with completed decision records. Returns without completed decisions are excluded from financial totals to prevent distorted averages. Each return's latest assessment and decision are used to prevent duplicate counting."
}
```

---

## 4. Error Responses

All error responses strictly follow standard JSON formatting without exposing internal database or stack trace details:

- **400 Bad Request:** Payload malformed or schema violation.
- **404 Not Found:** Referenced resource does not exist (e.g. unknown `return_id`).
- **422 Unprocessable Entity:** Field-level validation failed (e.g. negative price, invalid enum).
- **500 Internal Server Error:** Sanitized error response; trace recorded in secure server logs.
