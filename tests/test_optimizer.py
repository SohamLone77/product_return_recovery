import pytest
from app.models import ReturnRecord, AssessmentRecord
from app.decision_engine import calculate_recovery_decision

def test_repair_probability_zero_and_one(client):
    """Test: Repair probability at p=0 and p=1 behaves according to probabilistic model."""
    ret = client.post("/returns", json={
        "product_id": "P-PROB",
        "product_name": "Test Prob Phone",
        "category": "Electronics",
        "purchase_price": 500.0,
        "customer_id": "C-1",
        "return_reason": "Testing probabilities",
    }).json()

    # Case A: p_success = 0.0 (guaranteed failure) -> repair recovery equals fallback minus repair costs
    asm_p0 = client.post("/assessment", json={
        "return_id": ret["id"],
        "product_condition": "defective",
        "defect_category": "electrical",
        "warranty_status": "none",
        "repair_probability": 0.0,
        "potential_resale_value": 400.0,
        "estimated_repair_cost": 100.0,
        "parts_recovery_value": 80.0,
    }).json()

    dec_p0 = client.post("/decision", json={"return_id": ret["id"]}).json()
    repair_route_p0 = next(r for r in dec_p0["alternative_routes"] if r["route"] == "repair")
    # Repair is economically terrible when p=0
    assert dec_p0["recommended_action"] != "repair"
    assert dec_p0["repair_incremental_benefit"] < 0

    # Case B: p_success = 1.0 (guaranteed success)
    asm_p1 = client.post("/assessment", json={
        "return_id": ret["id"],
        "product_condition": "minor_damage",
        "defect_category": "functional",
        "warranty_status": "none",
        "repair_probability": 1.0,
        "potential_resale_value": 420.0,
        "estimated_repair_cost": 50.0,
        "parts_recovery_value": 80.0,
    }).json()

    dec_p1 = client.post("/decision", json={"return_id": ret["id"]}).json()
    assert dec_p1["recommended_action"] == "repair"
    assert dec_p1["repair_incremental_benefit"] > 0


def test_capacity_variations_and_unprofitable_rejection(client):
    """Test: Optimization under capacities 0, 1, 2, 4 and leaving unused slots if unprofitable."""
    # Seed 10 devices
    seed_res = client.post("/demo/seed")
    assert seed_res.status_code == 201

    # Capacity = 0 (No repairs permitted)
    opt_c0 = client.post("/optimize", json={"repair_capacity_slots": 0}).json()
    assert opt_c0["repair_slots_used"] == 0
    assert all(a["assigned_route"] != "repair" for a in opt_c0["allocations"])

    # Capacity = 1 (Exactly the single highest incremental benefit repair device gets slot)
    opt_c1 = client.post("/optimize", json={"repair_capacity_slots": 1}).json()
    assert opt_c1["repair_slots_used"] == 1
    repaired_c1 = [a for a in opt_c1["allocations"] if a["assigned_route"] == "repair"]
    assert len(repaired_c1) == 1

    # Capacity = 2
    opt_c2 = client.post("/optimize", json={"repair_capacity_slots": 2}).json()
    assert opt_c2["repair_slots_used"] == 2

    # Capacity = 4
    opt_c4 = client.post("/optimize", json={"repair_capacity_slots": 4}).json()
    assert opt_c4["repair_slots_used"] <= 4

    # Capacity = 10 (Large capacity):
    # System must NOT fill all 10 slots if only 4 devices have positive incremental repair benefit!
    opt_c10 = client.post("/optimize", json={"repair_capacity_slots": 10}).json()
    assert opt_c10["repair_slots_used"] == 4  # Unprofitable repairs must be rejected!
    assert opt_c10["repair_slots_used"] < 10


def test_optimization_aggregate_equals_sum_of_devices(client):
    """Test: Total expected net recovery equals the exact sum of individual device allocations."""
    client.post("/demo/seed")
    opt = client.post("/optimize", json={"repair_capacity_slots": 4}).json()

    individual_sum = round(sum(a["expected_net_recovery"] for a in opt["allocations"]), 2)
    assert round(opt["optimized_total_net_recovery"], 2) == individual_sum


def test_manual_review_restrictions_in_batch(client):
    """Test: Policy guardrails (counterfeit risk, lithium battery hazard) are never given repair slots."""
    client.post("/demo/seed")
    opt = client.post("/optimize", json={"repair_capacity_slots": 4}).json()

    # Find the synthetic counterfeit and swollen battery items
    counterfeit = next(a for a in opt["allocations"] if "Counterfeit" in a["product_name"])
    swollen_battery = next(a for a in opt["allocations"] if "Swollen" in a["product_name"])

    assert counterfeit["manual_review_required"] is True
    assert counterfeit["assigned_route"] == "manual_assessment"
    assert counterfeit["was_repair_selected"] is False

    assert swollen_battery["manual_review_required"] is True
    assert swollen_battery["assigned_route"] == "manual_assessment"
    assert swollen_battery["was_repair_selected"] is False


def test_baseline_comparisons_and_positive_uplift(client):
    """Test: Optimized allocation beats FIFO and cheapest-repair baselines with calculated positive uplift."""
    client.post("/demo/seed")
    opt = client.post("/optimize", json={"repair_capacity_slots": 4}).json()

    # Optimized must be >= FIFO baseline
    assert opt["optimized_total_net_recovery"] >= opt["baseline_fifo_net_recovery"]
    assert opt["dollar_uplift_vs_fifo"] >= 0.0

    # Optimized must be >= Cheapest Repair baseline
    assert opt["optimized_total_net_recovery"] >= opt["baseline_cheapest_repair_net_recovery"]
    assert opt["dollar_uplift_vs_cheapest"] >= 0.0

    # Unconstrained upper bound must be >= capacity-constrained optimization
    assert opt["baseline_unconstrained_net_recovery"] >= opt["optimized_total_net_recovery"]


def test_reproducibility_of_optimizer(client):
    """Test: Optimizer is fully deterministic and produces identical results on identical input."""
    client.post("/demo/seed")
    run1 = client.post("/optimize", json={"repair_capacity_slots": 4}).json()
    run2 = client.post("/optimize", json={"repair_capacity_slots": 4}).json()

    assert run1["optimized_total_net_recovery"] == run2["optimized_total_net_recovery"]
    assert run1["repair_slots_used"] == run2["repair_slots_used"]
    assert [a["assigned_route"] for a in run1["allocations"]] == [a["assigned_route"] for a in run2["allocations"]]
