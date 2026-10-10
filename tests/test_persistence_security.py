import os
import tempfile
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app

def test_persistence_survives_restart():
    """Test 14: Persistence survives application restart when using file-based storage."""
    # Create a temporary file database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        temp_db_path = tmp_file.name

    try:
        temp_db_url = f"sqlite:///{temp_db_path}"
        engine_file = create_engine(temp_db_url, connect_args={"check_same_thread": False})
        SessionFile = sessionmaker(autocommit=False, autoflush=False, bind=engine_file)
        Base.metadata.create_all(bind=engine_file)

        # Session 1: Write a return
        db1 = SessionFile()
        def override_db1():
            try:
                yield db1
            finally:
                db1.close()

        app.dependency_overrides[get_db] = override_db1
        with TestClient(app) as client1:
            res = client1.post("/returns", json={
                "product_id": "RESTART-SKU",
                "product_name": "Resilient Hardware",
                "category": "Electronics",
                "purchase_price": 500.0,
                "customer_id": "C-RESTART",
                "return_reason": "Testing persistence restart",
            })
            assert res.status_code == 201
            return_id = res.json()["id"]

        app.dependency_overrides.clear()
        engine_file.dispose()

        # Session 2: Re-open the file database (simulating server restart)
        engine_restarted = create_engine(temp_db_url, connect_args={"check_same_thread": False})
        SessionRestarted = sessionmaker(autocommit=False, autoflush=False, bind=engine_restarted)

        db2 = SessionRestarted()
        def override_db2():
            try:
                yield db2
            finally:
                db2.close()

        app.dependency_overrides[get_db] = override_db2
        with TestClient(app) as client2:
            get_res = client2.get("/returns")
            assert get_res.status_code == 200
            items = get_res.json()["items"]
            assert any(item["id"] == return_id for item in items)

        app.dependency_overrides.clear()
        engine_restarted.dispose()

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except OSError:
                pass


def test_server_errors_do_not_expose_stack_traces(db_session, monkeypatch):
    """Test 15: Unhandled exceptions are caught gracefully without exposing internal tracebacks."""
    # Simulate an internal runtime exception during database commit
    def faulty_commit():
        raise RuntimeError("SensitiveDatabaseException: secret_credentials_leaked")

    monkeypatch.setattr(db_session, "commit", faulty_commit)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Use raise_server_exceptions=False so TestClient returns the 500 response from FastAPI exception handler
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post("/returns", json={
            "product_id": "ERR-1",
            "product_name": "Crash Test",
            "category": "Test",
            "purchase_price": 10.0,
            "customer_id": "C-ERR",
            "return_reason": "Trigger error",
        })

    app.dependency_overrides.clear()

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    # Ensure raw trace and sensitive details are NOT leaked to client
    assert "SensitiveDatabaseException" not in data["detail"]
    assert "secret_credentials_leaked" not in data["detail"]
    assert "Traceback" not in data["detail"]
    assert data["detail"] == "An internal server error occurred. Please contact system administrator."
