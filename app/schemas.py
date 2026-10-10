from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

# --- Enums / Valid Values ---
VALID_CONDITIONS = {"unopened", "like_new", "minor_damage", "major_damage", "defective"}
VALID_DEFECT_CATEGORIES = {"none", "cosmetic", "functional", "missing_parts", "electrical", "other"}
VALID_WARRANTY_STATUSES = {"active", "expired", "unknown", "none"}
VALID_ACTIONS = {
    "restock",
    "repair",
    "refurbish",
    "resell_secondary",
    "return_to_supplier",
    "harvest_parts",
    "recycle",
    "dispose",
    "manual_assessment",
}

# --- Return Schemas ---
class ReturnCreate(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=64, description="Unique product or SKU identifier")
    product_name: str = Field(..., min_length=1, max_length=255, description="Full product title")
    category: str = Field(..., min_length=1, max_length=64, description="Product category (e.g. Electronics, Apparel)")
    purchase_price: float = Field(..., ge=0.0, description="Original purchase price paid by customer")
    currency: str = Field(default="USD", max_length=10, description="Currency code (e.g. USD, EUR, INR)")
    customer_id: str = Field(..., min_length=1, max_length=64, description="Identifier of the returning customer")
    order_id: Optional[str] = Field(default=None, max_length=64, description="Associated sales order ID")
    return_reason: str = Field(..., min_length=1, description="Customer-stated reason for return")

    @field_validator("product_id", "product_name", "category", "customer_id", "return_reason")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped


class ReturnResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    category: str
    purchase_price: float
    currency: str
    customer_id: str
    order_id: Optional[str]
    return_reason: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReturnListResponse(BaseModel):
    items: List[ReturnResponse]
    total: int
    limit: int
    offset: int


# --- Assessment Schemas ---
class AssessmentCreate(BaseModel):
    return_id: str = Field(..., min_length=1, max_length=64, description="Existing return record ID")
    product_condition: str = Field(..., description="Observed condition: unopened, like_new, minor_damage, major_damage, defective")
    defect_category: str = Field(..., description="Defect classification: none, cosmetic, functional, missing_parts, electrical, other")
    defect_description: Optional[str] = Field(default=None, description="Detailed defect explanation")
    visible_damage: bool = Field(default=False, description="Flag for physically observable damage")
    warranty_status: str = Field(..., description="User-reported warranty status: active, expired, unknown, none")
    purchase_date: Optional[str] = Field(default=None, description="Original purchase date (YYYY-MM-DD or ISO)")
    warranty_expiry_date: Optional[str] = Field(default=None, description="Warranty expiration date if known")
    verified_warranty_eligible: Optional[bool] = Field(default=None, description="Independently verified warranty eligibility")
    proof_of_purchase_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata or receipt verification info")
    image_reference: Optional[str] = Field(default=None, description="Image reference or storage link")
    fraud_risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Fraud indicator score (0.0 to 1.0)")
    fraud_flags: Optional[List[str]] = Field(default=None, description="Identified fraud signals or anomaly codes")
    assessor_notes: Optional[str] = Field(default=None, description="Internal notes from inspecting technician")

    @field_validator("product_condition")
    @classmethod
    def validate_condition(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in VALID_CONDITIONS:
            raise ValueError(f"Invalid product_condition '{v}'. Must be one of: {sorted(list(VALID_CONDITIONS))}")
        return lowered

    @field_validator("defect_category")
    @classmethod
    def validate_defect_cat(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in VALID_DEFECT_CATEGORIES:
            raise ValueError(f"Invalid defect_category '{v}'. Must be one of: {sorted(list(VALID_DEFECT_CATEGORIES))}")
        return lowered

    @field_validator("warranty_status")
    @classmethod
    def validate_warranty(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in VALID_WARRANTY_STATUSES:
            raise ValueError(f"Invalid warranty_status '{v}'. Must be one of: {sorted(list(VALID_WARRANTY_STATUSES))}")
        return lowered


class AssessmentResponse(BaseModel):
    id: str
    return_id: str
    product_condition: str
    defect_category: str
    defect_description: Optional[str]
    visible_damage: bool
    warranty_status: str
    purchase_date: Optional[str]
    warranty_expiry_date: Optional[str]
    verified_warranty_eligible: Optional[bool]
    proof_of_purchase_metadata: Optional[Dict[str, Any]]
    image_reference: Optional[str]
    fraud_risk_score: Optional[float]
    fraud_flags: Optional[List[str]]
    assessor_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Decision Schemas ---
class DecisionRequest(BaseModel):
    return_id: str = Field(..., min_length=1, max_length=64, description="Return record ID to evaluate")
    custom_costs: Optional[Dict[str, float]] = Field(default=None, description="Optional custom route costs override")


class RouteComparison(BaseModel):
    route: str
    feasible: bool
    expected_recovered_value: float
    route_costs: float
    expected_net_recovery: float
    cost_breakdown: Dict[str, float]
    feasibility_note: str


class DecisionResponse(BaseModel):
    id: str
    return_id: str
    recommended_action: str
    expected_recovered_value: float
    estimated_costs: float
    expected_net_recovery: float
    cost_breakdown: Dict[str, float]
    alternative_routes: List[RouteComparison]
    reason_codes: List[str]
    explanation: str
    manual_review_required: bool
    flags: List[str]
    capacity_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Analytics Schemas ---
class AnalyticsResponse(BaseModel):
    total_returns: int
    returns_by_condition: Dict[str, int]
    returns_by_warranty_status: Dict[str, int]
    counts_by_recommended_action: Dict[str, int]
    total_estimated_recovered_value: float
    total_estimated_processing_costs: float
    total_expected_net_recovery: float
    manual_physical_review_count: int
    fraud_risk_flag_count: int
    records_with_complete_economic_data: int
    accounting_notes: str
