def test_analytics_empty_dataset(client):
    """Test 12: Analytics handles empty datasets gracefully."""
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_returns"] == 0
    assert data["total_estimated_recovered_value"] == 0.0
    assert data["total_estimated_processing_costs"] == 0.0
    assert data["total_expected_net_recovery"] == 0.0
    assert data["manual_physical_review_count"] == 0
    assert data["fraud_risk_flag_count"] == 0
    assert data["records_with_complete_economic_data"] == 0


def test_analytics_populated_and_deduplication(client):
    """Test 12 & 13: Analytics with populated data and avoiding inflation from multiple assessments/decisions."""
    # Create return 1
    ret1 = client.post("/returns", json={
        "product_id": "P-1",
        "product_name": "Espresso Machine",
        "category": "Appliances",
        "purchase_price": 500.0,
        "customer_id": "C-1",
        "return_reason": "Doesn't power on",
    }).json()

    # Create assessment 1 for return 1
    client.post("/assessment", json={
        "return_id": ret1["id"],
        "product_condition": "minor_damage",
        "defect_category": "electrical",
        "warranty_status": "active",
        "verified_warranty_eligible": True
    })

    # Decision for return 1
    dec1 = client.post("/decision", json={"return_id": ret1["id"]}).json()

    # Second decision for return 1 (e.g. re-evaluated or updated)
    dec1_second = client.post("/decision", json={"return_id": ret1["id"]}).json()

    # Create return 2 (Unopened)
    ret2 = client.post("/returns", json={
        "product_id": "P-2",
        "product_name": "Smart Speaker",
        "category": "Electronics",
        "purchase_price": 100.0,
        "customer_id": "C-2",
        "return_reason": "Unopened return",
    }).json()

    client.post("/assessment", json={
        "return_id": ret2["id"],
        "product_condition": "unopened",
        "defect_category": "none",
        "warranty_status": "none"
    })
    dec2 = client.post("/decision", json={"return_id": ret2["id"]}).json()

    # Check analytics
    analytics_res = client.get("/analytics")
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    # Exactly 2 unique returns
    assert data["total_returns"] == 2
    assert data["records_with_complete_economic_data"] == 2

    # Check conditions
    assert data["returns_by_condition"].get("minor_damage") == 1
    assert data["returns_by_condition"].get("unopened") == 1

    # Check that financial totals are sum of latest decisions of ret1 and ret2, NOT inflated by the duplicate decision on ret1
    expected_recovered = round(dec1_second["expected_recovered_value"] + dec2["expected_recovered_value"], 2)
    expected_costs = round(dec1_second["estimated_costs"] + dec2["estimated_costs"], 2)
    expected_net = round(dec1_second["expected_net_recovery"] + dec2["expected_net_recovery"], 2)

    assert data["total_estimated_recovered_value"] == expected_recovered
    assert data["total_estimated_processing_costs"] == expected_costs
    assert data["total_expected_net_recovery"] == expected_net
