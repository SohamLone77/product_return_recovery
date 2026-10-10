import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ReturnRecord
from app.schemas import ReturnCreate, ReturnResponse, ReturnListResponse

router = APIRouter(prefix="/returns", tags=["Returns"])

@router.post(
    "",
    response_model=ReturnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new return record",
    description="Validates product return details, generates a unique return ID, and persists the return record."
)
def create_return(
    payload: ReturnCreate,
    db: Session = Depends(get_db)
):
    return_id = f"ret_{uuid.uuid4().hex[:12]}"

    db_return = ReturnRecord(
        id=return_id,
        product_id=payload.product_id,
        product_name=payload.product_name,
        category=payload.category,
        purchase_price=payload.purchase_price,
        currency=payload.currency,
        customer_id=payload.customer_id,
        order_id=payload.order_id,
        return_reason=payload.return_reason,
        status="registered",
    )
    db.add(db_return)
    db.commit()
    db.refresh(db_return)
    return db_return


@router.get(
    "",
    response_model=ReturnListResponse,
    summary="Retrieve stored return records",
    description="Queries persisted return records with support for pagination and filtering by category or status."
)
def list_returns(
    limit: int = Query(50, ge=1, le=200, description="Max number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    category: Optional[str] = Query(None, description="Filter returns by category"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter returns by processing status"),
    db: Session = Depends(get_db)
):
    query = db.query(ReturnRecord)

    if category:
        query = query.filter(ReturnRecord.category.ilike(f"%{category.strip()}%"))
    if status_filter:
        query = query.filter(ReturnRecord.status == status_filter.strip())

    total = query.count()
    items = query.order_by(ReturnRecord.created_at.desc()).offset(offset).limit(limit).all()

    return ReturnListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )
