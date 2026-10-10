#!/usr/bin/env python3
"""
Device Intelligence & Return Assessment Engine
Person 2 — Feature Branch: feature/device-assessment

Extends the existing Flask app with:
  POST /api/device-assessment          — Full device assessment submission
  POST /api/device-assessment/authenticity — Authenticity screening
  POST /api/device-assessment/condition   — Condition & repairability scoring
  POST /api/device-assessment/warranty   — Warranty entitlement verification
  GET  /api/device-assessment/returns     — 10 synthetic demo return records
  GET  /api/device-assessment/returns/<id> — Single demo record
  GET  /api/device-assessment/<id>        — Retrieve stored assessment

All AI / ML scoring uses a clearly labelled HEURISTIC RULE ENGINE.
No external model is called, no manufacturer API is invented.
"""

import os
import re
import uuid
import datetime
import json
from typing import Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ─────────────────────────────────────────────
# App bootstrap (reuse existing app if imported)
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ─────────────────────────────────────────────
# In-memory store for demo (replaces DB for hackathon)
# ─────────────────────────────────────────────
_assessment_store: dict = {}          # assessment_id → assessment dict
_returns_store: dict = {}             # return_id     → return record


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

VALID_CATEGORIES = [
    "Smartphones & Tablets",
    "Laptops & Computers",
    "Audio & Wearables",
    "Consumer Electronics",
    "Home Appliances",
    "Cameras & Accessories",
    "Gaming Consoles",
    "Other"
]

VALID_SCREEN_CONDITIONS = [
    "Perfect - no scratches",
    "Minor scratches (non-visible in use)",
    "Visible scratches",
    "Cracked - functional",
    "Cracked - non-functional",
    "Completely shattered",
    "Not applicable"
]

VALID_BODY_CONDITIONS = [
    "Like new",
    "Minor scuffs",
    "Dents/scratches visible",
    "Significant physical damage",
    "Severely damaged"
]

AUTHENTICITY_STATUSES = [
    "likely_genuine",
    "suspicious",
    "likely_counterfeit",
    "unknown"
]

WARRANTY_ELIGIBILITY = [
    "eligible",
    "not_eligible",
    "pending_verification",
    "insufficient_information",
    "manual_review"
]


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _validate_date(date_str: str) -> Optional[datetime.date]:
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.date.fromisoformat(date_str.strip())
    except ValueError:
        return None


def _new_id(prefix: str) -> str:
    suffix = uuid.uuid4().hex[:8].upper()
    date_part = datetime.date.today().strftime("%Y%m%d")
    return f"{prefix}-{date_part}-{suffix}"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3 — AUTHENTICITY SCREENING SERVICE (Rule-Based Demo)
# ═══════════════════════════════════════════════════════════════════════
# Clearly labelled as a RULE-BASED DEMONSTRATION CHECKER.
# No external API is called. No manufacturer database is queried.
# Missing data yields "unknown" or "pending_verification".
# ═══════════════════════════════════════════════════════════════════════

def _run_authenticity_check(data: dict) -> dict:
    """
    Rule-based authenticity risk screener.
    Returns authenticity_status, risk_score, indicators, missing_evidence,
    recommended_action, and confidence_score.

    IMPORTANT: This is a demonstration heuristic. It cannot verify real devices.
    """
    risk_score = 0
    indicators = []
    missing_evidence = []
    confidence = 70  # base confidence for heuristic

    serial = (data.get("serialNumber") or "").strip()
    imei = (data.get("imei") or "").strip()
    manufacturer = (data.get("manufacturer") or "").strip()
    model = (data.get("model") or "").strip()
    category = (data.get("category") or "").strip()
    purchase_price = data.get("claimedPurchasePrice")
    seller_channel = (data.get("sellerChannel") or "").strip().lower()
    invoice_available = data.get("invoiceAvailable", None)
    has_images = bool(data.get("images"))
    label_inconsistency = data.get("labelInconsistency", False)
    packaging_condition = (data.get("packagingCondition") or "").strip().lower()
    serial_on_label = (data.get("serialOnLabel") or "").strip()
    serial_on_device = (data.get("serialOnDevice") or "").strip()
    prev_repair = data.get("previousRepair", False)
    tamper_seals = data.get("tamperSealsIntact", None)

    # --- Missing evidence collection ---
    if not serial and not imei:
        missing_evidence.append("Serial number or IMEI not provided — cannot verify device identity")
        risk_score += 10
        confidence -= 15
    if not invoice_available:
        missing_evidence.append("Purchase invoice not available — purchase authenticity unverified")
        risk_score += 8
    if not has_images:
        missing_evidence.append("No device images provided — visual inspection not possible")
        confidence -= 10
    if not manufacturer:
        missing_evidence.append("Manufacturer not specified")
        risk_score += 5

    # --- Positive signals ---
    if invoice_available:
        indicators.append({"signal": "Invoice available", "impact": "positive"})
    if seller_channel in ["amazon", "flipkart", "croma", "reliance digital", "apple store", "samsung store",
                           "authorized reseller", "manufacturer direct"]:
        indicators.append({"signal": f"Purchase from trusted channel: {seller_channel}", "impact": "positive"})
    else:
        if seller_channel:
            indicators.append({"signal": f"Purchase channel unverified: {seller_channel}", "impact": "neutral"})
            risk_score += 5

    # --- Serial/Label inconsistency ---
    if label_inconsistency:
        risk_score += 30
        indicators.append({"signal": "Label-device inconsistency flagged by intake agent", "impact": "high_risk"})
        confidence -= 5

    if serial_on_label and serial_on_device and serial_on_label != serial_on_device:
        risk_score += 35
        indicators.append({
            "signal": f"Serial number mismatch: label={serial_on_label} vs device={serial_on_device}",
            "impact": "high_risk"
        })

    # --- Tamper seals ---
    if tamper_seals is False:
        risk_score += 20
        indicators.append({"signal": "Tamper seals broken or missing", "impact": "high_risk"})
    elif tamper_seals is True:
        indicators.append({"signal": "Tamper seals intact", "impact": "positive"})

    # --- Packaging ---
    if "damaged" in packaging_condition or "repackaged" in packaging_condition:
        risk_score += 10
        indicators.append({"signal": "Packaging shows signs of damage or repackaging", "impact": "suspicious"})

    # --- Previous unauthorized repair ---
    if prev_repair:
        risk_score += 12
        indicators.append({"signal": "Previous unauthorized repair reported", "impact": "suspicious"})

    # --- Price anomaly for certain categories ---
    price_anomaly_categories = {
        "Smartphones & Tablets": 3000,
        "Laptops & Computers": 15000,
        "Audio & Wearables": 1000,
        "Cameras & Accessories": 5000,
        "Gaming Consoles": 15000
    }
    min_price = price_anomaly_categories.get(category)
    if purchase_price is not None and min_price and isinstance(purchase_price, (int, float)):
        if purchase_price < min_price * 0.3:
            risk_score += 20
            indicators.append({
                "signal": f"Claimed purchase price (₹{purchase_price:,.0f}) is unusually low for {category}",
                "impact": "suspicious"
            })

    # --- IMEI/Serial format check ---
    if imei and not re.fullmatch(r"\d{15}", imei):
        risk_score += 10
        indicators.append({"signal": "IMEI format invalid (must be 15 digits)", "impact": "suspicious"})
    elif imei:
        indicators.append({"signal": "IMEI format appears valid", "impact": "neutral"})

    # --- Determine authenticity status ---
    risk_score = int(_clamp(risk_score))
    if not serial and not imei and not invoice_available:
        status = "unknown"
        action = "request_verification"
    elif risk_score >= 55:
        status = "likely_counterfeit"
        action = "escalate_to_manual_inspection"
    elif risk_score >= 25:
        status = "suspicious"
        action = "request_verification"
    elif risk_score < 10:
        status = "likely_genuine"
        action = "proceed"
    else:
        status = "unknown"
        action = "request_verification"

    confidence = int(_clamp(confidence))

    return {
        "authenticity_status": status,
        "authenticity_risk_score": risk_score,
        "indicators": indicators,
        "missing_evidence": missing_evidence,
        "recommended_action": action,
        "confidence_score": confidence,
        "assessment_method": "RULE_BASED_HEURISTIC_DEMO",
        "disclaimer": (
            "This assessment is a rule-based demonstration heuristic. "
            "It does not connect to any manufacturer verification service. "
            "A suspicious result does not automatically imply customer fraud."
        )
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4 — IMAGE-BASED CONDITION & REPAIRABILITY SCORING
# ═══════════════════════════════════════════════════════════════════════
# No computer-vision model available. Uses a transparent baseline
# driven by structured condition inputs + optional image metadata.
# Output is clearly labelled as a HEURISTIC ESTIMATE.
# ═══════════════════════════════════════════════════════════════════════

def _run_condition_score(data: dict) -> dict:
    """
    Heuristic condition & repairability scorer.
    Uses structured questionnaire inputs. Image count adds confidence.
    """
    score = 100.0
    repairability = 100.0
    observed_defects = []
    limitations = []
    recommended_inspection = []

    screen_condition = (data.get("screenCondition") or "").strip()
    body_condition = (data.get("bodyCondition") or "").strip()
    powers_on = data.get("powersOn")          # True / False / None = unknown
    liquid_damage = data.get("liquidDamage", False)
    impact_damage = data.get("impactDamage", False)
    missing_parts = data.get("missingComponents", False)
    tamper = data.get("tamperingEvidence", False)
    battery_issue = data.get("batteryIssue", False)
    screen_issue = data.get("screenIssue", False)
    charging_issue = data.get("chargingIssue", False)
    mb_issue = data.get("motherboardIssue", False)
    camera_issue = data.get("cameraIssue", False)
    software_issue = data.get("softwareIssue", False)
    customer_symptoms = (data.get("customerSymptoms") or "").strip()
    images = data.get("images") or []
    image_count = len(images) if isinstance(images, list) else 0

    # Confidence starts lower without images
    confidence = 45 + min(image_count * 8, 35)

    # Screen condition impact
    screen_impact = {
        "Perfect - no scratches": 0,
        "Minor scratches (non-visible in use)": -3,
        "Visible scratches": -10,
        "Cracked - functional": -20,
        "Cracked - non-functional": -35,
        "Completely shattered": -50,
        "Not applicable": 0
    }
    delta = screen_impact.get(screen_condition, -5)
    if delta < 0:
        observed_defects.append(f"Screen: {screen_condition}")
    score += delta
    repairability += delta * 0.6

    # Body condition impact
    body_impact = {
        "Like new": 0,
        "Minor scuffs": -5,
        "Dents/scratches visible": -12,
        "Significant physical damage": -22,
        "Severely damaged": -38
    }
    bdelta = body_impact.get(body_condition, -5)
    if bdelta < -5:
        observed_defects.append(f"Body: {body_condition}")
    score += bdelta
    repairability += bdelta * 0.4

    # Powers on
    if powers_on is False:
        score -= 25
        repairability -= 20
        observed_defects.append("Device does not power on")
    elif powers_on is None:
        score -= 5
        limitations.append("Power-on state unknown — physical testing required")
        recommended_inspection.append("Basic power-on and boot test")

    # Liquid damage
    if liquid_damage:
        score -= 30
        repairability -= 40
        observed_defects.append("Liquid/water damage reported")
        limitations.append("Corrosion extent cannot be determined from images alone")
        recommended_inspection.append("Internal board inspection under microscope")

    # Impact damage
    if impact_damage:
        score -= 15
        repairability -= 10
        observed_defects.append("Drop/impact damage reported")

    # Missing parts
    if missing_parts:
        score -= 10
        repairability -= 15
        observed_defects.append("Missing components or accessories")
        recommended_inspection.append("Full parts inventory audit")

    # Tampering
    if tamper:
        score -= 12
        repairability -= 8
        observed_defects.append("Evidence of tampering or unauthorized repair")
        recommended_inspection.append("Internal inspection for non-OEM components")

    # Functional defects
    if battery_issue:
        score -= 8
        repairability -= 10
        observed_defects.append("Battery issue")
    if screen_issue:
        score -= 10
        repairability -= 12
    if charging_issue:
        score -= 7
        repairability -= 8
        observed_defects.append("Charging/power issue")
    if mb_issue:
        score -= 25
        repairability -= 35
        observed_defects.append("Motherboard/internal hardware failure")
        limitations.append("Motherboard faults require bench diagnostics — image estimate unreliable")
        recommended_inspection.append("Full board-level diagnostics")
    if camera_issue:
        score -= 5
        repairability -= 6
    if software_issue:
        score -= 3
        repairability -= 2

    # Clamp scores
    condition_score = int(_clamp(score))
    repairability_score = int(_clamp(repairability))
    confidence_score = int(_clamp(confidence))

    limitations.append(
        "Internal component state (battery capacity, board health) cannot be reliably assessed from images"
    )

    return {
        "condition_score": condition_score,
        "repairability_score": repairability_score,
        "confidence_score": confidence_score,
        "visible_damage": [d for d in observed_defects if any(
            k in d.lower() for k in ["crack", "scratch", "dent", "damage", "liquid", "impact"]
        )],
        "observed_defects": observed_defects,
        "limitations": limitations,
        "recommended_inspection": recommended_inspection,
        "image_count_used": image_count,
        "assessment_method": "HEURISTIC_BASELINE_NO_CV_MODEL",
        "disclaimer": (
            "Condition and repairability scores are heuristic estimates based on structured inputs. "
            "No computer-vision model is active. Scores labeled as HEURISTIC ESTIMATE."
        )
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5 — WARRANTY ENTITLEMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════
# No manufacturer API is called. Uses configurable policy rules.
# Clearly labelled as MOCK/POLICY RULE ENGINE for demonstration.
# Warranty rejection ≠ fraud. These are separate outputs.
# ═══════════════════════════════════════════════════════════════════════

# Standard warranty durations in days by category (demo policy)
_DEFAULT_WARRANTY_DAYS = {
    "Smartphones & Tablets": 365,
    "Laptops & Computers": 365,
    "Audio & Wearables": 180,
    "Consumer Electronics": 365,
    "Home Appliances": 365,
    "Cameras & Accessories": 365,
    "Gaming Consoles": 365,
    "Other": 365
}

# Exclusion triggers — based on commonly known policies (demo approximation)
_WARRANTY_EXCLUSIONS = {
    "liquid_damage": "Physical damage from liquid/moisture is typically excluded from standard warranty.",
    "impact_damage": "Physical damage from drops or impacts is typically excluded from standard warranty.",
    "unauthorized_repair": "Warranty may be voided by unauthorized third-party repair.",
}


def _run_warranty_verification(data: dict) -> dict:
    """
    Policy-rule-based warranty eligibility verifier.
    SOURCE: MOCK_POLICY_RULES — no manufacturer API is connected.
    """
    evidence_used = []
    missing_info = []
    exclusion_reasons = []
    eligibility = "insufficient_information"

    purchase_date_str = (data.get("purchaseDate") or "").strip()
    return_date_str = (data.get("returnDate") or "").strip()
    warranty_claimed = data.get("warrantyClaimed", False)
    invoice_available = data.get("invoiceAvailable", False)
    serial = (data.get("serialNumber") or "").strip()
    category = (data.get("category") or "").strip()
    liquid_damage = data.get("liquidDamage", False)
    impact_damage = data.get("impactDamage", False)
    tamper = data.get("tamperingEvidence", False)
    warranty_start_str = (data.get("warrantyStartDate") or "").strip()
    warranty_end_str = (data.get("warrantyEndDate") or "").strip()

    today = datetime.date.today()
    purchase_date = _validate_date(purchase_date_str)
    return_date = _validate_date(return_date_str) or today
    warranty_start = _validate_date(warranty_start_str)
    warranty_end = _validate_date(warranty_end_str)

    # --- Compute warranty window ---
    if not purchase_date:
        missing_info.append("Purchase date not provided — warranty period cannot be calculated")
        warranty_end_computed = None
    else:
        duration_days = _DEFAULT_WARRANTY_DAYS.get(category, 365)
        warranty_end_computed = purchase_date + datetime.timedelta(days=duration_days)
        evidence_used.append(f"Purchase date: {purchase_date_str}")
        evidence_used.append(f"Standard warranty duration for {category or 'product'}: {duration_days} days")
        if warranty_end:
            evidence_used.append(f"Customer-provided warranty end: {warranty_end_str}")
            # Use customer-provided end if later (benefit of doubt)
            if warranty_end > warranty_end_computed:
                warranty_end_computed = warranty_end

    # --- Invoice & serial ---
    if invoice_available:
        evidence_used.append("Purchase invoice available")
    else:
        missing_info.append("Purchase invoice not available — purchase legitimacy unverified")

    if serial:
        evidence_used.append(f"Serial number provided: {serial}")
    else:
        missing_info.append("Serial number not provided — device identity unverified")

    # --- Exclusion checks ---
    if liquid_damage:
        exclusion_reasons.append(_WARRANTY_EXCLUSIONS["liquid_damage"])
    if impact_damage:
        exclusion_reasons.append(_WARRANTY_EXCLUSIONS["impact_damage"])
    if tamper:
        exclusion_reasons.append(_WARRANTY_EXCLUSIONS["unauthorized_repair"])

    # --- Determine potential repair costs (INR demo values) ---
    in_warranty_cost = 0        # covered by OEM
    out_warranty_cost_map = {   # rough OOW repair estimates in INR
        "Smartphones & Tablets": 8000,
        "Laptops & Computers": 15000,
        "Audio & Wearables": 3000,
        "Consumer Electronics": 6000,
        "Home Appliances": 5000,
        "Cameras & Accessories": 10000,
        "Gaming Consoles": 8000,
        "Other": 7000
    }
    out_warranty_cost = out_warranty_cost_map.get(category, 7000)

    # --- Final eligibility decision ---
    if not purchase_date:
        eligibility = "insufficient_information"
        reason = "Cannot determine warranty eligibility without a purchase date."
    elif not warranty_claimed:
        eligibility = "not_eligible"
        reason = "Customer has not claimed warranty coverage."
    elif exclusion_reasons:
        # Check if all defects are excluded
        if liquid_damage or tamper:
            eligibility = "not_eligible"
            reason = "Return condition matches standard warranty exclusions. " + " ".join(exclusion_reasons)
        elif impact_damage and not (liquid_damage or tamper):
            eligibility = "manual_review"
            reason = "Impact damage may be excluded. Manual policy review recommended."
    elif warranty_end_computed and return_date > warranty_end_computed:
        eligibility = "not_eligible"
        reason = (
            f"Warranty period ended on {warranty_end_computed.isoformat()}. "
            f"Device returned on {return_date.isoformat()} — outside coverage window."
        )
    elif not invoice_available and not serial:
        eligibility = "pending_verification"
        reason = "Awaiting proof of purchase and serial verification before eligibility confirmed."
    elif not invoice_available:
        eligibility = "pending_verification"
        reason = "Invoice required to confirm purchase date and channel. Eligibility pending verification."
    else:
        eligibility = "eligible"
        reason = (
            f"Device appears within warranty period (estimated expiry: "
            f"{warranty_end_computed.isoformat() if warranty_end_computed else 'unknown'}). "
            "Invoice available. No exclusion triggers identified."
        )

    return {
        "warranty_status": eligibility,
        "eligibility_reason": reason,
        "evidence_used": evidence_used,
        "missing_information": missing_info,
        "exclusion_reasons": exclusion_reasons,
        "estimated_warranty_expiry": (
            warranty_end_computed.isoformat() if warranty_end_computed else None
        ),
        "potential_warranty_repair_cost_inr": in_warranty_cost if eligibility == "eligible" else None,
        "estimated_out_of_warranty_repair_cost_inr": out_warranty_cost,
        "verification_source": "MOCK_POLICY_RULES_DEMO",
        "verification_timestamp": _now_iso(),
        "disclaimer": (
            "This warranty evaluation is based on configurable policy rules for demonstration purposes. "
            "No manufacturer API or authorized warranty database was queried. "
            "A warranty rejection does NOT imply customer fraud."
        )
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6 — FULL DEVICE ASSESSMENT ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

def _compute_final_disposition(condition_score, repairability_score,
                                warranty_status, authenticity_status,
                                estimated_repair_cost, estimated_resale_value):
    """
    Preliminary economic disposition heuristic.
    The real economic engine will use complete cost/value data.
    """
    if authenticity_status == "likely_counterfeit":
        return "QUARANTINE_PENDING_INVESTIGATION"
    if authenticity_status == "suspicious":
        return "MANUAL_REVIEW"

    if condition_score >= 90 and repairability_score >= 85:
        return "RESTOCK_AS_NEW"
    if condition_score >= 75:
        return "OPEN_BOX_RESALE"
    if warranty_status == "eligible" and repairability_score >= 50:
        return "WARRANTY_OEM_REPAIR"
    if repairability_score >= 60 and condition_score >= 40:
        return "IN_HOUSE_REFURBISH"
    if condition_score >= 20:
        return "SECONDARY_MARKET_PARTS"
    return "RECYCLE_OR_SCRAP"


def _run_full_assessment(data: dict) -> tuple:
    """
    Orchestrates all four sub-assessments and returns (response_dict, http_status).
    """
    errors = {}

    return_id = (data.get("returnId") or "").strip()
    if not return_id:
        errors["returnId"] = "Return ID is required."

    category = (data.get("category") or "").strip()
    if not category:
        errors["category"] = "Product category is required."

    manufacturer = (data.get("manufacturer") or "").strip()
    model = (data.get("model") or "").strip()
    purchase_date_str = (data.get("purchaseDate") or "").strip()

    if purchase_date_str:
        parsed_pd = _validate_date(purchase_date_str)
        if not parsed_pd:
            errors["purchaseDate"] = "Purchase date must be in YYYY-MM-DD format."
        elif parsed_pd > datetime.date.today():
            errors["purchaseDate"] = "Purchase date cannot be in the future."

    if errors:
        return {"status": "error", "message": "Validation failed.", "errors": errors}, 422

    # Run sub-assessments
    auth_result = _run_authenticity_check(data)
    cond_result = _run_condition_score(data)
    warr_result = _run_warranty_verification(data)

    # Compute cost fields (customer-provided or defaults)
    est_repair_cost = data.get("estimatedRepairCost") or 0
    est_resale_value = data.get("estimatedResaleValue") or 0
    est_parts_value = data.get("estimatedPartsValue") or 0
    est_labor_cost = data.get("estimatedLaborCost") or 0
    est_repair_hours = data.get("estimatedRepairHours") or 0

    disposition = _compute_final_disposition(
        cond_result["condition_score"],
        cond_result["repairability_score"],
        warr_result["warranty_status"],
        auth_result["authenticity_status"],
        est_repair_cost,
        est_resale_value
    )

    # Manual review flag
    manual_review_reasons = []
    if auth_result["authenticity_status"] in ["suspicious", "likely_counterfeit"]:
        manual_review_reasons.append("Authenticity risk flag: " + auth_result["authenticity_status"])
    if auth_result["missing_evidence"]:
        manual_review_reasons.append("Missing evidence: " + "; ".join(auth_result["missing_evidence"][:2]))
    if warr_result["warranty_status"] == "manual_review":
        manual_review_reasons.append("Warranty eligibility requires policy adjudication")
    if cond_result["confidence_score"] < 40:
        manual_review_reasons.append("Condition assessment confidence too low — physical inspection required")

    assessment_id = _new_id("DA")

    now_time = _now_iso()
    response = {
        "status": "success",
        "assessmentId": assessment_id,
        "assessment_id": assessment_id,
        "returnId": return_id,
        "return_id": return_id,
        "assessmentTimestamp": now_time,
        "assessment_timestamp": now_time,

        # Product identity
        "product": {
            "category": category,
            "manufacturer": manufacturer,
            "model": model,
            "serialNumber": (data.get("serialNumber") or "").strip(),
            "imei": (data.get("imei") or "").strip(),
            "purchaseDate": purchase_date_str,
            "returnDate": (data.get("returnDate") or "").strip(),
            "sellerChannel": (data.get("sellerChannel") or "").strip(),
            "claimedPurchasePrice": data.get("claimedPurchasePrice"),
            "invoiceAvailable": data.get("invoiceAvailable", False)
        },

        # Core scores (both camelCase and snake_case for cross-module compatibility)
        "conditionScore": cond_result["condition_score"],
        "condition_score": cond_result["condition_score"],
        "repairabilityScore": cond_result["repairability_score"],
        "repairability_score": cond_result["repairability_score"],
        "confidenceScore": cond_result["confidence_score"],
        "confidence_score": cond_result["confidence_score"],

        # Authenticity
        "authenticityStatus": auth_result["authenticity_status"],
        "authenticity_status": auth_result["authenticity_status"],
        "authenticityRiskScore": auth_result["authenticity_risk_score"],
        "authenticity_risk_score": auth_result["authenticity_risk_score"],

        # Warranty
        "warrantyStatus": warr_result["warranty_status"],
        "warranty_status": warr_result["warranty_status"],

        # Defects & evidence
        "observedDefects": cond_result["observed_defects"],
        "observed_defects": cond_result["observed_defects"],
        "visibleDamage": cond_result["visible_damage"],
        "visible_damage": cond_result["visible_damage"],

        # Economic estimates (INR)
        "estimatedRepairCost": est_repair_cost,
        "estimated_repair_cost": est_repair_cost,
        "estimatedRepairHours": est_repair_hours,
        "estimated_repair_hours": est_repair_hours,
        "estimatedResaleValue": est_resale_value,
        "estimated_resale_value": est_resale_value,
        "estimatedPartsValue": est_parts_value,
        "estimated_parts_value": est_parts_value,
        "estimatedLaborCost": est_labor_cost,
        "estimated_labor_cost": est_labor_cost,

        # Evidence blocks
        "evidence": {
            "authenticity": auth_result,
            "condition": cond_result,
            "warranty": warr_result
        },

        # Disposition
        "preliminaryDisposition": disposition,

        # Review flags
        "manualReviewRequired": bool(manual_review_reasons),
        "manual_review_required": bool(manual_review_reasons),
        "manualReviewReasons": manual_review_reasons,
        "manual_review_reasons": manual_review_reasons,

        # Meta
        "isMock": False,
        "assessmentEngine": "DEVICE_INTELLIGENCE_V1_HEURISTIC"
    }

    # Persist to in-memory store
    _assessment_store[assessment_id] = response

    return response, 201


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7 — SYNTHETIC DEMO RETURN RECORDS (10 devices)
# ═══════════════════════════════════════════════════════════════════════

def _build_demo_returns():
    today = datetime.date.today()

    def d(days_ago):
        return (today - datetime.timedelta(days=days_ago)).isoformat()

    records = [
        {
            "returnId": "RET-DEMO-001",
            "label": "GENUINE — New Sealed Phone, In-Warranty",
            "category": "Smartphones & Tablets",
            "manufacturer": "Apple",
            "model": "iPhone 15 Pro",
            "serialNumber": "F7KNXQR4T1M3",
            "imei": "358142094521063",
            "purchaseDate": d(60),
            "returnDate": d(2),
            "sellerChannel": "Apple Store",
            "claimedPurchasePrice": 134900,
            "invoiceAvailable": True,
            "warrantyClaimed": True,
            "powersOn": True,
            "screenCondition": "Perfect - no scratches",
            "bodyCondition": "Like new",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "tamperSealsIntact": True,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Changed mind — prefer older model",
            "estimatedRepairCost": 0,
            "estimatedResaleValue": 120000,
            "estimatedPartsValue": 0,
            "labelInconsistency": False,
            "images": ["front.jpg", "back.jpg"]
        },
        {
            "returnId": "RET-DEMO-002",
            "label": "GENUINE — Used Laptop, Expired Warranty, Minor Screen Scratch",
            "category": "Laptops & Computers",
            "manufacturer": "Dell",
            "model": "XPS 15 9530",
            "serialNumber": "DXPS9530K2891",
            "purchaseDate": d(400),
            "returnDate": d(1),
            "sellerChannel": "Flipkart",
            "claimedPurchasePrice": 145000,
            "invoiceAvailable": True,
            "warrantyClaimed": False,
            "powersOn": True,
            "screenCondition": "Visible scratches",
            "bodyCondition": "Minor scuffs",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "batteryIssue": True,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Battery holds 40% capacity. Screen has hairline scratches.",
            "estimatedRepairCost": 6500,
            "estimatedResaleValue": 85000,
            "estimatedPartsValue": 20000,
            "labelInconsistency": False,
            "images": ["front.jpg"]
        },
        {
            "returnId": "RET-DEMO-003",
            "label": "SUSPICIOUS — Mismatched Serials, Likely Tampered",
            "category": "Smartphones & Tablets",
            "manufacturer": "Samsung",
            "model": "Galaxy S24 Ultra",
            "serialNumber": "R5CT5004000",
            "imei": "356781234567890",
            "serialOnLabel": "R5CT5004000",
            "serialOnDevice": "R5CT1239871",
            "purchaseDate": d(45),
            "returnDate": d(0),
            "sellerChannel": "Street market",
            "claimedPurchasePrice": 28000,
            "invoiceAvailable": False,
            "warrantyClaimed": True,
            "powersOn": True,
            "screenCondition": "Cracked - functional",
            "bodyCondition": "Significant physical damage",
            "liquidDamage": False,
            "impactDamage": True,
            "missingComponents": True,
            "tamperingEvidence": True,
            "tamperSealsIntact": False,
            "batteryIssue": False,
            "screenIssue": True,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Dropped device. Screen cracked.",
            "labelInconsistency": True,
            "estimatedRepairCost": 22000,
            "estimatedResaleValue": 55000,
            "estimatedPartsValue": 12000,
            "images": []
        },
        {
            "returnId": "RET-DEMO-004",
            "label": "GENUINE — Liquid Damaged Headphones, Warranty Excluded",
            "category": "Audio & Wearables",
            "manufacturer": "Sony",
            "model": "WH-1000XM5",
            "serialNumber": "SNYWH5X2091",
            "purchaseDate": d(90),
            "returnDate": d(0),
            "sellerChannel": "Amazon",
            "claimedPurchasePrice": 26990,
            "invoiceAvailable": True,
            "warrantyClaimed": True,
            "powersOn": False,
            "screenCondition": "Not applicable",
            "bodyCondition": "Significant physical damage",
            "liquidDamage": True,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "batteryIssue": True,
            "screenIssue": False,
            "chargingIssue": True,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Fell into pool. Won't turn on.",
            "estimatedRepairCost": 12000,
            "estimatedResaleValue": 4000,
            "estimatedPartsValue": 5000,
            "images": ["damage1.jpg"]
        },
        {
            "returnId": "RET-DEMO-005",
            "label": "LIKELY COUNTERFEIT — Low Price, IMEI Invalid, No Invoice",
            "category": "Smartphones & Tablets",
            "manufacturer": "Apple",
            "model": "iPhone 15",
            "serialNumber": "FAKE123456",
            "imei": "0000000000",
            "purchaseDate": d(20),
            "returnDate": d(0),
            "sellerChannel": "Unknown vendor",
            "claimedPurchasePrice": 8000,
            "invoiceAvailable": False,
            "warrantyClaimed": True,
            "powersOn": True,
            "screenCondition": "Visible scratches",
            "bodyCondition": "Minor scuffs",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": True,
            "tamperSealsIntact": False,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": True,
            "customerSymptoms": "Device seems slow. iOS version looks different.",
            "labelInconsistency": True,
            "estimatedRepairCost": 0,
            "estimatedResaleValue": 2000,
            "estimatedPartsValue": 1000,
            "images": []
        },
        {
            "returnId": "RET-DEMO-006",
            "label": "GENUINE — Non-functional Gaming Console, In-Warranty, Board Issue",
            "category": "Gaming Consoles",
            "manufacturer": "Sony",
            "model": "PlayStation 5",
            "serialNumber": "PS5CED2034887",
            "purchaseDate": d(200),
            "returnDate": d(0),
            "sellerChannel": "Croma",
            "claimedPurchasePrice": 54990,
            "invoiceAvailable": True,
            "warrantyClaimed": True,
            "powersOn": False,
            "screenCondition": "Not applicable",
            "bodyCondition": "Like new",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "tamperSealsIntact": True,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": True,
            "softwareIssue": False,
            "customerSymptoms": "Console showed blue light of death and stopped powering on.",
            "estimatedRepairCost": 18000,
            "estimatedResaleValue": 35000,
            "estimatedPartsValue": 15000,
            "images": ["front.jpg", "back.jpg", "ports.jpg"]
        },
        {
            "returnId": "RET-DEMO-007",
            "label": "UNKNOWN — No Invoice, No Serial, Partially Functional Camera",
            "category": "Cameras & Accessories",
            "manufacturer": "Canon",
            "model": "EOS R6 Mark II",
            "serialNumber": "",
            "purchaseDate": "",
            "returnDate": d(0),
            "sellerChannel": "Gift — unknown origin",
            "claimedPurchasePrice": None,
            "invoiceAvailable": False,
            "warrantyClaimed": False,
            "powersOn": True,
            "screenCondition": "Cracked - functional",
            "bodyCondition": "Dents/scratches visible",
            "liquidDamage": False,
            "impactDamage": True,
            "missingComponents": True,
            "tamperingEvidence": False,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "cameraIssue": True,
            "softwareIssue": False,
            "customerSymptoms": "Autofocus unreliable. LCD cracked.",
            "estimatedRepairCost": 25000,
            "estimatedResaleValue": 60000,
            "estimatedPartsValue": 18000,
            "images": ["front.jpg"]
        },
        {
            "returnId": "RET-DEMO-008",
            "label": "GENUINE — Refurbishable Home Appliance, Out-of-Warranty",
            "category": "Home Appliances",
            "manufacturer": "Dyson",
            "model": "V15 Detect",
            "serialNumber": "DYV15D88-2023",
            "purchaseDate": d(450),
            "returnDate": d(0),
            "sellerChannel": "Reliance Digital",
            "claimedPurchasePrice": 52900,
            "invoiceAvailable": True,
            "warrantyClaimed": False,
            "powersOn": True,
            "screenCondition": "Not applicable",
            "bodyCondition": "Dents/scratches visible",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": True,
            "tamperingEvidence": False,
            "batteryIssue": True,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Battery drains in 10 minutes. Missing floor head attachment.",
            "estimatedRepairCost": 3500,
            "estimatedResaleValue": 28000,
            "estimatedPartsValue": 8000,
            "images": ["front.jpg", "battery_bay.jpg"]
        },
        {
            "returnId": "RET-DEMO-009",
            "label": "SUSPICIOUS — Repackaged Tablet, Invoice Mismatch Suspected",
            "category": "Smartphones & Tablets",
            "manufacturer": "Samsung",
            "model": "Galaxy Tab S9",
            "serialNumber": "R52Y234X001",
            "purchaseDate": d(30),
            "returnDate": d(0),
            "sellerChannel": "Third-party reseller",
            "claimedPurchasePrice": 45000,
            "invoiceAvailable": True,
            "warrantyClaimed": True,
            "powersOn": True,
            "screenCondition": "Visible scratches",
            "bodyCondition": "Dents/scratches visible",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "tamperSealsIntact": False,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": True,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "USB-C port intermittent. Device was repackaged when received.",
            "packagingCondition": "repackaged box",
            "labelInconsistency": False,
            "estimatedRepairCost": 4500,
            "estimatedResaleValue": 38000,
            "estimatedPartsValue": 8000,
            "images": ["front.jpg"]
        },
        {
            "returnId": "RET-DEMO-010",
            "label": "GENUINE — Like-New Wearable, Warranty Eligible, Cosmetic Return",
            "category": "Audio & Wearables",
            "manufacturer": "Apple",
            "model": "AirPods Pro 2nd Gen",
            "serialNumber": "H9XQ7MP2K1R4",
            "purchaseDate": d(14),
            "returnDate": d(0),
            "sellerChannel": "Apple Store",
            "claimedPurchasePrice": 24900,
            "invoiceAvailable": True,
            "warrantyClaimed": False,
            "powersOn": True,
            "screenCondition": "Not applicable",
            "bodyCondition": "Like new",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "tamperSealsIntact": True,
            "batteryIssue": False,
            "screenIssue": False,
            "chargingIssue": False,
            "motherboardIssue": False,
            "softwareIssue": False,
            "customerSymptoms": "Returning as a gift — recipient already owns AirPods.",
            "estimatedRepairCost": 0,
            "estimatedResaleValue": 22000,
            "estimatedPartsValue": 0,
            "images": ["front.jpg", "case.jpg"]
        }
    ]
    return {r["returnId"]: r for r in records}


# Pre-load demo returns
_returns_store = _build_demo_returns()


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8 — FLASK API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/device-assessment", methods=["POST"])
def post_device_assessment():
    """Full device assessment (all four sub-assessments combined)."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Expected JSON payload."}), 400
    result, status = _run_full_assessment(data)
    return jsonify(result), status


@app.route("/api/device-assessment/authenticity", methods=["POST"])
def post_authenticity():
    """Standalone authenticity risk check."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Expected JSON payload."}), 400
    return jsonify({"status": "success", "result": _run_authenticity_check(data)}), 200


@app.route("/api/device-assessment/condition", methods=["POST"])
def post_condition_score():
    """Standalone condition and repairability score."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Expected JSON payload."}), 400
    return jsonify({"status": "success", "result": _run_condition_score(data)}), 200


@app.route("/api/device-assessment/warranty", methods=["POST"])
def post_warranty():
    """Standalone warranty entitlement check."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Expected JSON payload."}), 400
    return jsonify({"status": "success", "result": _run_warranty_verification(data)}), 200


@app.route("/api/device-assessment/returns", methods=["GET"])
def get_demo_returns():
    """Returns the 10 labelled synthetic demo return records."""
    return jsonify({
        "status": "success",
        "count": len(_returns_store),
        "returns": list(_returns_store.values())
    }), 200


@app.route("/api/device-assessment/returns/<return_id>", methods=["GET"])
def get_demo_return(return_id):
    """Returns a single demo return record by ID."""
    record = _returns_store.get(return_id)
    if not record:
        return jsonify({"status": "error", "message": f"Return '{return_id}' not found."}), 404
    return jsonify({"status": "success", "return": record}), 200


@app.route("/api/device-assessment/<assessment_id>", methods=["GET"])
def get_assessment(assessment_id):
    """Retrieve a stored assessment by ID."""
    assessment = _assessment_store.get(assessment_id)
    if not assessment:
        return jsonify({"status": "error", "message": f"Assessment '{assessment_id}' not found."}), 404
    return jsonify({"status": "success", "assessment": assessment}), 200


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9 — ORIGINAL PERSON 2 ENDPOINTS (preserved verbatim)
# ═══════════════════════════════════════════════════════════════════════

VALID_CATEGORIES_P2 = [
    "Consumer Electronics", "Smartphones & Tablets",
    "Audio & Wearables", "Home Appliances",
    "Computing & Laptops", "Other"
]
VALID_CONDITIONS_P2 = [
    "New / unopened", "Like new", "Used", "Damaged", "Non-functional"
]
VALID_DEFECT_CATEGORIES_P2 = [
    "No defect", "Battery issue", "Display or screen damage",
    "Charging or connectivity issue", "Hardware failure",
    "Software issue", "Liquid damage", "Other"
]
VALID_WARRANTY_STATUSES_P2 = ["In warranty", "Expired", "Unknown"]


def validate_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.date.fromisoformat(date_str.strip())
    except ValueError:
        return None


def calculate_preliminary_disposition(condition, defect_cat, warranty_status):
    if condition == "New / unopened" and defect_cat == "No defect":
        return {"route": "RESTOCK_AS_NEW", "priority": "LOW", "estimatedRecoveryRatio": 0.95,
                "recommendedAction": "Perform barcode verification and return to primary fulfillment inventory."}
    if condition == "Like new" and defect_cat == "No defect":
        return {"route": "OPEN_BOX_RESALE", "priority": "MEDIUM", "estimatedRecoveryRatio": 0.85,
                "recommendedAction": "Repackage in Grade-A box and list in certified open-box channel."}
    if defect_cat == "Liquid damage":
        return {"route": "PARTS_HARVEST_OR_RECYCLE", "priority": "LOW", "estimatedRecoveryRatio": 0.20,
                "recommendedAction": "Liquid contact detected. Harvest non-impacted subcomponents and route remainder to e-waste recycling."}
    if warranty_status == "In warranty" and condition in ["Damaged", "Non-functional"]:
        return {"route": "WARRANTY_OEM_REPAIR", "priority": "HIGH", "estimatedRecoveryRatio": 0.75,
                "recommendedAction": "Route to authorized manufacturer warranty service center for claim processing."}
    if defect_cat in ["Display or screen damage", "Battery issue", "Charging or connectivity issue"]:
        return {"route": "IN_HOUSE_REFURBISH", "priority": "HIGH", "estimatedRecoveryRatio": 0.60,
                "recommendedAction": "Stage for modular component replacement in refurbishment bay."}
    if condition == "Non-functional":
        return {"route": "PARTS_HARVEST_OR_RECYCLE", "priority": "LOW", "estimatedRecoveryRatio": 0.25,
                "recommendedAction": "Decommission product, harvest undamaged subcomponents, route remainder to e-waste recycling."}
    return {"route": "SECONDARY_MARKET_INSPECTION", "priority": "MEDIUM", "estimatedRecoveryRatio": 0.50,
            "recommendedAction": "Route to grading station for secondary B2B liquidation or outlet resale."}


def handle_assessment_submission(data):
    errors = {}
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400
    product_id = (data.get("productId") or "").strip()
    if not product_id:
        errors["productId"] = "Product identifier or SKU is required."
    category = (data.get("category") or "").strip()
    if not category:
        errors["category"] = "Product category is required."
    elif category not in VALID_CATEGORIES_P2:
        errors["category"] = f"Category must be one of: {', '.join(VALID_CATEGORIES_P2)}."
    condition = (data.get("condition") or "").strip()
    if not condition:
        errors["condition"] = "Product condition is required."
    elif condition not in VALID_CONDITIONS_P2:
        errors["condition"] = f"Condition must be one of: {', '.join(VALID_CONDITIONS_P2)}."
    defect_cat = (data.get("defectCategory") or "").strip()
    if not defect_cat:
        errors["defectCategory"] = "Defect category is required."
    elif defect_cat not in VALID_DEFECT_CATEGORIES_P2:
        errors["defectCategory"] = f"Defect category must be one of: {', '.join(VALID_DEFECT_CATEGORIES_P2)}."
    defect_desc = (data.get("defectDescription") or "").strip()
    if defect_cat == "Other" and not defect_desc:
        errors["defectDescription"] = "Please provide an explanatory description when selecting 'Other' defect."
    if condition in ["Damaged", "Non-functional"]:
        if defect_cat == "No defect":
            errors["defectCategory"] = f"Products marked as '{condition}' must specify a defect category other than 'No defect'."
        if not defect_desc:
            errors["defectDescription"] = f"Defect description is required when product condition is '{condition}'."
    visible_damage = data.get("visibleDamage")
    if visible_damage is None or not isinstance(visible_damage, bool):
        errors["visibleDamage"] = "Visible damage must be explicitly indicated (Yes or No)."
    warranty_status = (data.get("warrantyStatus") or "").strip()
    if not warranty_status:
        errors["warrantyStatus"] = "Warranty status is required."
    elif warranty_status not in VALID_WARRANTY_STATUSES_P2:
        errors["warrantyStatus"] = f"Warranty status must be one of: {', '.join(VALID_WARRANTY_STATUSES_P2)}."
    purchase_date_str = (data.get("purchaseDate") or "").strip()
    purchase_date = validate_date(purchase_date_str)
    today = datetime.date.today()
    if not purchase_date_str:
        errors["purchaseDate"] = "Purchase date is required."
    elif not purchase_date:
        errors["purchaseDate"] = "Purchase date must be a valid date in YYYY-MM-DD format."
    elif purchase_date > today:
        errors["purchaseDate"] = f"Purchase date cannot be in the future (today is {today.isoformat()})."
    warranty_expiry_str = (data.get("warrantyExpiryDate") or "").strip()
    if warranty_expiry_str:
        warranty_expiry = validate_date(warranty_expiry_str)
        if not warranty_expiry:
            errors["warrantyExpiryDate"] = "Warranty expiry date must be a valid date in YYYY-MM-DD format."
        elif purchase_date and warranty_expiry < purchase_date:
            errors["warrantyExpiryDate"] = "Warranty expiry date cannot precede the purchase date."
    if errors:
        return jsonify({"status": "error", "message": "Validation failed on submitted assessment fields.", "errors": errors}), 422
    random_suffix = uuid.uuid4().hex[:6].upper()
    date_prefix = datetime.date.today().strftime("%Y%m%d")
    assessment_id = f"ASM-{date_prefix}-{random_suffix}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    disposition = calculate_preliminary_disposition(condition, defect_cat, warranty_status)
    return jsonify({
        "status": "success",
        "assessmentId": assessment_id,
        "timestamp": timestamp,
        "product": {"productId": product_id, "productName": (data.get("productName") or "").strip(),
                    "category": category, "condition": condition},
        "defect": {"category": defect_cat, "description": defect_desc,
                   "visibleDamage": visible_damage, "hasAttachedImage": bool(data.get("damageImage"))},
        "warranty": {"status": warranty_status, "purchaseDate": purchase_date_str,
                     "warrantyExpiryDate": warranty_expiry_str or None,
                     "proofOfPurchase": (data.get("proofOfPurchase") or "").strip()},
        "preliminaryDisposition": disposition,
        "isMock": False
    }), 201


@app.route("/assessment", methods=["POST"])
@app.route("/api/assessment", methods=["POST"])
def post_assessment():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Expected JSON payload."}), 400
    return handle_assessment_submission(data)


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Product Return & Device Assessment Engine",
        "version": "2.0.0",
        "modules": ["return-assessment", "device-intelligence"],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }), 200


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.route("/", methods=["GET"])
def serve_index():
    # If assessment-wizard.html is requested or index.html exists, serve appropriate UI
    if os.path.exists(os.path.join(app.static_folder, "assessment-wizard.html")):
        return send_from_directory(app.static_folder, "assessment-wizard.html")
    return send_from_directory(app.static_folder, "index.html")


@app.route("/dashboard", methods=["GET"])
def serve_dashboard():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/assessment-wizard", methods=["GET"])
def serve_assessment_wizard():
    return send_from_directory(app.static_folder, "assessment-wizard.html")


@app.route("/device-assessment", methods=["GET"])
def serve_device_assessment_page():
    return send_from_directory(app.static_folder, "device-assessment.html")


@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Product Return & Device Assessment Engine on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
