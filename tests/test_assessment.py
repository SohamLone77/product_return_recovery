def test_assessment_unknown_return_id_404(client):
    """Test 7: Assessments with unknown return IDs are rejected with 404."""
    payload = {
        "return_id": "ret_non_existent_12345",
        "product_condition": "like_new",
        "defect_category": "none",
        "warranty_status": "active"
    }
    response = client.post("/assessment", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_assessment_invalid_fields_rejected(client):
    """Test 8: Invalid assessment fields are rejected."""
    # First create a valid return
    ret_res = client.post("/returns", json={
        "product_id": "SKU-TEST",
        "product_name": "Test Item",
        "category": "Electronics",
        "purchase_price": 100.0,
        "customer_id": "C-1",
        "return_reason": "Broken",
    })
    return_id = ret_res.json()["id"]

    # Invalid product_condition
    bad_condition = {
        "return_id": return_id,
        "product_condition": "totally_smashed_to_bits",  # invalid
        "defect_category": "none",
        "warranty_status": "active"
    }
    res1 = client.post("/assessment", json=bad_condition)
    assert res1.status_code == 422

    # Invalid defect_category
    bad_defect = {
        "return_id": return_id,
        "product_condition": "minor_damage",
        "defect_category": "alien_laser_burn",  # invalid
        "warranty_status": "active"
    }
    res2 = client.post("/assessment", json=bad_defect)
    assert res2.status_code == 422

    # Invalid fraud score > 1.0
    bad_fraud = {
        "return_id": return_id,
        "product_condition": "minor_damage",
        "defect_category": "functional",
        "warranty_status": "active",
        "fraud_risk_score": 2.5
    }
    res3 = client.post("/assessment", json=bad_fraud)
    assert res3.status_code == 422


def test_create_valid_assessment_and_link_to_return(client):
    """Test 6: Valid assessments persist and link to the correct return."""
    ret_res = client.post("/returns", json={
        "product_id": "SKU-440",
        "product_name": "Espresso Machine",
        "category": "Appliances",
        "purchase_price": 450.0,
        "customer_id": "CUST-44",
        "return_reason": "Steam wand pressure failure",
    })
    return_id = ret_res.json()["id"]

    assessment_payload = {
        "return_id": return_id,
        "product_condition": "minor_damage",
        "defect_category": "functional",
        "defect_description": "Steam wand valve loose, electrical pump works normally.",
        "visible_damage": False,
        "warranty_status": "active",
        "purchase_date": "2025-01-10",
        "warranty_expiry_date": "2026-01-10",
        "verified_warranty_eligible": True,
        "proof_of_purchase_metadata": {"invoice_no": "INV-9821"},
        "fraud_risk_score": 0.05,
        "fraud_flags": [],
        "assessor_notes": "Clean physical state, original box included."
    }
    response = client.post("/assessment", json=assessment_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("asm_")
    assert data["return_id"] == return_id
    assert data["product_condition"] == "minor_damage"
    assert data["verified_warranty_eligible"] is True
    assert data["warranty_status"] == "active"

    # Check that return status was updated to 'assessed'
    returns_list = client.get(f"/returns")
    target = [item for item in returns_list.json()["items"] if item["id"] == return_id][0]
    assert target["status"] == "assessed"
