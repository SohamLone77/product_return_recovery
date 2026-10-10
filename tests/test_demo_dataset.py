def test_seed_demo_dataset_creates_10_devices(client):
    """Test: Seeding creates exactly 10 demonstration devices."""
    res = client.post("/demo/seed")
    assert res.status_code == 201
    data = res.json()
    assert data["seeded_count"] == 10
    assert len(data["return_ids"]) == 10

    # Verify GET /demo/dataset
    spec_res = client.get("/demo/dataset")
    assert spec_res.status_code == 200
    assert len(spec_res.json()["devices"]) == 10


def test_10_devices_demonstration_scenarios(client):
    """Test: All 6 required business scenarios in the 10-device dataset execute accurately."""
    client.post("/demo/seed")
    opt = client.post("/optimize", json={"repair_capacity_slots": 4}).json()

    allocations_by_product = {a["product_name"]: a for a in opt["allocations"]}

    # Scenario 1: Repair has strong positive incremental value (Phones, Laptops, Tablets, TV)
    flagship_phone = next(a for name, a in allocations_by_product.items() if "Flagship Smartphone" in name)
    gaming_laptop = next(a for name, a in allocations_by_product.items() if "Ultra Gaming Laptop" in name)
    creator_tablet = next(a for name, a in allocations_by_product.items() if "Professional Creator Tablet" in name)
    oled_tv = next(a for name, a in allocations_by_product.items() if "Smart 4K OLED Cinema TV" in name)

    assert flagship_phone["assigned_route"] == "repair"
    assert flagship_phone["repair_incremental_benefit"] > 0

    assert gaming_laptop["assigned_route"] == "repair"
    assert gaming_laptop["repair_incremental_benefit"] > 0

    assert creator_tablet["assigned_route"] == "repair"
    assert creator_tablet["repair_incremental_benefit"] > 0

    assert oled_tv["assigned_route"] == "repair"
    assert oled_tv["repair_incremental_benefit"] > 0

    # Exactly 4 repair slots used
    assert opt["repair_slots_used"] == 4
    assert opt["capacity_utilization_pct"] == 100.0

    # Scenario 2: Repair is possible but economically unattractive (Budget Phone)
    budget_phone = next(a for name, a in allocations_by_product.items() if "Budget Smartphone A12" in name)
    assert budget_phone["assigned_route"] != "repair"
    assert budget_phone["was_repair_selected"] is False
    assert budget_phone["repair_incremental_benefit"] <= 0

    # Scenario 3: Refurbishment beats repair (Smartwatch Active 5)
    smartwatch = next(a for name, a in allocations_by_product.items() if "Smartwatch Active 5" in name)
    assert smartwatch["assigned_route"] == "refurbish"
    assert smartwatch["was_repair_selected"] is False

    # Scenario 4: Parts harvesting beats recycling (Custom Gaming Tower)
    gaming_tower = next(a for name, a in allocations_by_product.items() if "High-Performance Tower PC" in name)
    assert gaming_tower["assigned_route"] == "harvest_parts"
    assert gaming_tower["expected_net_recovery"] > 100.0

    # Scenario 5: Warranty verification materially affects expected cost (Smart Home Hub)
    smart_hub = next(a for name, a in allocations_by_product.items() if "Smart Home Automation Hub" in name)
    assert smart_hub["assigned_route"] == "return_to_supplier"

    # Scenario 6: Manual review is appropriate (Counterfeit Earbuds & Swollen Battery Ultrabook)
    counterfeit_buds = next(a for name, a in allocations_by_product.items() if "Counterfeit Suspect" in name)
    assert counterfeit_buds["assigned_route"] == "manual_assessment"
    assert counterfeit_buds["manual_review_required"] is True

    swollen_laptop = next(a for name, a in allocations_by_product.items() if "Swollen Lithium Cell" in name)
    assert swollen_laptop["assigned_route"] == "manual_assessment"
    assert swollen_laptop["manual_review_required"] is True
