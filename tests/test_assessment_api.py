#!/usr/bin/env python3
"""
Unit and integration tests for Person 2's Return Assessment API (app.py).
Tests all validation rules, condition checks, defect handling, date boundaries,
and successful response generation.
"""

import unittest
import json
import datetime
from app import app


class TestAssessmentAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        today_str = datetime.date.today().isoformat()
        future_str = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        past_str = (datetime.date.today() - datetime.timedelta(days=180)).isoformat()
        self.today_str = today_str
        self.future_str = future_str
        self.past_str = past_str

        self.valid_payload = {
            "productId": "SKU-9941-PRO",
            "productName": "UltraView OLED 65-inch 4K Smart TV",
            "category": "Consumer Electronics",
            "condition": "Used",
            "defectCategory": "Battery issue",
            "defectDescription": "Remote battery terminals corroded, rapid discharge on unit.",
            "visibleDamage": False,
            "damageImage": None,
            "warrantyStatus": "In warranty",
            "purchaseDate": past_str,
            "warrantyExpiryDate": future_str,
            "proofOfPurchase": "INV-2025-4819"
        }

    def test_health_endpoint(self):
        res = self.app.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")

    def test_successful_assessment_submission(self):
        res = self.app.post("/assessment", json=self.valid_payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["assessmentId"].startswith("ASM-"))
        self.assertFalse(data["isMock"])
        self.assertIn("preliminaryDisposition", data)
        self.assertIn("route", data["preliminaryDisposition"])

    def test_missing_required_product_fields(self):
        payload = dict(self.valid_payload)
        payload["productId"] = "   "
        payload["category"] = ""
        payload["condition"] = ""

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("productId", data["errors"])
        self.assertIn("category", data["errors"])
        self.assertIn("condition", data["errors"])

    def test_future_purchase_date_fails(self):
        payload = dict(self.valid_payload)
        payload["purchaseDate"] = self.future_str

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("purchaseDate", data["errors"])

    def test_warranty_expiry_before_purchase_date_fails(self):
        payload = dict(self.valid_payload)
        payload["purchaseDate"] = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        payload["warrantyExpiryDate"] = (datetime.date.today() - datetime.timedelta(days=50)).isoformat()

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("warrantyExpiryDate", data["errors"])

    def test_damaged_condition_requires_defect_details(self):
        payload = dict(self.valid_payload)
        payload["condition"] = "Damaged"
        payload["defectCategory"] = "No defect"
        payload["defectDescription"] = ""

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("defectCategory", data["errors"])
        self.assertIn("defectDescription", data["errors"])

    def test_other_defect_requires_description(self):
        payload = dict(self.valid_payload)
        payload["defectCategory"] = "Other"
        payload["defectDescription"] = "   "

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("defectDescription", data["errors"])

    def test_new_unopened_disposition_heuristic(self):
        payload = dict(self.valid_payload)
        payload["condition"] = "New / unopened"
        payload["defectCategory"] = "No defect"
        payload["defectDescription"] = ""

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["preliminaryDisposition"]["route"], "RESTOCK_AS_NEW")

    def test_non_functional_liquid_damage_heuristic(self):
        payload = dict(self.valid_payload)
        payload["condition"] = "Non-functional"
        payload["defectCategory"] = "Liquid damage"
        payload["defectDescription"] = "Submerged in pool, logic board shorted."

        res = self.app.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["preliminaryDisposition"]["route"], "PARTS_HARVEST_OR_RECYCLE")


if __name__ == "__main__":
    unittest.main()
