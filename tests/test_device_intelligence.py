#!/usr/bin/env python3
"""
Tests for Device Intelligence & Return Assessment Engine (feature/device-assessment).

Tests cover:
- All 10 demo return record fixtures
- Authenticity screening: genuine, suspicious, counterfeit, unknown
- Condition scoring: powered-off, liquid damage, screen damage, motherboard failure
- Warranty verification: eligible, not eligible, pending, exclusions
- Full device assessment endpoint: validation, score fields, evidence, disposition
- API failures and missing data
"""

import unittest
import json
import datetime
from app import app, _build_demo_returns, _run_authenticity_check, _run_condition_score, _run_warranty_verification


class TestDemoReturnFixtures(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_demo_returns_endpoint_returns_10_records(self):
        r = self.client.get("/api/device-assessment/returns")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["count"], 10)
        self.assertIsInstance(data["returns"], list)

    def test_all_demo_returns_have_required_fields(self):
        returns = _build_demo_returns()
        for rid, rec in returns.items():
            with self.subTest(return_id=rid):
                self.assertIn("returnId", rec)
                self.assertIn("label", rec)
                self.assertIn("category", rec)
                self.assertIn("manufacturer", rec)

    def test_demo_return_by_id(self):
        r = self.client.get("/api/device-assessment/returns/RET-DEMO-001")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["return"]["returnId"], "RET-DEMO-001")

    def test_demo_return_missing_id_returns_404(self):
        r = self.client.get("/api/device-assessment/returns/RET-DOES-NOT-EXIST")
        self.assertEqual(r.status_code, 404)

    def test_demo_returns_cover_all_scenario_types(self):
        returns = list(_build_demo_returns().values())
        labels = " ".join(r.get("label", "") for r in returns)
        self.assertIn("GENUINE", labels)
        self.assertIn("SUSPICIOUS", labels)
        self.assertIn("COUNTERFEIT", labels)
        self.assertIn("UNKNOWN", labels)


class TestAuthenticityScreening(unittest.TestCase):
    """Feature A — Authenticity risk detection"""

    def test_likely_genuine_clean_device(self):
        result = _run_authenticity_check({
            "serialNumber": "F7KNXQR4T1M3",
            "imei": "358142094521063",
            "invoiceAvailable": True,
            "sellerChannel": "Apple Store",
            "tamperSealsIntact": True,
            "labelInconsistency": False,
            "category": "Smartphones & Tablets",
            "claimedPurchasePrice": 134900
        })
        self.assertEqual(result["authenticity_status"], "likely_genuine")
        self.assertLess(result["authenticity_risk_score"], 15)
        self.assertIn("assessment_method", result)
        self.assertIn("disclaimer", result)

    def test_suspicious_tamper_seals_broken(self):
        result = _run_authenticity_check({
            "serialNumber": "ABC123",
            "invoiceAvailable": False,
            "tamperSealsIntact": False,
            "labelInconsistency": True,
            "sellerChannel": "street market",
            "category": "Smartphones & Tablets",
            "claimedPurchasePrice": 28000
        })
        self.assertIn(result["authenticity_status"], ["suspicious", "likely_counterfeit"])
        self.assertGreater(result["authenticity_risk_score"], 25)

    def test_likely_counterfeit_serial_mismatch_low_price(self):
        result = _run_authenticity_check({
            "serialNumber": "FAKE123456",
            "imei": "0000000000",
            "invoiceAvailable": False,
            "tamperSealsIntact": False,
            "labelInconsistency": True,
            "serialOnLabel": "FAKE123456",
            "serialOnDevice": "DIFFERENT99",
            "sellerChannel": "unknown vendor",
            "category": "Smartphones & Tablets",
            "claimedPurchasePrice": 8000
        })
        self.assertEqual(result["authenticity_status"], "likely_counterfeit")
        self.assertGreaterEqual(result["authenticity_risk_score"], 55)

    def test_unknown_when_no_serial_no_invoice(self):
        result = _run_authenticity_check({
            "serialNumber": "",
            "imei": "",
            "invoiceAvailable": False
        })
        self.assertEqual(result["authenticity_status"], "unknown")
        self.assertIn("missing_evidence", result)
        self.assertGreater(len(result["missing_evidence"]), 0)

    def test_invalid_imei_raises_risk(self):
        result = _run_authenticity_check({
            "imei": "0000000000",
            "invoiceAvailable": True
        })
        self.assertGreater(result["authenticity_risk_score"], 5)

    def test_action_proceed_for_genuine(self):
        result = _run_authenticity_check({
            "serialNumber": "VALID123",
            "imei": "358142094521063",
            "invoiceAvailable": True,
            "sellerChannel": "Croma",
            "tamperSealsIntact": True,
            "claimedPurchasePrice": 50000
        })
        if result["authenticity_status"] == "likely_genuine":
            self.assertEqual(result["recommended_action"], "proceed")

    def test_disclaimer_always_present(self):
        result = _run_authenticity_check({})
        self.assertIn("disclaimer", result)
        self.assertIn("manufacturer", result["disclaimer"].lower())


class TestConditionScoring(unittest.TestCase):
    """Feature B — Condition & repairability scoring"""

    def test_perfect_device_high_score(self):
        result = _run_condition_score({
            "powersOn": True,
            "screenCondition": "Perfect - no scratches",
            "bodyCondition": "Like new",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "images": ["front.jpg", "back.jpg"]
        })
        self.assertGreaterEqual(result["condition_score"], 90)
        self.assertGreaterEqual(result["repairability_score"], 85)
        self.assertGreater(result["confidence_score"], 55)

    def test_liquid_damage_reduces_score_significantly(self):
        result = _run_condition_score({
            "powersOn": False,
            "screenCondition": "Not applicable",
            "bodyCondition": "Significant physical damage",
            "liquidDamage": True,
            "impactDamage": False
        })
        self.assertLess(result["condition_score"], 50)
        self.assertLess(result["repairability_score"], 50)
        self.assertTrue(any("liquid" in d.lower() for d in result["observed_defects"]))

    def test_motherboard_issue_drops_repairability(self):
        result = _run_condition_score({"motherboardIssue": True, "powersOn": False})
        self.assertLess(result["repairability_score"], 60)
        self.assertTrue(any("motherboard" in d.lower() for d in result["observed_defects"]))

    def test_no_images_lowers_confidence(self):
        result_no_img = _run_condition_score({"powersOn": True, "images": []})
        result_with_img = _run_condition_score({"powersOn": True, "images": ["a.jpg", "b.jpg", "c.jpg"]})
        self.assertLess(result_no_img["confidence_score"], result_with_img["confidence_score"])

    def test_powers_on_unknown_adds_limitation(self):
        result = _run_condition_score({"powersOn": None})
        self.assertTrue(any("unknown" in l.lower() for l in result["limitations"]))

    def test_shattered_screen_score_decrease(self):
        result = _run_condition_score({"screenCondition": "Completely shattered", "powersOn": True})
        self.assertLess(result["condition_score"], 60)

    def test_assessment_method_label_present(self):
        result = _run_condition_score({})
        self.assertEqual(result["assessment_method"], "HEURISTIC_BASELINE_NO_CV_MODEL")
        self.assertIn("disclaimer", result)


class TestWarrantyVerification(unittest.TestCase):
    """Feature D — Warranty entitlement verification"""

    def test_eligible_clean_case(self):
        today = datetime.date.today()
        purchase_date = (today - datetime.timedelta(days=60)).isoformat()
        result = _run_warranty_verification({
            "category": "Smartphones & Tablets",
            "purchaseDate": purchase_date,
            "returnDate": today.isoformat(),
            "warrantyClaimed": True,
            "invoiceAvailable": True,
            "serialNumber": "VALID123",
            "liquidDamage": False,
            "impactDamage": False,
            "tamperingEvidence": False
        })
        self.assertEqual(result["warranty_status"], "eligible")

    def test_not_eligible_warranty_not_claimed(self):
        purchase_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        result = _run_warranty_verification({
            "category": "Audio & Wearables",
            "purchaseDate": purchase_date,
            "warrantyClaimed": False,
            "invoiceAvailable": True
        })
        self.assertEqual(result["warranty_status"], "not_eligible")

    def test_not_eligible_expired_warranty(self):
        old_purchase = (datetime.date.today() - datetime.timedelta(days=400)).isoformat()
        result = _run_warranty_verification({
            "category": "Smartphones & Tablets",
            "purchaseDate": old_purchase,
            "warrantyClaimed": True,
            "invoiceAvailable": True,
            "liquidDamage": False,
            "tamperingEvidence": False
        })
        self.assertEqual(result["warranty_status"], "not_eligible")
        self.assertIn("outside coverage", result["eligibility_reason"])

    def test_not_eligible_liquid_damage_exclusion(self):
        purchase_date = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
        result = _run_warranty_verification({
            "category": "Audio & Wearables",
            "purchaseDate": purchase_date,
            "warrantyClaimed": True,
            "invoiceAvailable": True,
            "liquidDamage": True
        })
        self.assertIn(result["warranty_status"], ["not_eligible"])
        self.assertGreater(len(result["exclusion_reasons"]), 0)

    def test_pending_verification_no_invoice(self):
        purchase_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        result = _run_warranty_verification({
            "category": "Gaming Consoles",
            "purchaseDate": purchase_date,
            "warrantyClaimed": True,
            "invoiceAvailable": False,
            "serialNumber": ""
        })
        self.assertEqual(result["warranty_status"], "pending_verification")

    def test_insufficient_information_no_purchase_date(self):
        result = _run_warranty_verification({
            "category": "Laptops & Computers",
            "purchaseDate": "",
            "warrantyClaimed": True
        })
        self.assertEqual(result["warranty_status"], "insufficient_information")

    def test_disclaimer_always_present(self):
        result = _run_warranty_verification({})
        self.assertIn("disclaimer", result)
        self.assertIn("fraud", result["disclaimer"].lower())

    def test_out_of_warranty_cost_always_returned(self):
        result = _run_warranty_verification({
            "category": "Smartphones & Tablets",
            "warrantyClaimed": False
        })
        self.assertIsNotNone(result["estimated_out_of_warranty_repair_cost_inr"])


class TestFullDeviceAssessmentEndpoint(unittest.TestCase):
    """End-to-end API tests"""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        today = datetime.date.today()
        self.valid_payload = {
            "returnId": "RET-TEST-001",
            "category": "Smartphones & Tablets",
            "manufacturer": "Apple",
            "model": "iPhone 15 Pro",
            "serialNumber": "F7KNXQR4T1M3",
            "imei": "358142094521063",
            "purchaseDate": (today - datetime.timedelta(days=60)).isoformat(),
            "returnDate": today.isoformat(),
            "sellerChannel": "Apple Store",
            "claimedPurchasePrice": 134900,
            "invoiceAvailable": True,
            "warrantyClaimed": True,
            "powersOn": True,
            "screenCondition": "Perfect - no scratches",
            "bodyCondition": "Like new",
            "liquidDamage": False,
            "impactDamage": False,
            "missingComponents": False,
            "tamperingEvidence": False,
            "tamperSealsIntact": True,
            "batteryIssue": False,
            "images": ["front.jpg", "back.jpg"]
        }

    def test_full_assessment_returns_all_required_fields(self):
        r = self.client.post("/api/device-assessment", json=self.valid_payload)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        self.assertEqual(d["status"], "success")
        for field in [
            "assessmentId", "returnId", "conditionScore", "repairabilityScore",
            "confidenceScore", "authenticityStatus", "authenticityRiskScore",
            "warrantyStatus", "observedDefects", "estimatedRepairCost",
            "estimatedResaleValue", "evidence", "manualReviewRequired",
            "assessmentTimestamp", "preliminaryDisposition"
        ]:
            with self.subTest(field=field):
                self.assertIn(field, d)

    def test_missing_return_id_returns_422(self):
        payload = dict(self.valid_payload)
        payload["returnId"] = ""
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 422)
        self.assertIn("returnId", r.get_json()["errors"])

    def test_missing_category_returns_422(self):
        payload = dict(self.valid_payload)
        payload["category"] = ""
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 422)

    def test_future_purchase_date_returns_422(self):
        payload = dict(self.valid_payload)
        payload["purchaseDate"] = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 422)

    def test_assessment_is_stored_and_retrievable(self):
        r = self.client.post("/api/device-assessment", json=self.valid_payload)
        self.assertEqual(r.status_code, 201)
        assessment_id = r.get_json()["assessmentId"]
        r2 = self.client.get(f"/api/device-assessment/{assessment_id}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json()["assessment"]["assessmentId"], assessment_id)

    def test_unknown_assessment_id_returns_404(self):
        r = self.client.get("/api/device-assessment/NONEXISTENT-ID-99")
        self.assertEqual(r.status_code, 404)

    def test_suspicious_device_sets_manual_review(self):
        payload = dict(self.valid_payload)
        payload["labelInconsistency"] = True
        payload["tamperSealsIntact"] = False
        payload["invoiceAvailable"] = False
        payload["sellerChannel"] = "street market"
        payload["claimedPurchasePrice"] = 5000
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        self.assertTrue(d["manualReviewRequired"])
        self.assertGreater(len(d["manualReviewReasons"]), 0)

    def test_liquid_damage_routes_to_recycle(self):
        payload = dict(self.valid_payload)
        payload["liquidDamage"] = True
        payload["powersOn"] = False
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        self.assertIn(d["preliminaryDisposition"],
                      ["RECYCLE_OR_SCRAP", "SECONDARY_MARKET_PARTS", "MANUAL_REVIEW"])

    def test_new_sealed_device_routes_to_restock(self):
        payload = dict(self.valid_payload)
        payload["screenCondition"] = "Perfect - no scratches"
        payload["bodyCondition"] = "Like new"
        payload["powersOn"] = True
        payload["liquidDamage"] = False
        payload["impactDamage"] = False
        payload["tamperSealsIntact"] = True
        payload["batteryIssue"] = False
        r = self.client.post("/api/device-assessment", json=payload)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        self.assertIn(d["preliminaryDisposition"],
                      ["RESTOCK_AS_NEW", "OPEN_BOX_RESALE", "WARRANTY_OEM_REPAIR"])

    def test_health_endpoint_shows_v2(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("device-intelligence", d.get("modules", []))

    def test_standalone_authenticity_endpoint(self):
        r = self.client.post("/api/device-assessment/authenticity",
                             json={"serialNumber": "ABC", "invoiceAvailable": True,
                                   "tamperSealsIntact": True})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("authenticity_status", d["result"])

    def test_standalone_condition_endpoint(self):
        r = self.client.post("/api/device-assessment/condition",
                             json={"powersOn": True, "liquidDamage": False,
                                   "screenCondition": "Like new"})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("condition_score", d["result"])

    def test_standalone_warranty_endpoint(self):
        purchase_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        r = self.client.post("/api/device-assessment/warranty",
                             json={"category": "Audio & Wearables",
                                   "purchaseDate": purchase_date,
                                   "warrantyClaimed": True,
                                   "invoiceAvailable": True,
                                   "liquidDamage": False})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn("warranty_status", d["result"])

    def test_device_assessment_page_route(self):
        with self.client.get("/device-assessment") as r:
            self.assertEqual(r.status_code, 200)
            self.assertIn("Device Intelligence &amp; Return Assessment", r.get_data(as_text=True))

    def test_shared_contract_has_both_case_conventions(self):
        r = self.client.post("/api/device-assessment", json=self.valid_payload)
        self.assertEqual(r.status_code, 201)
        d = r.get_json()
        # Verify required snake_case contract fields
        for field in [
            "return_id", "assessment_id", "condition_score", "repairability_score",
            "confidence_score", "authenticity_status", "authenticity_risk_score",
            "warranty_status", "observed_defects", "estimated_repair_cost",
            "estimated_repair_hours", "estimated_resale_value", "estimated_parts_value",
            "evidence", "manual_review_required", "manual_review_reasons", "assessment_timestamp"
        ]:
            with self.subTest(snake_case_field=field):
                self.assertIn(field, d)
        # Verify linking to return_id
        self.assertEqual(d["return_id"], self.valid_payload["returnId"])
        self.assertEqual(d["returnId"], self.valid_payload["returnId"])

    def test_conflicting_warranty_evidence_triggers_review(self):
        """Impact damage without liquid damage triggers manual_review in policy."""
        purchase_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        r = self.client.post("/api/device-assessment/warranty",
                             json={"category": "Smartphones & Tablets",
                                   "purchaseDate": purchase_date,
                                   "warrantyClaimed": True,
                                   "invoiceAvailable": True,
                                   "impactDamage": True,
                                   "liquidDamage": False})
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d["result"]["warranty_status"], "manual_review")

    def test_empty_json_body_returns_400(self):
        r = self.client.post("/api/device-assessment", data="invalid-non-json", content_type="application/json")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
