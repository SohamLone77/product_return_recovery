#!/usr/bin/env python3
"""
End-to-End and Integration Tests for Return Assessment Module.
Verifies all static assets, HTML element IDs, schema validations,
date boundaries, and recovery heuristics.
"""

import unittest
import json
import datetime
from app import app


class TestEndToEndAssessmentFlow(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.today = datetime.date.today()
        self.past_date = (self.today - datetime.timedelta(days=90)).isoformat()
        self.future_date = (self.today + datetime.timedelta(days=15)).isoformat()

    def test_static_assets_and_entry_point(self):
        """Verify HTML entry point, stylesheets, and JavaScript files serve 200 OK."""
        with self.client.get("/") as res:
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)
            self.assertIn("Intelligent Product Returns", html)
            self.assertIn("btnStartNewReturn", html)
            self.assertIn("returnAssessmentForm", html)
            self.assertIn("inputProductId", html)
            self.assertIn("selectCategory", html)
            self.assertIn("textareaDefectDesc", html)
            self.assertIn("inputPurchaseDate", html)
            self.assertIn("btnWizardSubmit", html)

        # Check CSS
        with self.client.get("/css/main.css") as res_css:
            self.assertEqual(res_css.status_code, 200)
        with self.client.get("/css/assessment.css") as res_asm_css:
            self.assertEqual(res_asm_css.status_code, 200)

        # Check JS
        with self.client.get("/js/api/assessmentApi.js") as res_api_js:
            self.assertEqual(res_api_js.status_code, 200)
            self.assertIn("MockAssessmentService", res_api_js.get_data(as_text=True))
            self.assertIn("AssessmentApiClient", res_api_js.get_data(as_text=True))

    def test_workflow_new_unopened_electronics(self):
        """Happy path: New unopened item -> RESTOCK_AS_NEW route."""
        payload = {
            "productId": "PRD-M3-PRO-01",
            "productName": "Apple MacBook Pro 14 M3",
            "category": "Computing & Laptops",
            "condition": "New / unopened",
            "defectCategory": "No defect",
            "defectDescription": "",
            "visibleDamage": False,
            "damageImage": None,
            "warrantyStatus": "In warranty",
            "purchaseDate": self.past_date,
            "warrantyExpiryDate": self.future_date,
            "proofOfPurchase": "INV-APPLE-0091"
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["assessmentId"].startswith("ASM-"))
        self.assertEqual(data["preliminaryDisposition"]["route"], "RESTOCK_AS_NEW")
        self.assertGreaterEqual(data["preliminaryDisposition"]["estimatedRecoveryRatio"], 0.90)

    def test_workflow_damaged_screen_with_image(self):
        """Damaged screen with base64 image -> IN_HOUSE_REFURBISH route."""
        payload = {
            "productId": "PRD-GALAXY-S24",
            "productName": "Samsung Galaxy S24 Ultra",
            "category": "Smartphones & Tablets",
            "condition": "Damaged",
            "defectCategory": "Display or screen damage",
            "defectDescription": "Digitizer glass cracked across top corner.",
            "visibleDamage": True,
            "damageImage": {
                "fileName": "front_crack.png",
                "fileSize": 102400,
                "contentType": "image/png",
                "dataUrl": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            },
            "warrantyStatus": "Expired",
            "purchaseDate": "2023-01-15",
            "warrantyExpiryDate": "2024-01-15",
            "proofOfPurchase": "INV-SAMS-9921"
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["preliminaryDisposition"]["route"], "IN_HOUSE_REFURBISH")
        self.assertTrue(data["defect"]["hasAttachedImage"])

    def test_workflow_liquid_damage_recycle(self):
        """Liquid damage -> voids warranty, routes to PARTS_HARVEST_OR_RECYCLE."""
        payload = {
            "productId": "PRD-DYSON-V12",
            "productName": "Dyson V12 Detect Slim",
            "category": "Home Appliances",
            "condition": "Non-functional",
            "defectCategory": "Liquid damage",
            "defectDescription": "Water intake through motor chamber during cleaning.",
            "visibleDamage": True,
            "warrantyStatus": "In warranty",
            "purchaseDate": self.past_date,
            "warrantyExpiryDate": self.future_date,
            "proofOfPurchase": "INV-DYS-8821"
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["preliminaryDisposition"]["route"], "PARTS_HARVEST_OR_RECYCLE")
        self.assertEqual(data["preliminaryDisposition"]["estimatedRecoveryRatio"], 0.20)

    def test_validation_missing_defect_description_on_other(self):
        """Selecting 'Other' defect requires explanatory description."""
        payload = {
            "productId": "PRD-OTHER-TEST",
            "category": "Other",
            "condition": "Used",
            "defectCategory": "Other",
            "defectDescription": "   ",
            "visibleDamage": False,
            "warrantyStatus": "Unknown",
            "purchaseDate": self.past_date
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("defectDescription", data["errors"])

    def test_validation_damaged_product_rejects_no_defect(self):
        """A damaged item cannot claim 'No defect'."""
        payload = {
            "productId": "PRD-DAMAGED-TEST",
            "category": "Consumer Electronics",
            "condition": "Damaged",
            "defectCategory": "No defect",
            "defectDescription": "Minor scratch",
            "visibleDamage": True,
            "warrantyStatus": "Unknown",
            "purchaseDate": self.past_date
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("defectCategory", data["errors"])

    def test_validation_future_date_boundary(self):
        """Future purchase date is rejected with ISO date message."""
        payload = {
            "productId": "PRD-FUTURE-TEST",
            "category": "Consumer Electronics",
            "condition": "Used",
            "defectCategory": "Battery issue",
            "defectDescription": "Battery drain",
            "visibleDamage": False,
            "warrantyStatus": "In warranty",
            "purchaseDate": (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("purchaseDate", data["errors"])
        self.assertIn("cannot be in the future", data["errors"]["purchaseDate"])

    def test_validation_expiry_precedes_purchase(self):
        """Warranty expiry earlier than purchase date is rejected."""
        payload = {
            "productId": "PRD-DATE-TEST",
            "category": "Consumer Electronics",
            "condition": "Used",
            "defectCategory": "Battery issue",
            "defectDescription": "Battery drain",
            "visibleDamage": False,
            "warrantyStatus": "In warranty",
            "purchaseDate": "2025-06-01",
            "warrantyExpiryDate": "2025-05-31"
        }
        res = self.client.post("/assessment", json=payload)
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn("warrantyExpiryDate", data["errors"])


if __name__ == "__main__":
    unittest.main()
