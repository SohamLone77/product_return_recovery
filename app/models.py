import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class ReturnRecord(Base):
    __tablename__ = "returns"

    id = Column(String(64), primary_key=True, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    purchase_price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")
    customer_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(64), nullable=True)
    return_reason = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="registered")  # registered, assessed, decided
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    assessments = relationship("AssessmentRecord", back_populates="return_record", cascade="all, delete-orphan", order_by="desc(AssessmentRecord.created_at)")
    decisions = relationship("DecisionRecord", back_populates="return_record", cascade="all, delete-orphan", order_by="desc(DecisionRecord.created_at)")


class AssessmentRecord(Base):
    __tablename__ = "assessments"

    id = Column(String(64), primary_key=True, index=True)
    return_id = Column(String(64), ForeignKey("returns.id"), nullable=False, index=True)
    product_condition = Column(String(32), nullable=False)  # unopened, like_new, minor_damage, major_damage, defective
    defect_category = Column(String(32), nullable=False)    # none, cosmetic, functional, missing_parts, electrical, other
    defect_description = Column(Text, nullable=True)
    visible_damage = Column(Boolean, nullable=False, default=False)
    warranty_status = Column(String(32), nullable=False)    # user-reported: active, expired, unknown, none
    purchase_date = Column(String(64), nullable=True)
    warranty_expiry_date = Column(String(64), nullable=True)
    verified_warranty_eligible = Column(Boolean, nullable=True)  # verified eligibility distinct from user-reported
    proof_of_purchase_metadata = Column(JSON, nullable=True)
    image_reference = Column(String(255), nullable=True)
    fraud_risk_score = Column(Float, nullable=True)
    fraud_flags = Column(JSON, nullable=True)
    assessor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship
    return_record = relationship("ReturnRecord", back_populates="assessments")


class DecisionRecord(Base):
    __tablename__ = "decisions"

    id = Column(String(64), primary_key=True, index=True)
    return_id = Column(String(64), ForeignKey("returns.id"), nullable=False, index=True)
    recommended_action = Column(String(64), nullable=False)  # restock, repair, refurbish, resell_secondary, return_to_supplier, harvest_parts, recycle, dispose, manual_assessment
    expected_recovered_value = Column(Float, nullable=False, default=0.0)
    estimated_costs = Column(Float, nullable=False, default=0.0)
    expected_net_recovery = Column(Float, nullable=False, default=0.0)
    cost_breakdown = Column(JSON, nullable=False, default=dict)
    alternative_routes = Column(JSON, nullable=False, default=list)
    reason_codes = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=False)
    manual_review_required = Column(Boolean, nullable=False, default=False)
    flags = Column(JSON, nullable=False, default=list)
    capacity_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship
    return_record = relationship("ReturnRecord", back_populates="decisions")
