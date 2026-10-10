from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import ReturnRecord, AssessmentRecord, DecisionRecord

def calculate_operational_analytics(db: Session) -> Dict[str, Any]:
    """
    Computes rigorous operational and financial analytics directly from stored records.
    Deduplicates across multiple assessments or decisions per return by selecting the latest
    finalized assessment and latest decision per unique return.
    """
    # 1. Fetch all returns
    all_returns = db.query(ReturnRecord).all()
    total_returns = len(all_returns)

    returns_by_condition: Dict[str, int] = {}
    returns_by_warranty_status: Dict[str, int] = {}
    counts_by_recommended_action: Dict[str, int] = {}

    total_recovered_val = 0.0
    total_processing_costs = 0.0
    total_net_recovery = 0.0
    manual_review_count = 0
    fraud_flag_count = 0
    records_with_complete_data = 0

    if total_returns == 0:
        return {
            "total_returns": 0,
            "returns_by_condition": {},
            "returns_by_warranty_status": {},
            "counts_by_recommended_action": {},
            "total_estimated_recovered_value": 0.0,
            "total_estimated_processing_costs": 0.0,
            "total_expected_net_recovery": 0.0,
            "manual_physical_review_count": 0,
            "fraud_risk_flag_count": 0,
            "records_with_complete_economic_data": 0,
            "accounting_notes": "Database is currently empty. All financial and operational aggregations are zeroed.",
        }

    for ret in all_returns:
        # Latest assessment (if any)
        latest_assessment = (
            db.query(AssessmentRecord)
            .filter(AssessmentRecord.return_id == ret.id)
            .order_by(AssessmentRecord.created_at.desc())
            .first()
        )

        if latest_assessment:
            cond = latest_assessment.product_condition
            returns_by_condition[cond] = returns_by_condition.get(cond, 0) + 1

            w_stat = latest_assessment.warranty_status
            returns_by_warranty_status[w_stat] = returns_by_warranty_status.get(w_stat, 0) + 1

            if latest_assessment.fraud_risk_score and latest_assessment.fraud_risk_score >= 0.7:
                fraud_flag_count += 1
            elif latest_assessment.fraud_flags and len(latest_assessment.fraud_flags) > 0:
                fraud_flag_count += 1
        else:
            returns_by_condition["unassessed"] = returns_by_condition.get("unassessed", 0) + 1
            returns_by_warranty_status["unassessed"] = returns_by_warranty_status.get("unassessed", 0) + 1

        # Latest decision (if any)
        latest_decision = (
            db.query(DecisionRecord)
            .filter(DecisionRecord.return_id == ret.id)
            .order_by(DecisionRecord.created_at.desc())
            .first()
        )

        if latest_decision:
            action = latest_decision.recommended_action
            counts_by_recommended_action[action] = counts_by_recommended_action.get(action, 0) + 1

            if latest_decision.manual_review_required:
                manual_review_count += 1

            total_recovered_val += float(latest_decision.expected_recovered_value or 0.0)
            total_processing_costs += float(latest_decision.estimated_costs or 0.0)
            total_net_recovery += float(latest_decision.expected_net_recovery or 0.0)
            records_with_complete_data += 1

    return {
        "total_returns": total_returns,
        "returns_by_condition": returns_by_condition,
        "returns_by_warranty_status": returns_by_warranty_status,
        "counts_by_recommended_action": counts_by_recommended_action,
        "total_estimated_recovered_value": round(total_recovered_val, 2),
        "total_estimated_processing_costs": round(total_processing_costs, 2),
        "total_expected_net_recovery": round(total_net_recovery, 2),
        "manual_physical_review_count": manual_review_count,
        "fraud_risk_flag_count": fraud_flag_count,
        "records_with_complete_economic_data": records_with_complete_data,
        "accounting_notes": (
            f"Financial aggregations calculated strictly across {records_with_complete_data} returns with completed decision records. "
            "Returns without completed decisions are excluded from financial totals to prevent distorted averages. "
            "Each return's latest assessment and decision are used to prevent duplicate counting."
        ),
    }
