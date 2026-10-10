import itertools
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import ReturnRecord, AssessmentRecord, DecisionRecord, OptimizationRunRecord
from app.decision_engine import calculate_recovery_decision

def run_batch_optimization(
    db: Session,
    return_ids: Optional[List[str]] = None,
    repair_capacity_slots: int = 4,
    max_repair_hours: Optional[float] = None,
    custom_costs: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Reverse Logistics Batch Capacity Optimizer.
    Maximizes aggregate expected net recovery over N devices subject to:
      - Total selected repairs <= repair_capacity_slots
      - Total repair hours <= max_repair_hours (if configured)
      - Each device assigned exactly one feasible disposition
      - Manual review / safety / fraud guardrails respected

    Key Optimization Engine Mechanism:
      Incremental Repair Benefit_i = Net Repair Recovery_i - Best Feasible Non-Repair Recovery_i
      Only candidates with positive incremental benefit (> 0) are considered.
      If fewer than capacity candidates have positive incremental benefit, remaining slots are left unused.
    """
    # 1. Fetch returns
    if return_ids:
        returns = db.query(ReturnRecord).filter(ReturnRecord.id.in_(return_ids)).all()
    else:
        returns = db.query(ReturnRecord).order_by(ReturnRecord.created_at.asc()).all()

    if not returns:
        return {
            "run_id": f"run_{uuid.uuid4().hex[:12]}",
            "total_devices_evaluated": 0,
            "repair_capacity_slots": repair_capacity_slots,
            "repair_slots_used": 0,
            "capacity_utilization_pct": 0.0,
            "optimized_total_net_recovery": 0.0,
            "baseline_unconstrained_net_recovery": 0.0,
            "baseline_fifo_net_recovery": 0.0,
            "baseline_cheapest_repair_net_recovery": 0.0,
            "dollar_uplift_vs_fifo": 0.0,
            "pct_uplift_vs_fifo": 0.0,
            "dollar_uplift_vs_cheapest": 0.0,
            "pct_uplift_vs_cheapest": 0.0,
            "allocations": [],
            "batch_explanation": "No devices available to evaluate.",
            "comparison_summary": {},
        }

    # 2. Evaluate individual device economics
    device_data = []
    for ret in returns:
        latest_assessment = (
            db.query(AssessmentRecord)
            .filter(AssessmentRecord.return_id == ret.id)
            .order_by(AssessmentRecord.created_at.desc())
            .first()
        )
        dec = calculate_recovery_decision(ret, latest_assessment, custom_costs)

        # Find repair route info
        repair_route = next((r for r in dec["alternative_routes"] if r["route"] == "repair"), None)
        repair_feasible = bool(repair_route and repair_route["feasible"] and not dec["manual_review_required"])
        repair_net = float(repair_route["expected_net_recovery"]) if repair_route else -999.0
        repair_cost = float(repair_route["route_costs"]) if repair_route else 999.0
        repair_proceeds = float(repair_route["expected_recovered_value"]) if repair_route else 0.0

        # Hours estimate
        repair_hours = 2.0
        if latest_assessment and latest_assessment.estimated_repair_hours is not None:
            repair_hours = float(latest_assessment.estimated_repair_hours)

        # Best non-repair route
        best_non_repair_route = dec["best_non_repair_route"]
        best_non_repair_net = float(dec["best_non_repair_net_recovery"])
        best_non_repair_item = next((r for r in dec["alternative_routes"] if r["route"] == best_non_repair_route), None)
        best_non_repair_proceeds = float(best_non_repair_item["expected_recovered_value"]) if best_non_repair_item else 0.0
        best_non_repair_cost = float(best_non_repair_item["route_costs"]) if best_non_repair_item else 0.0

        # Incremental benefit of repair
        if repair_feasible:
            incremental_benefit = round(repair_net - best_non_repair_net, 2)
        else:
            incremental_benefit = -999.0

        device_data.append({
            "return_id": ret.id,
            "product_name": ret.product_name,
            "category": ret.category,
            "decision": dec,
            "repair_feasible": repair_feasible,
            "repair_net": repair_net,
            "repair_cost": repair_cost,
            "repair_proceeds": repair_proceeds,
            "repair_hours": repair_hours,
            "best_non_repair_route": best_non_repair_route,
            "best_non_repair_net": best_non_repair_net,
            "best_non_repair_proceeds": best_non_repair_proceeds,
            "best_non_repair_cost": best_non_repair_cost,
            "incremental_benefit": incremental_benefit,
            "manual_review_required": dec["manual_review_required"],
            "manual_review_reasons": dec["manual_review_reasons"],
        })

    # =========================================================================
    # 3. EXACT COMBINATORIAL OPTIMIZATION
    # =========================================================================
    # Candidate pool: Devices where repair is feasible, not blocked by review, and incremental benefit > 0
    repair_candidates = [
        d for d in device_data
        if d["repair_feasible"] and d["incremental_benefit"] > 0.0 and not d["manual_review_required"]
    ]

    best_repair_subset = []
    best_total_recovery = -float("inf")

    # Evaluate all subsets of repair candidates of size 0 to min(capacity, len(candidates))
    max_k = min(repair_capacity_slots, len(repair_candidates))
    for k in range(max_k + 1):
        for subset in itertools.combinations(repair_candidates, k):
            # Check hours budget if configured
            if max_repair_hours is not None:
                total_hours = sum(d["repair_hours"] for d in subset)
                if total_hours > max_repair_hours:
                    continue

            selected_ids = {d["return_id"] for d in subset}
            current_total = 0.0

            for d in device_data:
                if d["manual_review_required"]:
                    # Manual review case keeps its manual review outcome
                    current_total += d["decision"]["expected_net_recovery"]
                elif d["return_id"] in selected_ids:
                    current_total += d["repair_net"]
                else:
                    current_total += d["best_non_repair_net"]

            if current_total > best_total_recovery:
                best_total_recovery = current_total
                best_repair_subset = list(subset)

    selected_repair_ids = {d["return_id"] for d in best_repair_subset}
    optimized_total_recovery = round(best_total_recovery, 2)
    slots_used = len(best_repair_subset)
    capacity_utilization = round((slots_used / repair_capacity_slots) * 100.0, 1) if repair_capacity_slots > 0 else 0.0

    # Build allocations
    allocations = []
    for d in device_data:
        rid = d["return_id"]
        if d["manual_review_required"]:
            assigned = "manual_assessment"
            proceeds = d["decision"]["expected_recovered_value"]
            cost = d["decision"]["estimated_costs"]
            net = d["decision"]["expected_net_recovery"]
            rationale = f"Escalated for human review: {'; '.join(d['manual_review_reasons'])}. Automated repair prohibited."
            was_repair = False
        elif rid in selected_repair_ids:
            assigned = "repair"
            proceeds = d["repair_proceeds"]
            cost = d["repair_cost"]
            net = d["repair_net"]
            rationale = (
                f"Selected for repair bench slot. Delivers +${d['incremental_benefit']:.2f} incremental net recovery "
                f"over fallback '{d['best_non_repair_route']}'."
            )
            was_repair = True
        else:
            assigned = d["best_non_repair_route"]
            proceeds = d["best_non_repair_proceeds"]
            cost = d["best_non_repair_cost"]
            net = d["best_non_repair_net"]
            if d["incremental_benefit"] <= 0.0:
                rationale = f"Routed to '{assigned}' because repair has negative or non-positive incremental benefit (${d['incremental_benefit']:.2f})."
            else:
                rationale = (
                    f"Routed to '{assigned}' due to repair capacity constraint ({slots_used}/{repair_capacity_slots} slots full). "
                    f"Higher-yielding devices took precedence."
                )
            was_repair = False

        allocations.append({
            "return_id": rid,
            "product_name": d["product_name"],
            "category": d["category"],
            "assigned_route": assigned,
            "expected_proceeds": round(proceeds, 2),
            "expected_cost": round(cost, 2),
            "expected_net_recovery": round(net, 2),
            "was_repair_selected": was_repair,
            "repair_feasible": d["repair_feasible"],
            "repair_incremental_benefit": d["incremental_benefit"] if d["repair_feasible"] else 0.0,
            "best_non_repair_route": d["best_non_repair_route"],
            "best_non_repair_net_recovery": round(d["best_non_repair_net"], 2),
            "repair_hours": d["repair_hours"],
            "manual_review_required": d["manual_review_required"],
            "manual_review_reasons": d["manual_review_reasons"],
            "allocation_rationale": rationale,
        })

    # =========================================================================
    # 4. BASELINE COMPUTATIONS & ACTUAL UPLIFT
    # =========================================================================
    # Baseline 1: Unconstrained Baseline (Every device where repair is top choice gets repaired)
    unconstrained_total = 0.0
    for d in device_data:
        if d["manual_review_required"]:
            unconstrained_total += d["decision"]["expected_net_recovery"]
        elif d["repair_feasible"] and d["incremental_benefit"] > 0:
            unconstrained_total += d["repair_net"]
        else:
            unconstrained_total += d["best_non_repair_net"]
    unconstrained_total = round(unconstrained_total, 2)

    # Baseline 2: FIFO / Arrival-order Baseline
    # First devices requiring repair take slots until capacity full, regardless of incremental benefit
    fifo_repair_slots_remaining = repair_capacity_slots
    fifo_total = 0.0
    for d in device_data:
        if d["manual_review_required"]:
            fifo_total += d["decision"]["expected_net_recovery"]
        elif d["repair_feasible"] and fifo_repair_slots_remaining > 0:
            fifo_total += d["repair_net"]
            fifo_repair_slots_remaining -= 1
        else:
            fifo_total += d["best_non_repair_net"]
    fifo_total = round(fifo_total, 2)

    # Baseline 3: Lowest-Cost Repair Baseline
    # Devices with cheapest repair cost take slots until capacity full
    repairable_by_cost = sorted([d for d in device_data if d["repair_feasible"] and not d["manual_review_required"]], key=lambda x: x["repair_cost"])
    cheapest_repair_ids = {d["return_id"] for d in repairable_by_cost[:repair_capacity_slots]}
    cheapest_total = 0.0
    for d in device_data:
        if d["manual_review_required"]:
            cheapest_total += d["decision"]["expected_net_recovery"]
        elif d["return_id"] in cheapest_repair_ids:
            cheapest_total += d["repair_net"]
        else:
            cheapest_total += d["best_non_repair_net"]
    cheapest_total = round(cheapest_total, 2)

    dollar_uplift_vs_fifo = round(optimized_total_recovery - fifo_total, 2)
    pct_uplift_vs_fifo = round((dollar_uplift_vs_fifo / abs(fifo_total)) * 100.0, 1) if fifo_total != 0.0 else 0.0

    dollar_uplift_vs_cheapest = round(optimized_total_recovery - cheapest_total, 2)
    pct_uplift_vs_cheapest = round((dollar_uplift_vs_cheapest / abs(cheapest_total)) * 100.0, 1) if cheapest_total != 0.0 else 0.0

    # 5. Explanations
    batch_explanation = (
        f"Evaluated {len(device_data)} returned devices against {repair_capacity_slots} repair bench slots. "
        f"Allocated {slots_used}/{repair_capacity_slots} slots ({capacity_utilization}% utilization) exclusively to devices "
        f"delivering positive incremental net recovery. "
        f"Achieved ${optimized_total_recovery:.2f} total expected net recovery, generating "
        f"+${dollar_uplift_vs_fifo:.2f} (+{pct_uplift_vs_fifo}%) financial uplift over FIFO arrival scheduling and "
        f"+${dollar_uplift_vs_cheapest:.2f} (+{pct_uplift_vs_cheapest}%) over naive cheapest-repair scheduling."
    )

    comparison_summary = {
        "optimized": {
            "total_net_recovery": optimized_total_recovery,
            "repairs_selected": slots_used,
            "strategy": "Maximum Incremental Net Recovery Knapsack Optimization",
        },
        "baseline_fifo": {
            "total_net_recovery": fifo_total,
            "dollar_difference": dollar_uplift_vs_fifo,
            "pct_uplift": pct_uplift_vs_fifo,
            "strategy": "First-In-First-Out (Arrival Order) Repair Scheduling",
        },
        "baseline_cheapest_repair": {
            "total_net_recovery": cheapest_total,
            "dollar_difference": dollar_uplift_vs_cheapest,
            "pct_uplift": pct_uplift_vs_cheapest,
            "strategy": "Cheapest Repair Cost First",
        },
        "baseline_unconstrained": {
            "total_net_recovery": unconstrained_total,
            "strategy": "Theoretical Unconstrained Upper Bound (Infinite Repair Slots)",
        },
    }

    run_id = f"opt_{uuid.uuid4().hex[:12]}"

    # Persist optimization run record
    opt_record = OptimizationRunRecord(
        id=run_id,
        repair_capacity_slots=repair_capacity_slots,
        repair_slots_used=slots_used,
        total_devices_evaluated=len(device_data),
        optimized_total_net_recovery=optimized_total_recovery,
        baseline_unconstrained_net_recovery=unconstrained_total,
        baseline_fifo_net_recovery=fifo_total,
        baseline_cheapest_repair_net_recovery=cheapest_total,
        dollar_uplift_vs_fifo=dollar_uplift_vs_fifo,
        pct_uplift_vs_fifo=pct_uplift_vs_fifo,
        dollar_uplift_vs_cheapest=dollar_uplift_vs_cheapest,
        pct_uplift_vs_cheapest=pct_uplift_vs_cheapest,
        allocations=allocations,
        batch_explanation=batch_explanation,
        comparison_summary=comparison_summary,
    )
    db.add(opt_record)

    # Update return status to 'optimized' and record decisions
    for alloc in allocations:
        ret_obj = db.query(ReturnRecord).filter(ReturnRecord.id == alloc["return_id"]).first()
        if ret_obj:
            ret_obj.status = "optimized"

    db.commit()

    return {
        "run_id": run_id,
        "total_devices_evaluated": len(device_data),
        "repair_capacity_slots": repair_capacity_slots,
        "repair_slots_used": slots_used,
        "capacity_utilization_pct": capacity_utilization,
        "optimized_total_net_recovery": optimized_total_recovery,
        "baseline_unconstrained_net_recovery": unconstrained_total,
        "baseline_fifo_net_recovery": fifo_total,
        "baseline_cheapest_repair_net_recovery": cheapest_total,
        "dollar_uplift_vs_fifo": dollar_uplift_vs_fifo,
        "pct_uplift_vs_fifo": pct_uplift_vs_fifo,
        "dollar_uplift_vs_cheapest": dollar_uplift_vs_cheapest,
        "pct_uplift_vs_cheapest": pct_uplift_vs_cheapest,
        "allocations": allocations,
        "batch_explanation": batch_explanation,
        "comparison_summary": comparison_summary,
        "created_at": opt_record.created_at,
    }
