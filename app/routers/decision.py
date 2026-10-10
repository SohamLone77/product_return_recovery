import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReturnRecord, AssessmentRecord, DecisionRecord
from app.schemas import DecisionRequest, DecisionResponse
from app.decision_engine import calculate_recovery_decision

router = APIRouter(prefix="/decision", tags=["Decision Engine"])

@router.post(
    "",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate explainable recovery decision",
    description="Evaluates product return condition, warranty eligibility, and economic costs across feasible disposition routes. Persists the decision record."
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
        expected_recovered_value=decision_data["expected_recovered_value"],
        estimated_costs=decision_data["estimated_costs"],
        expected_net_recovery=decision_data["expected_net_recovery"],
        cost_breakdown=decision_data["cost_breakdown"],
        alternative_routes=decision_data["alternative_routes"],
        reason_codes=decision_data["reason_codes"],
        explanation=decision_data["explanation"],
        manual_review_required=decision_data["manual_review_required"],
        flags=decision_data["flags"],
        capacity_notes=decision_data["capacity_notes"],
    )

    db.add(decision_rec)
    return_rec.status = "decided"
    db.commit()
    db.refresh(decision_rec)

    return decision_rec
