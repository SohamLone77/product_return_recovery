from typing import Dict, Any, List, Optional
from app.models import ReturnRecord, AssessmentRecord

def calculate_recovery_decision(
    return_rec: ReturnRecord,
    assessment: Optional[AssessmentRecord],
    custom_costs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Reverse Logistics Economic Decision Engine.
    Evaluates all 7 disposition options (Restock, Repair, Refurbish, Return to Supplier,
    Harvest Parts, Recycle, Dispose) using expected net recovery:
      Expected Net Recovery = Expected Proceeds - Expected Route Costs

    Implements explicit probabilistic repair modeling:
      Expected Net Repair Recovery = p_success * V_success + (1 - p_success) * C_failure
                                     - C_repair - C_test - C_logistics - C_liability
    and computes the key optimization metric:
      Repair Incremental Benefit = Expected Net Repair Recovery - Best Feasible Non-Repair Net Recovery
    """
    custom_costs = custom_costs or {}
    price = float(return_rec.purchase_price)

    flags: List[str] = []
    reason_codes: List[str] = []
    manual_review_reasons: List[str] = []
    assumptions: List[str] = []
    alternative_routes: List[Dict[str, Any]] = []

    # 1. Check for missing assessment
    if not assessment:
        flags.append("MISSING_ASSESSMENT")
        reason_codes.append("RC_MANUAL_REVIEW_REQUIRED")
        manual_review_reasons.append("No technical intake inspection record found.")
        return {
            "recommended_action": "manual_assessment",
            "recommended_route": "manual_assessment",
            "expected_recovered_value": 0.0,
            "estimated_costs": 0.0,
            "expected_net_recovery": 0.0,
            "cost_breakdown": {"inspection": 0.0},
            "alternative_routes": [],
            "reason_codes": reason_codes,
            "explanation": "No physical assessment record found. Flagged for manual physical assessment.",
            "manual_review_required": True,
            "manual_review_reasons": manual_review_reasons,
            "flags": flags,
            "best_non_repair_route": "none",
            "best_non_repair_net_recovery": 0.0,
            "repair_incremental_benefit": 0.0,
            "incremental_value_vs_next_best_route": 0.0,
            "confidence_score": 0.0,
            "assumptions": ["Assessment missing; zero proceeds assumed until intake."],
            "operational_reasons": "Requires technician physical triage before disposition scheduling.",
            "capacity_notes": "Awaiting initial intake inspection before bench scheduling.",
        }

    # Extract assessment attributes
    condition = assessment.product_condition
    defect_cat = assessment.defect_category
    visible_dmg = assessment.visible_damage
    warranty_status = assessment.warranty_status
    verified_warranty = assessment.verified_warranty_eligible
    fraud_score = float(assessment.fraud_risk_score or 0.0)
    fraud_flags = list(assessment.fraud_flags or [])
    safety_hazard = bool(assessment.safety_hazard)
    auth_risk = float(assessment.authenticity_risk or 0.0)

    # 2. Policy & Safety Guardrails
    if safety_hazard:
        flags.append("SAFETY_HAZARD_LITHIUM_BATTERY")
        reason_codes.append("RC_SAFETY_HAZARD_BLOCK")
        manual_review_reasons.append("Safety hazard detected (e.g. swollen lithium battery, thermal damage). Standard automated processing blocked.")

    if auth_risk >= 0.70 or fraud_score >= 0.70 or any(f in {"COUNTERFEIT_SUSPECTED", "SERIAL_MISMATCH", "REPEAT_CLAIMANT"} for f in fraud_flags):
        flags.append("HIGH_AUTHENTICITY_OR_FRAUD_RISK")
        flags.append("FRAUD_RISK_SUSPECTED")
        reason_codes.append("RC_HIGH_FRAUD_RISK")
        manual_review_reasons.append(f"Elevated fraud/authenticity risk (score: {max(auth_risk, fraud_score):.2f}). Potential counterfeit or serial mismatch.")

    # Ambiguous data check
    is_ambiguous = (
        (visible_dmg and condition in {"unopened", "like_new"}) or
        (condition == "defective" and defect_cat == "none") or
        (defect_cat == "other" and not assessment.defect_description)
    )
    if is_ambiguous:
        flags.append("AMBIGUOUS_DATA_REPORT")
        reason_codes.append("RC_AMBIGUOUS_ASSESSMENT")
        manual_review_reasons.append("Conflicting assessment data between condition grade and reported defect.")

    # 3. Base Operational Costs
    base_inspection = custom_costs.get("inspection", 8.0)
    base_handling = custom_costs.get("handling", 5.0)

    # =========================================================================
    # ROUTE A: Restock as New
    # =========================================================================
    restock_feasible = (
        condition in {"unopened", "like_new"} and
        not visible_dmg and
        defect_cat == "none" and
        not safety_hazard and
        auth_risk < 0.50
    )
    restock_proceeds = round(price * 0.95, 2) if condition == "unopened" else round(price * 0.85, 2)
    restock_costs_dict = {
        "inspection": base_inspection,
        "handling": base_handling,
        "repackaging": 5.0 if condition == "like_new" else 0.0,
    }
    total_restock_cost = round(sum(restock_costs_dict.values()), 2)
    net_restock = round(restock_proceeds - total_restock_cost, 2)
    alternative_routes.append({
        "route": "restock",
        "feasible": restock_feasible,
        "expected_recovered_value": restock_proceeds if restock_feasible else 0.0,
        "route_costs": total_restock_cost if restock_feasible else 0.0,
        "expected_net_recovery": net_restock if restock_feasible else -total_restock_cost,
        "cost_breakdown": restock_costs_dict if restock_feasible else {},
        "feasibility_note": "Feasible: Unopened/like-new unit with zero defects or damage." if restock_feasible else "Infeasible: Unit has physical damage, defect, or safety/authenticity flags.",
    })

    # =========================================================================
    # ROUTE B: Return to Supplier / Warranty Claim
    # =========================================================================
    # Models supplier reimbursement credit, claim rejection probability, and logistics
    supplier_eligible = (
        verified_warranty is True or
        (verified_warranty is None and warranty_status == "active" and defect_cat in {"functional", "electrical"})
    )
    supplier_feasible = supplier_eligible and not safety_hazard and auth_risk < 0.50

    p_claim_success = 0.98 if verified_warranty is True else 0.70
    supplier_credit_val = round(price * 0.90, 2)
    supplier_shipping = custom_costs.get("supplier_shipping", 12.0)
    rma_fee = 6.0
    supplier_expected_proceeds = round(p_claim_success * supplier_credit_val, 2)
    rejection_risk_cost = round((1.0 - p_claim_success) * (supplier_shipping + 15.0), 2)
    supplier_costs_dict = {
        "inspection": base_inspection,
        "supplier_shipping": supplier_shipping,
        "rma_processing": rma_fee,
        "claim_rejection_risk": rejection_risk_cost,
    }
    total_supplier_cost = round(sum(supplier_costs_dict.values()), 2)
    net_supplier = round(supplier_expected_proceeds - total_supplier_cost, 2)
    if not verified_warranty and warranty_status == "active":
        assumptions.append("Supplier warranty is user-claimed but unverified; 70% claim acceptance modeled.")
    alternative_routes.append({
        "route": "return_to_supplier",
        "feasible": supplier_feasible,
        "expected_recovered_value": supplier_expected_proceeds if supplier_feasible else 0.0,
        "route_costs": total_supplier_cost if supplier_feasible else 0.0,
        "expected_net_recovery": net_supplier if supplier_feasible else -total_supplier_cost,
        "cost_breakdown": supplier_costs_dict if supplier_feasible else {},
        "feasibility_note": "Feasible: Verified/active manufacturer warranty with authorized RMA." if supplier_feasible else "Infeasible: Expired/unsupported warranty or policy flags.",
    })

    # =========================================================================
    # ROUTE C: Refurbish (Cosmetic Renew + Repackaging)
    # =========================================================================
    refurb_feasible = (
        condition in {"like_new", "minor_damage"} and
        defect_cat in {"none", "cosmetic", "missing_parts"} and
        not safety_hazard and
        auth_risk < 0.50
    )
    refurb_proceeds = round(price * 0.75, 2)
    refurb_labor = custom_costs.get("refurbish", round(price * 0.12 + 10.0, 2))
    refurb_costs_dict = {
        "inspection": base_inspection,
        "cosmetic_renew_labor": refurb_labor,
        "packaging_and_cleaning": 8.0,
        "handling": base_handling,
        "warranty_reserve": 10.0,
    }
    total_refurb_cost = round(sum(refurb_costs_dict.values()), 2)
    net_refurb = round(refurb_proceeds - total_refurb_cost, 2)
    alternative_routes.append({
        "route": "refurbish",
        "feasible": refurb_feasible,
        "expected_recovered_value": refurb_proceeds if refurb_feasible else 0.0,
        "route_costs": total_refurb_cost if refurb_feasible else 0.0,
        "expected_net_recovery": net_refurb if refurb_feasible else -total_refurb_cost,
        "cost_breakdown": refurb_costs_dict if refurb_feasible else {},
        "feasibility_note": "Feasible: Minor cosmetic wear or packaging renewal without internal electrical rework." if refurb_feasible else "Infeasible: Excessive damage or unopened inventory.",
    })

    # =========================================================================
    # ROUTE D: Harvest for Parts
    # =========================================================================
    harvest_feasible = (
        condition in {"minor_damage", "major_damage", "defective"} and
        return_rec.category in {"Electronics", "Appliances", "Computers", "Accessories"} and
        auth_risk < 0.60
    )
    harvest_val = assessment.parts_recovery_value if assessment.parts_recovery_value is not None else round(price * 0.35, 2)
    harvest_costs_dict = {
        "inspection": base_inspection,
        "disassembly_labor": 14.0,
        "component_testing": 8.0,
        "handling": base_handling,
    }
    total_harvest_cost = round(sum(harvest_costs_dict.values()), 2)
    net_harvest = round(harvest_val - total_harvest_cost, 2)
    alternative_routes.append({
        "route": "harvest_parts",
        "feasible": harvest_feasible,
        "expected_recovered_value": harvest_val if harvest_feasible else 0.0,
        "route_costs": total_harvest_cost if harvest_feasible else 0.0,
        "expected_net_recovery": net_harvest if harvest_feasible else -total_harvest_cost,
        "cost_breakdown": harvest_costs_dict if harvest_feasible else {},
        "feasibility_note": "Feasible: High-value reusable modular components (displays, boards, memory)." if harvest_feasible else "Infeasible: Non-modular or counterfeit unit.",
    })

    # =========================================================================
    # ROUTE E: Resell Secondary Channel (As-Is Wholesale / Liquidation)
    # =========================================================================
    resell_sec_feasible = condition in {"like_new", "minor_damage", "defective"} and not safety_hazard and auth_risk < 0.50
    resell_sec_proceeds = round(price * 0.45, 2) if condition != "defective" else round(price * 0.22, 2)
    resell_sec_costs_dict = {
        "inspection": base_inspection,
        "handling_and_listing": 6.0,
        "b2b_shipping_allocation": 5.0,
    }
    total_resell_sec_cost = round(sum(resell_sec_costs_dict.values()), 2)
    net_resell_sec = round(resell_sec_proceeds - total_resell_sec_cost, 2)
    alternative_routes.append({
        "route": "resell_secondary",
        "feasible": resell_sec_feasible,
        "expected_recovered_value": resell_sec_proceeds if resell_sec_feasible else 0.0,
        "route_costs": total_resell_sec_cost if resell_sec_feasible else 0.0,
        "expected_net_recovery": net_resell_sec if resell_sec_feasible else -total_resell_sec_cost,
        "cost_breakdown": resell_sec_costs_dict if resell_sec_feasible else {},
        "feasibility_note": "Feasible: Immediate as-is secondary liquidation." if resell_sec_feasible else "Infeasible: Unopened goods should restock; hazardous items prohibited.",
    })

    # =========================================================================
    # ROUTE F: Recycle (Material Recovery)
    # =========================================================================
    recycle_feasible = condition in {"minor_damage", "major_damage", "defective"}
    recycle_val = round(max(price * 0.04, 4.0), 2)
    recycle_costs_dict = {
        "inspection": base_inspection,
        "sorting_and_transport": 5.0,
        "compliance_fee": 3.0,
    }
    total_recycle_cost = round(sum(recycle_costs_dict.values()), 2)
    net_recycle = round(recycle_val - total_recycle_cost, 2)
    alternative_routes.append({
        "route": "recycle",
        "feasible": recycle_feasible,
        "expected_recovered_value": recycle_val if recycle_feasible else 0.0,
        "route_costs": total_recycle_cost if recycle_feasible else 0.0,
        "expected_net_recovery": net_recycle if recycle_feasible else -total_recycle_cost,
        "cost_breakdown": recycle_costs_dict if recycle_feasible else {},
        "feasibility_note": "Feasible: Material scrap recovery for damaged non-resale units." if recycle_feasible else "Infeasible: Unit has higher value recovery paths.",
    })

    # =========================================================================
    # ROUTE G: Scrap or Dispose
    # =========================================================================
    dispose_proceeds = 0.0
    dispose_costs_dict = {
        "handling": base_handling,
        "disposal_fee": 8.0 if not safety_hazard else 25.0,  # hazardous battery disposal costs more
    }
    total_dispose_cost = round(sum(dispose_costs_dict.values()), 2)
    net_dispose = round(dispose_proceeds - total_dispose_cost, 2)
    alternative_routes.append({
        "route": "dispose",
        "feasible": True,
        "expected_recovered_value": dispose_proceeds,
        "route_costs": total_dispose_cost,
        "expected_net_recovery": net_dispose,
        "cost_breakdown": dispose_costs_dict,
        "feasibility_note": "Feasible: Safe environmental disposal when other routes yield negative net recovery.",
    })

    # =========================================================================
    # ROUTE H: Repair (Explicit Probabilistic Reverse Logistics Model)
    # Expected Net Repair Recovery = p_success * V_success + (1 - p_success) * C_failure
    #                               - C_repair - C_test - C_logistics - C_liability
    # =========================================================================
    repair_feasible = (
        condition in {"minor_damage", "defective"} and
        defect_cat in {"functional", "electrical", "cosmetic", "missing_parts"} and
        not safety_hazard and
        auth_risk < 0.50
    )

    # 1. Probability of success
    if assessment.repair_probability is not None:
        p_success = float(assessment.repair_probability)
    else:
        # Default heuristic based on defect and condition
        p_success = 0.85 if defect_cat != "electrical" else 0.65
        if condition == "defective":
            p_success -= 0.15
        p_success = max(0.05, min(0.99, p_success))

    # 2. Resale value after successful repair V_success
    if assessment.potential_resale_value is not None:
        v_success = float(assessment.potential_resale_value)
    else:
        v_success = round(price * 0.80, 2)

    # 3. Fallback route if repair fails C_failure
    # If repair fails, fall back to parts harvest if feasible, otherwise recycling
    if harvest_feasible and net_harvest > 0:
        c_failure = net_harvest
    else:
        c_failure = max(0.0, net_recycle)

    # 4. Route costs
    if assessment.estimated_repair_cost is not None:
        c_repair = float(assessment.estimated_repair_cost)
    else:
        c_repair = custom_costs.get("repair", round(price * 0.22 + 15.0, 2))

    c_test = 12.0
    c_logistics = base_handling + 5.0
    c_liability = round(v_success * 0.04, 2)  # post-repair return/warranty reserve

    total_repair_costs = round(c_repair + c_test + c_logistics + c_liability, 2)
    expected_repair_proceeds = round(p_success * v_success + (1.0 - p_success) * c_failure, 2)
    net_repair = round(expected_repair_proceeds - total_repair_costs, 2)

    repair_costs_dict = {
        "inspection": base_inspection,
        "repair_parts_labor": c_repair,
        "diagnostic_testing": c_test,
        "handling_and_logistics": c_logistics,
        "post_repair_warranty_liability": c_liability,
    }

    assumptions.append(f"Repair modeled with p_success={p_success:.2f}, V_success=${v_success:.2f}, fallback=${c_failure:.2f}.")

    alternative_routes.append({
        "route": "repair",
        "feasible": repair_feasible,
        "expected_recovered_value": expected_repair_proceeds if repair_feasible else 0.0,
        "route_costs": total_repair_costs if repair_feasible else 0.0,
        "expected_net_recovery": net_repair if repair_feasible else -total_repair_costs,
        "cost_breakdown": repair_costs_dict if repair_feasible else {},
        "feasibility_note": f"Feasible: Technician bench repairable with estimated success probability {p_success*100:.0f}%." if repair_feasible else "Infeasible: Severe structural damage, safety hazard, or non-repairable defect.",
    })

    # =========================================================================
    # IDENTIFY BEST NON-REPAIR ROUTE & REPAIR INCREMENTAL BENEFIT
    # =========================================================================
    non_repair_candidates = [
        r for r in alternative_routes
        if r["route"] != "repair" and r["feasible"]
    ]
    if non_repair_candidates:
        non_repair_candidates.sort(key=lambda x: x["expected_net_recovery"], reverse=True)
        best_non_repair = non_repair_candidates[0]
        best_non_repair_route = best_non_repair["route"]
        best_non_repair_net = float(best_non_repair["expected_net_recovery"])
    else:
        best_non_repair_route = "dispose"
        best_non_repair_net = float(net_dispose)

    # Repair Incremental Benefit = Net Repair - Best Non-Repair Net
    if repair_feasible:
        repair_incremental_benefit = round(net_repair - best_non_repair_net, 2)
    else:
        repair_incremental_benefit = -999.0

    # =========================================================================
    # ESCALATION OR TOP DISPOSITION SELECTION
    # =========================================================================
    # If policy guardrails trigger manual review, route to manual_assessment
    if manual_review_reasons:
        selected_route = "manual_assessment"
        manual_review_required = True
        reason_codes.append("RC_MANUAL_REVIEW_REQUIRED")
        explanation = f"Escalated for manual review: {'; '.join(manual_review_reasons)}"
        best_rec = {
            "route": "manual_assessment",
            "feasible": True,
            "expected_recovered_value": 0.0,
            "route_costs": base_inspection,
            "expected_net_recovery": -base_inspection,
            "cost_breakdown": {"inspection": base_inspection},
            "feasibility_note": "Manual review required by policy guardrails.",
        }
        incremental_vs_next = 0.0
    else:
        # Evaluate all feasible candidates
        all_feasible = [r for r in alternative_routes if r["feasible"]]
        all_feasible.sort(key=lambda x: x["expected_net_recovery"], reverse=True)

        best_rec = all_feasible[0]
        selected_route = best_rec["route"]
        manual_review_required = False

        # Incremental value vs next best route
        if len(all_feasible) > 1:
            next_best = all_feasible[1]
            incremental_vs_next = round(best_rec["expected_net_recovery"] - next_best["expected_net_recovery"], 2)
        else:
            incremental_vs_next = 0.0

        if selected_route == "restock":
            reason_codes.append("RC_RESTOCK_MAX_MARGIN")
            explanation = f"Product in pristine condition ({condition}). Restock captures ${best_rec['expected_net_recovery']:.2f} net recovery without rework."
        elif selected_route == "return_to_supplier":
            reason_codes.append("RC_SUPPLIER_WARRANTY_RECOVERY")
            explanation = f"Covered under warranty. Supplier credit delivers ${best_rec['expected_net_recovery']:.2f} net recovery, outperforming internal rework."
        elif selected_route == "repair":
            reason_codes.append("RC_ECONOMIC_REPAIR_OPTIMAL")
            explanation = f"Repair is economically optimal with positive incremental benefit of +${repair_incremental_benefit:.2f} over next-best route ({best_non_repair_route})."
        elif selected_route == "refurbish":
            reason_codes.append("RC_REFURBISH_CERTIFICATION")
            explanation = f"Cosmetic refurbishment renewal yields ${best_rec['expected_net_recovery']:.2f} net resale value, beating component harvesting."
        elif selected_route == "harvest_parts":
            reason_codes.append("RC_PARTS_HARVEST_MAX")
            explanation = f"Modular component extraction captures ${best_rec['expected_net_recovery']:.2f} reusable parts value, outperforming scrap recycling."
        elif selected_route == "resell_secondary":
            reason_codes.append("RC_SECONDARY_LIQUIDATION")
            explanation = f"Secondary liquidation captures ${best_rec['expected_net_recovery']:.2f} immediate liquidity without technician labor."
        elif selected_route == "recycle":
            reason_codes.append("RC_ECO_RECYCLE")
            explanation = f"Heavy damage precludes resale; material recycling recovers ${best_rec['expected_net_recovery']:.2f} scrap credit."
        else:
            reason_codes.append("RC_DISPOSE_MIN_LOSS")
            explanation = f"All active recovery avenues are negative; safe disposal chosen to minimize loss (-${abs(best_rec['expected_net_recovery']):.2f})."

    confidence_score = 0.95 if not manual_review_required else 0.40
    operational_reasons = (
        f"Route '{selected_route}' validated against condition '{condition}', defect '{defect_cat}', "
        f"and warranty status '{warranty_status}'. Incremental benefit vs best alternative is ${incremental_vs_next:.2f}."
    )

    capacity_notes = (
        f"Repair incremental benefit is ${repair_incremental_benefit:.2f} relative to '{best_non_repair_route}' (${best_non_repair_net:.2f}). "
        "Final execution subject to batch repair bench capacity limits."
    )

    return {
        "recommended_action": selected_route,
        "recommended_route": selected_route,
        "expected_recovered_value": best_rec["expected_recovered_value"],
        "estimated_costs": best_rec["route_costs"],
        "expected_net_recovery": best_rec["expected_net_recovery"],
        "cost_breakdown": best_rec["cost_breakdown"],
        "alternative_routes": alternative_routes,
        "reason_codes": reason_codes,
        "explanation": explanation,
        "manual_review_required": manual_review_required,
        "manual_review_reasons": manual_review_reasons,
        "flags": flags,
        "capacity_notes": capacity_notes,
        "best_non_repair_route": best_non_repair_route,
        "best_non_repair_net_recovery": best_non_repair_net,
        "repair_incremental_benefit": repair_incremental_benefit,
        "incremental_value_vs_next_best_route": incremental_vs_next,
        "confidence_score": confidence_score,
        "assumptions": assumptions,
        "operational_reasons": operational_reasons,
    }
