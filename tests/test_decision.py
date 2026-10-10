def test_decision_restock_optimal(client):
    """Test 9 & 11: Decisions work when sufficient economic data exists and math matches documented formula."""
    # 1. Create return
    ret_res = client.post("/returns", json={
        "product_id": "SKU-RESTOCK-1",
        "product_name": "Premium Blender",
        "category": "Appliances",
        "purchase_price": 200.0,
        "customer_id": "C-10",
        "return_reason": "Unwanted gift",
    })
    return_id = ret_res.json()["id"]

    # 2. Add unopened assessment
    client.post("/assessment", json={
        "return_id": return_id,
        "product_condition": "unopened",
        "defect_category": "none",
        "visible_damage": False,
        "warranty_status": "active"
    })

    # 3. Request decision
    dec_res = client.post("/decision", json={"return_id": return_id})
    assert dec_res.status_code == 200
    data = dec_res.json()

    assert data["return_id"] == return_id
    assert data["recommended_action"] == "restock"
    assert data["manual_review_required"] is False
    assert "RC_RESTOCK_MAX_MARGIN" in data["reason_codes"]

    # Verify formula consistency: Net Recovery = Recovered Value - Estimated Costs
    recovered_val = data["expected_recovered_value"]
    costs = data["estimated_costs"]
    net_recovery = data["expected_net_recovery"]
    assert round(recovered_val - costs, 2) == round(net_recovery, 2)
    assert len(data["alternative_routes"]) > 0


def test_decision_supplier_warranty(client):
    """Test 9: Verified warranty route correctly chooses return_to_supplier."""
    ret_res = client.post("/returns", json={
        "product_id": "SKU-MONITOR",
        "product_name": "4K Gaming Monitor",
        "category": "Electronics",
        "purchase_price": 600.0,
        "customer_id": "C-20",
        "return_reason": "Display panel flickering",
    })
    return_id = ret_res.json()["id"]

    client.post("/assessment", json={
        "return_id": return_id,
        "product_condition": "defective",
        "defect_category": "electrical",
        "visible_damage": False,
        "warranty_status": "active",
        "verified_warranty_eligible": True
    })

    dec_res = client.post("/decision", json={"return_id": return_id})
    assert dec_res.status_code == 200
    data = dec_res.json()
    assert data["recommended_action"] == "return_to_supplier"
    assert "RC_SUPPLIER_WARRANTY_RECOVERY" in data["reason_codes"]
    assert round(data["expected_recovered_value"] - data["estimated_costs"], 2) == round(data["expected_net_recovery"], 2)


def test_decision_ambiguous_or_incomplete_cases_flagged(client):
    """Test 10: Ambiguous damage or missing assessment cases are flagged for manual review."""
    # Case A: Return with NO assessment
    ret_no_asm = client.post("/returns", json={
        "product_id": "SKU-NO-ASM",
        "product_name": "Tablet",
        "category": "Electronics",
        "purchase_price": 400.0,
        "customer_id": "C-30",
        "return_reason": "Not working",
    })
    id_no_asm = ret_no_asm.json()["id"]

    dec_res_no_asm = client.post("/decision", json={"return_id": id_no_asm})
    assert dec_res_no_asm.status_code == 200
    data_no_asm = dec_res_no_asm.json()
    assert data_no_asm["recommended_action"] == "manual_assessment"
    assert data_no_asm["manual_review_required"] is True
    assert "MISSING_ASSESSMENT" in data_no_asm["flags"]

    # Case B: High fraud risk indicator
    ret_fraud = client.post("/returns", json={
        "product_id": "SKU-FRAUD",
        "product_name": "Gold Watch",
        "category": "Jewelry",
        "purchase_price": 1500.0,
        "customer_id": "C-SUSPECT",
        "return_reason": "Box was empty upon receipt",
    })
    id_fraud = ret_fraud.json()["id"]

    client.post("/assessment", json={
        "return_id": id_fraud,
        "product_condition": "unopened",
        "defect_category": "none",
        "warranty_status": "none",
        "fraud_risk_score": 0.88,
        "fraud_flags": ["WEIGHT_MISMATCH", "REPEAT_CLAIMANT"]
    })

    dec_fraud = client.post("/decision", json={"return_id": id_fraud})
    assert dec_fraud.status_code == 200
    data_fraud = dec_fraud.json()
    assert data_fraud["recommended_action"] == "manual_assessment"
    assert data_fraud["manual_review_required"] is True
    assert "FRAUD_RISK_SUSPECTED" in data_fraud["flags"]
