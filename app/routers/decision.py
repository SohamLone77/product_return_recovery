import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReturnRecord, AssessmentRecord, DecisionRecord
from app.schemas import (
    DecisionRequest,
    DecisionResponse,
    OptimizeRequest,
    OptimizeResponse,
    DemoSeedResponse,
)
from app.decision_engine import calculate_recovery_decision
from app.optimizer_service import run_batch_optimization
from app.demo_dataset import seed_demo_dataset, DEMO_DEVICES_SPEC

router = APIRouter(tags=["Reverse Logistics Decision & Optimization Engine"])

@router.post(
    "/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate single device disposition",
    description="Calculates expected net recovery across all 7 disposition routes, computes incremental repair benefit vs best non-repair fallback, enforces policy guardrails, and persists the decision."
)
def generate_decision(
    payload: DecisionRequest,
    db: Session = Depends(get_db)
):
    return_rec = db.query(ReturnRecord).filter(ReturnRecord.id == payload.return_id).first()
    if not return_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return record with ID '{payload.return_id}' not found."
        )

    # Fetch latest assessment
    latest_assessment = (
        db.query(AssessmentRecord)
        .filter(AssessmentRecord.return_id == payload.return_id)
        .order_by(AssessmentRecord.created_at.desc())
        .first()
    )

    decision_data = calculate_recovery_decision(
        return_rec=return_rec,
        assessment=latest_assessment,
        custom_costs=payload.custom_costs
    )

    decision_id = f"dec_{uuid.uuid4().hex[:12]}"
    decision_rec = DecisionRecord(
        id=decision_id,
        return_id=payload.return_id,
        recommended_action=decision_data["recommended_action"],
        recommended_route=decision_data["recommended_route"],
        expected_recovered_value=decision_data["expected_recovered_value"],
        estimated_costs=decision_data["estimated_costs"],
        expected_net_recovery=decision_data["expected_net_recovery"],
        cost_breakdown=decision_data["cost_breakdown"],
        alternative_routes=decision_data["alternative_routes"],
        reason_codes=decision_data["reason_codes"],
        explanation=decision_data["explanation"],
        manual_review_required=decision_data["manual_review_required"],
        manual_review_reasons=decision_data["manual_review_reasons"],
        flags=decision_data["flags"],
        capacity_notes=decision_data["capacity_notes"],
        best_non_repair_route=decision_data["best_non_repair_route"],
        best_non_repair_net_recovery=decision_data["best_non_repair_net_recovery"],
        repair_incremental_benefit=decision_data["repair_incremental_benefit"],
        incremental_value_vs_next_best_route=decision_data["incremental_value_vs_next_best_route"],
        confidence_score=decision_data["confidence_score"],
        assumptions=decision_data["assumptions"],
        operational_reasons=decision_data["operational_reasons"],
    )

    db.add(decision_rec)
    return_rec.status = "decided"
    db.commit()
    db.refresh(decision_rec)

    return decision_rec


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch optimize repair allocation under capacity constraints",
    description="Solves the reverse logistics knapsack problem over N devices and K repair bench slots. Maximizes aggregate net recovery by allocating slots based on positive incremental repair benefit over best non-repair fallbacks. Computes rigorous uplift vs FIFO and cheapest-repair baselines."
)
def batch_optimize(
    payload: OptimizeRequest = OptimizeRequest(),
    db: Session = Depends(get_db)
):
    result = run_batch_optimization(
        db=db,
        return_ids=payload.return_ids,
        repair_capacity_slots=payload.repair_capacity_slots,
        max_repair_hours=payload.max_repair_hours,
        custom_costs=payload.custom_costs,
    )
    return result


@router.post(
    "/demo/seed",
    response_model=DemoSeedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Seed 10 synthetic demonstration electronic devices",
    description="Populates the database with 10 representative electronic returns illustrating repair viability, refurbishment superiority, component harvesting, warranty claims, and safety/authenticity manual reviews."
)
def seed_demo(db: Session = Depends(get_db)):
    result = seed_demo_dataset(db)
    return result


@router.get(
    "/demo/dataset",
    summary="Inspect 10 synthetic demonstration devices specification",
    description="Returns the raw specification of the 10 synthetic devices for inspection and UI visualization."
)
def get_demo_dataset_spec():
    return {
        "description": "10 Synthetic Demonstration Electronic Devices for Reverse Logistics Optimization",
        "repair_capacity_slots": 4,
        "devices": DEMO_DEVICES_SPEC,
    }
