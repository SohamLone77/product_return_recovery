import uuid
from typing import Dict, Any, List, Optional
from app.models import ReturnRecord, AssessmentRecord, DecisionRecord

def calculate_recovery_decision(
    return_rec: ReturnRecord,
    assessment: Optional[AssessmentRecord],
    custom_costs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Transparent, deterministic recovery decision algorithm comparing expected net recovery across feasible routes:
    Expected Net Recovery = Expected Recovered Value - Route Specific Costs - Applicable Liabilities.
    """
    flags: List[str] = []
    reason_codes: List[str] = []
    alternative_routes: List[Dict[str, Any]] = []

    price = float(return_rec.purchase_price)
    custom_costs = custom_costs or {}

    # Check for missing assessment
    if not assessment:
        flags.append("MISSING_ASSESSMENT")
        reason_codes.append("RC_MANUAL_REVIEW_REQUIRED")
        return {
            "recommended_action": "manual_assessment",
            "expected_recovered_value": 0.0,
            "estimated_costs": 0.0,
            "expected_net_recovery": 0.0,
            "cost_breakdown": {"inspection": 0.0, "processing": 0.0},
            "alternative_routes": [],
            "reason_codes": reason_codes,
            "explanation": "No physical or technical assessment record found for this return. Flagged for manual physical assessment.",
            "manual_review_required": True,
            "flags": flags,
            "capacity_notes": "Awaiting initial intake inspection before bench scheduling.",
        }

    condition = assessment.product_condition
    defect_cat = assessment.defect_category
    warranty_status = assessment.warranty_status
    verified_warranty = assessment.verified_warranty_eligible
    fraud_score = assessment.fraud_risk_score or 0.0
    fraud_flags = assessment.fraud_flags or []

    # Fraud evaluation
    if fraud_score >= 0.7 or len(fraud_flags) > 0:
        flags.append("FRAUD_RISK_SUSPECTED")
        reason_codes.append("RC_HIGH_FRAUD_RISK")

    # Ambiguous damage check
    is_ambiguous = (
        (assessment.visible_damage and condition in {"unopened", "like_new"}) or
        (defect_cat == "other" and not assessment.defect_description) or
        (condition == "defective" and defect_cat == "none")
    )
    if is_ambiguous:
        flags.append("AMBIGUOUS_DAMAGE_REPORT")
        reason_codes.append("RC_AMBIGUOUS_DATA")

    # Define route cost models (inspection, repair, shipping, handling, testing, processing, disposal)
    # Inspection is standard baseline across routes
    base_inspection = custom_costs.get("inspection", 8.0)
    base_handling = custom_costs.get("handling", 5.0)

    # Route 1: Restock (Direct return to shelf)
    restock_feasible = condition in {"unopened", "like_new"} and not assessment.visible_damage and defect_cat == "none"
    restock_val = round(price * 0.95, 2) if condition == "unopened" else round(price * 0.85, 2)
    restock_costs = {
        "inspection": base_inspection,
        "handling": base_handling,
        "repackaging": 5.0 if condition == "like_new" else 0.0,
        "testing": 0.0,
    }
    total_restock_cost = round(sum(restock_costs.values()), 2)
    net_restock = round(restock_val - total_restock_cost, 2)
    alternative_routes.append({
        "route": "restock",
        "feasible": restock_feasible,
        "expected_recovered_value": restock_val if restock_feasible else 0.0,
        "route_costs": total_restock_cost if restock_feasible else 0.0,
        "expected_net_recovery": net_restock if restock_feasible else -total_restock_cost,
        "cost_breakdown": restock_costs if restock_feasible else {},
        "feasibility_note": "Feasible for unopened or like-new inventory without physical defects." if restock_feasible else "Infeasible: Product shows wear, damage, or functional defects.",
    })

    # Route 2: Return to Supplier / Manufacturer
    supplier_feasible = (
        verified_warranty is True or
        (verified_warranty is None and warranty_status == "active" and defect_cat in {"functional", "electrical"})
    )
    supplier_val = round(price * 0.90, 2)
    supplier_costs = {
        "inspection": base_inspection,
        "shipping_and_handling": custom_costs.get("supplier_shipping", 12.0),
        "rma_processing": 6.0,
    }
    total_supplier_cost = round(sum(supplier_costs.values()), 2)
    net_supplier = round(supplier_val - total_supplier_cost, 2)
    alternative_routes.append({
        "route": "return_to_supplier",
        "feasible": supplier_feasible,
        "expected_recovered_value": supplier_val if supplier_feasible else 0.0,
        "route_costs": total_supplier_cost if supplier_feasible else 0.0,
        "expected_net_recovery": net_supplier if supplier_feasible else -total_supplier_cost,
        "cost_breakdown": supplier_costs if supplier_feasible else {},
        "feasibility_note": "Feasible under active supplier warranty with authorized RMA." if supplier_feasible else "Infeasible: Outside supplier warranty window or unverified coverage.",
    })

    # Route 3: Repair & Resell Grade A
    repair_feasible = condition in {"minor_damage", "defective"} and defect_cat in {"functional", "electrical", "cosmetic"}
    repair_cost_est = custom_costs.get("repair", round(price * 0.25 + 15.0, 2))
    repair_val = round(price * 0.80, 2)
    repair_costs = {
        "inspection": base_inspection,
        "repair_parts_labor": repair_cost_est,
        "testing": 10.0,
        "handling": base_handling,
    }
    total_repair_cost = round(sum(repair_costs.values()), 2)
    net_repair = round(repair_val - total_repair_cost, 2)
    alternative_routes.append({
        "route": "repair",
        "feasible": repair_feasible,
        "expected_recovered_value": repair_val if repair_feasible else 0.0,
        "route_costs": total_repair_cost if repair_feasible else 0.0,
        "expected_net_recovery": net_repair if repair_feasible else -total_repair_cost,
        "cost_breakdown": repair_costs if repair_feasible else {},
        "feasibility_note": "Feasible for repairable components where recovery value exceeds technician & part costs." if repair_feasible else "Infeasible: Severe structural damage or no repair required.",
    })

    # Route 4: Refurbish (Cosmetic renewal + functional certification)
    refurb_feasible = condition in {"like_new", "minor_damage"} and defect_cat in {"none", "cosmetic", "missing_parts"}
    refurb_cost_est = custom_costs.get("refurbish", round(price * 0.15 + 10.0, 2))
    refurb_val = round(price * 0.75, 2)
    refurb_costs = {
        "inspection": base_inspection,
        "refurbishment_labor": refurb_cost_est,
        "packaging_and_cleaning": 8.0,
        "handling": base_handling,
    }
    total_refurb_cost = round(sum(refurb_costs.values()), 2)
    net_refurb = round(refurb_val - total_refurb_cost, 2)
    alternative_routes.append({
        "route": "refurbish",
        "feasible": refurb_feasible,
        "expected_recovered_value": refurb_val if refurb_feasible else 0.0,
        "route_costs": total_refurb_cost if refurb_feasible else 0.0,
        "expected_net_recovery": net_refurb if refurb_feasible else -total_refurb_cost,
        "cost_breakdown": refurb_costs if refurb_feasible else {},
        "feasibility_note": "Feasible for minor cosmetic wear or missing packaging requiring recertification." if refurb_feasible else "Infeasible: Excessive damage or unneeded for unopened stock.",
    })

    # Route 5: Resell Secondary Channel (As-Is / Liquidation / B2B Wholesaler)
    resell_sec_feasible = condition in {"like_new", "minor_damage", "defective"}
    resell_sec_val = round(price * 0.45, 2) if condition != "defective" else round(price * 0.25, 2)
    resell_sec_costs = {
        "inspection": base_inspection,
        "listing_and_handling": 6.0,
        "b2b_shipping_allocation": 5.0,
    }
    total_resell_sec_cost = round(sum(resell_sec_costs.values()), 2)
    net_resell_sec = round(resell_sec_val - total_resell_sec_cost, 2)
    alternative_routes.append({
        "route": "resell_secondary",
        "feasible": resell_sec_feasible,
        "expected_recovered_value": resell_sec_val if resell_sec_feasible else 0.0,
        "route_costs": total_resell_sec_cost if resell_sec_feasible else 0.0,
        "expected_net_recovery": net_resell_sec if resell_sec_feasible else -total_resell_sec_cost,
        "cost_breakdown": resell_sec_costs if resell_sec_feasible else {},
        "feasibility_note": "Feasible for rapid disposition via discount or secondary liquidation marketplaces." if resell_sec_feasible else "Infeasible: Unopened goods should be restocked.",
    })

    # Route 6: Harvest Parts
    harvest_feasible = condition in {"minor_damage", "major_damage", "defective"} and return_rec.category in {"Electronics", "Appliances", "Computers"}
    harvest_val = round(price * 0.35, 2)
    harvest_costs = {
        "inspection": base_inspection,
        "disassembly_labor": 12.0,
        "component_testing_and_cataloging": 8.0,
    }
    total_harvest_cost = round(sum(harvest_costs.values()), 2)
    net_harvest = round(harvest_val - total_harvest_cost, 2)
    alternative_routes.append({
        "route": "harvest_parts",
        "feasible": harvest_feasible,
        "expected_recovered_value": harvest_val if harvest_feasible else 0.0,
        "route_costs": total_harvest_cost if harvest_feasible else 0.0,
        "expected_net_recovery": net_harvest if harvest_feasible else -total_harvest_cost,
        "cost_breakdown": harvest_costs if harvest_feasible else {},
        "feasibility_note": "Feasible for complex products containing high-value reusable subcomponents." if harvest_feasible else "Infeasible: Non-modular category or simple assembly.",
    })

    # Route 7: Recycle (Material recovery / e-waste compliance)
    recycle_feasible = condition in {"major_damage", "defective"}
    recycle_val = round(max(price * 0.05, 3.0), 2)
    recycle_costs = {
        "inspection": base_inspection,
        "sorting_and_transport": 5.0,
    }
    total_recycle_cost = round(sum(recycle_costs.values()), 2)
    net_recycle = round(recycle_val - total_recycle_cost, 2)
    alternative_routes.append({
        "route": "recycle",
        "feasible": recycle_feasible,
        "expected_recovered_value": recycle_val if recycle_feasible else 0.0,
        "route_costs": total_recycle_cost if recycle_feasible else 0.0,
        "expected_net_recovery": net_recycle if recycle_feasible else -total_recycle_cost,
        "cost_breakdown": recycle_costs if recycle_feasible else {},
        "feasibility_note": "Feasible for non-repairable units with recyclable scrap metals or materials." if recycle_feasible else "Infeasible: Product has higher-value recovery potential.",
    })

    # Route 8: Dispose (Safe ecological disposal / scrap)
    dispose_val = 0.0
    dispose_costs = {
        "handling": base_handling,
        "disposal_fee": 6.0,
    }
    total_dispose_cost = round(sum(dispose_costs.values()), 2)
    net_dispose = round(dispose_val - total_dispose_cost, 2)
    alternative_routes.append({
        "route": "dispose",
        "feasible": True,
        "expected_recovered_value": dispose_val,
        "route_costs": total_dispose_cost,
        "expected_net_recovery": net_dispose,
        "cost_breakdown": dispose_costs,
        "feasibility_note": "Feasible as last resort when repair, parts harvest, and recycling cannot yield positive return.",
    })

    # Route 9: Manual Assessment
    alternative_routes.append({
        "route": "manual_assessment",
        "feasible": True,
        "expected_recovered_value": 0.0,
        "route_costs": base_inspection,
        "expected_net_recovery": -base_inspection,
        "cost_breakdown": {"inspection": base_inspection},
        "feasibility_note": "Route for ambiguous defect conditions, high fraud alerts, or special customer escalations.",
    })

    # Priority Decision Logic:
    # 1. If high fraud or ambiguous data -> manual_assessment
    if is_ambiguous or fraud_score >= 0.7:
        selected_route = "manual_assessment"
        manual_review = True
        if fraud_score >= 0.7:
            reason_codes.append("RC_HIGH_FRAUD_FLAG")
            explanation = f"Flagged for manual physical assessment due to elevated fraud risk score ({fraud_score:.2f}) and active risk indicators."
        else:
            reason_codes.append("RC_AMBIGUOUS_ASSESSMENT")
            explanation = "Flagged for manual physical assessment due to conflicting condition and defect indicators in the assessment report."
        best_rec = next(r for r in alternative_routes if r["route"] == "manual_assessment")
    else:
        # Filter feasible candidate routes excluding manual_assessment and dispose unless no other options
        candidates = [r for r in alternative_routes if r["feasible"] and r["route"] not in {"manual_assessment", "dispose"}]
        if not candidates:
            candidates = [r for r in alternative_routes if r["feasible"]]

        # Sort by highest expected net recovery
        candidates.sort(key=lambda x: x["expected_net_recovery"], reverse=True)
        best_rec = candidates[0]
        selected_route = best_rec["route"]
        manual_review = False

        if selected_route == "restock":
            reason_codes.append("RC_RESTOCK_MAX_MARGIN")
            explanation = f"Product in {condition} condition with zero functional defects. Direct restock delivers maximum net recovery of ${best_rec['expected_net_recovery']:.2f}."
        elif selected_route == "return_to_supplier":
            reason_codes.append("RC_SUPPLIER_WARRANTY_RECOVERY")
            explanation = f"Covered under warranty with defect in {defect_cat}. RMA return to supplier provides highest net recovery of ${best_rec['expected_net_recovery']:.2f} with minimal internal costs."
        elif selected_route == "repair":
            reason_codes.append("RC_ECONOMIC_REPAIR_OPTIMAL")
            explanation = f"Defect category '{defect_cat}' is economically viable to repair. Net recovery of ${best_rec['expected_net_recovery']:.2f} outperforms secondary liquidation."
        elif selected_route == "refurbish":
            reason_codes.append("RC_REFURBISH_CERTIFICATION")
            explanation = f"Refurbishment and packaging renewal recovers ${best_rec['expected_net_recovery']:.2f} net resale value."
        elif selected_route == "resell_secondary":
            reason_codes.append("RC_SECONDARY_LIQUIDATION")
            explanation = f"Direct secondary channel disposition optimal; yields ${best_rec['expected_net_recovery']:.2f} without repair overhead."
        elif selected_route == "harvest_parts":
            reason_codes.append("RC_PARTS_HARVEST_MAX")
            explanation = f"Device repair uneconomical; harvesting modular components captures ${best_rec['expected_net_recovery']:.2f} value."
        elif selected_route == "recycle":
            reason_codes.append("RC_ECO_RECYCLE")
            explanation = f"Extensive damage prevents resale; recycling satisfies compliance and recovers ${best_rec['expected_net_recovery']:.2f} scrap credit."
        else:
            reason_codes.append("RC_DISPOSE_MIN_LOSS")
            explanation = f"Negative expected net recovery across all refurbishment options; safe disposal selected to minimize holding loss (${best_rec['expected_net_recovery']:.2f})."

    capacity_note = "Single-device deterministic baseline evaluation. Repair bench capacity and technician batch scheduling ready for integration."

    return {
        "recommended_action": selected_route,
        "expected_recovered_value": best_rec["expected_recovered_value"],
        "estimated_costs": best_rec["route_costs"],
        "expected_net_recovery": best_rec["expected_net_recovery"],
        "cost_breakdown": best_rec["cost_breakdown"],
        "alternative_routes": alternative_routes,
        "reason_codes": reason_codes,
        "explanation": explanation,
        "manual_review_required": manual_review,
        "flags": flags,
        "capacity_notes": capacity_note,
    }
