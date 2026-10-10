import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReturnRecord, AssessmentRecord
from app.schemas import AssessmentCreate, AssessmentResponse

router = APIRouter(prefix="/assessment", tags=["Assessment"])

@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit return physical assessment",
    description="Validates product condition, defect classification, warranty eligibility, and engineering parameters. Links assessment directly to the referenced return record."
)
def submit_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db)
):
    # Verify referenced return exists
    return_rec = db.query(ReturnRecord).filter(ReturnRecord.id == payload.return_id).first()
    if not return_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Return record with ID '{payload.return_id}' not found."
        )

    assessment_id = f"asm_{uuid.uuid4().hex[:12]}"

    assessment = AssessmentRecord(
        id=assessment_id,
        return_id=payload.return_id,
        product_condition=payload.product_condition,
        defect_category=payload.defect_category,
        defect_description=payload.defect_description,
        visible_damage=payload.visible_damage,
        warranty_status=payload.warranty_status,
        purchase_date=payload.purchase_date,
        warranty_expiry_date=payload.warranty_expiry_date,
        verified_warranty_eligible=payload.verified_warranty_eligible,
        proof_of_purchase_metadata=payload.proof_of_purchase_metadata,
        image_reference=payload.image_reference,
        fraud_risk_score=payload.fraud_risk_score,
        fraud_flags=payload.fraud_flags,
        assessor_notes=payload.assessor_notes,
        repair_probability=payload.repair_probability,
        estimated_repair_cost=payload.estimated_repair_cost,
        estimated_repair_hours=payload.estimated_repair_hours,
        potential_resale_value=payload.potential_resale_value,
        parts_recovery_value=payload.parts_recovery_value,
        authenticity_risk=payload.authenticity_risk,
        safety_hazard=payload.safety_hazard,
    )

    db.add(assessment)

    # Update return status if not yet decided
    if return_rec.status == "registered":
        return_rec.status = "assessed"

    db.commit()
    db.refresh(assessment)
    return assessment
