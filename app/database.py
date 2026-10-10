from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# For SQLite, ensure check_same_thread=False
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency that yields a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_schema_migrations(engine):
    """
    Ensures newly added columns exist in SQLite without requiring manual migrations.
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        # Check assessments table
        if "assessments" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("assessments")}
            new_assessment_cols = [
                ("repair_probability", "REAL"),
                ("estimated_repair_cost", "REAL"),
                ("estimated_repair_hours", "REAL"),
                ("potential_resale_value", "REAL"),
                ("parts_recovery_value", "REAL"),
                ("authenticity_risk", "REAL"),
                ("safety_hazard", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in new_assessment_cols:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE assessments ADD COLUMN {col_name} {col_type}"))

        # Check decisions table
        if "decisions" in inspector.get_table_names():
            existing_cols = {col["name"] for col in inspector.get_columns("decisions")}
            new_decision_cols = [
                ("recommended_route", "TEXT"),
                ("best_non_repair_route", "TEXT"),
                ("best_non_repair_net_recovery", "REAL"),
                ("repair_incremental_benefit", "REAL"),
                ("incremental_value_vs_next_best_route", "REAL"),
                ("confidence_score", "REAL"),
                ("manual_review_reasons", "TEXT"),
                ("assumptions", "TEXT"),
                ("operational_reasons", "TEXT"),
            ]
            for col_name, col_type in new_decision_cols:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE decisions ADD COLUMN {col_name} {col_type}"))
