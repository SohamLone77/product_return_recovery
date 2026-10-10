from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import AnalyticsResponse
from app.analytics_service import calculate_operational_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get(
    "",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute operational and financial return analytics",
    description="Aggregates returns by condition, warranty status, recommended action, and calculates net financial recovery totals across persisted records."
)
def get_analytics(db: Session = Depends(get_db)):
    analytics_data = calculate_operational_analytics(db)
    return analytics_data
