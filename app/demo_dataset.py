import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import ReturnRecord, AssessmentRecord

DEMO_DEVICES_SPEC = [
    {
        "product_id": "SYNTH-PHONE-15PRO",
        "product_name": "[Synthetic Demo] Flagship Smartphone 15 Pro (256GB)",
        "category": "Electronics",
        "purchase_price": 1100.0,
        "customer_id": "CUST-DEMO-01",
        "order_id": "ORD-SYNTH-101",
        "return_reason": "Cracked OLED display from minor drop; touch partially responsive",
        "assessment": {
            "product_condition": "minor_damage",
            "defect_category": "functional",
            "defect_description": "Front glass cracked, OLED panel damaged, motherboard and battery healthy.",
            "visible_damage": True,
            "warranty_status": "expired",
            "verified_warranty_eligible": False,
            "repair_probability": 0.95,
            "estimated_repair_cost": 120.0,
            "estimated_repair_hours": 1.5,
            "potential_resale_value": 850.0,
            "parts_recovery_value": 280.0,
            "authenticity_risk": 0.05,
            "safety_hazard": False,
            "fraud_risk_score": 0.05,
            "assessor_notes": "Clean logic board, genuine Apple hardware. Strong repair candidate.",
        }
    },
    {
        "product_id": "SYNTH-LAPTOP-RTX4080",
        "product_name": "[Synthetic Demo] Ultra Gaming Laptop 16 (RTX 4080, 32GB RAM)",
        "category": "Computers",
        "purchase_price": 2200.0,
        "customer_id": "CUST-DEMO-02",
        "order_id": "ORD-SYNTH-102",
        "return_reason": "Device will not power on; charging LED blinks once",
        "assessment": {
            "product_condition": "defective",
            "defect_category": "electrical",
            "defect_description": "Blown surface-mount capacitor on primary 19V rail; GPU/CPU silicon intact.",
            "visible_damage": False,
            "warranty_status": "expired",
            "verified_warranty_eligible": False,
            "repair_probability": 0.90,
            "estimated_repair_cost": 160.0,
            "estimated_repair_hours": 2.5,
            "potential_resale_value": 1650.0,
            "parts_recovery_value": 550.0,
            "authenticity_risk": 0.02,
            "safety_hazard": False,
            "fraud_risk_score": 0.05,
            "assessor_notes": "High residual market value. Component micro-soldering delivers massive recovery.",
        }
    },
    {
        "product_id": "SYNTH-TABLET-PRO13",
        "product_name": "[Synthetic Demo] Professional Creator Tablet 13-inch",
        "category": "Electronics",
        "purchase_price": 950.0,
        "customer_id": "CUST-DEMO-03",
        "order_id": "ORD-SYNTH-103",
        "return_reason": "Battery drops from 50% to 0% suddenly during use",
        "assessment": {
            "product_condition": "minor_damage",
            "defect_category": "functional",
            "defect_description": "Degraded battery cells; screen and enclosure in pristine condition.",
            "visible_damage": False,
            "warranty_status": "expired",
            "verified_warranty_eligible": False,
            "repair_probability": 0.92,
            "estimated_repair_cost": 85.0,
            "estimated_repair_hours": 1.0,
            "potential_resale_value": 720.0,
            "parts_recovery_value": 220.0,
            "authenticity_risk": 0.03,
            "safety_hazard": False,
            "fraud_risk_score": 0.04,
            "assessor_notes": "Simple battery pack swap restores device to Grade A resale condition.",
        }
    },
    {
        "product_id": "SYNTH-OLEDTV-65",
        "product_name": "[Synthetic Demo] 65-inch Smart 4K OLED Cinema TV",
        "category": "Electronics",
        "purchase_price": 1400.0,
        "customer_id": "CUST-DEMO-04",
        "order_id": "ORD-SYNTH-104",
        "return_reason": "Vertical colored lines on left side of screen",
        "assessment": {
            "product_condition": "minor_damage",
            "defect_category": "functional",
            "defect_description": "Loose T-Con LVDS ribbon cable; OLED panel itself is undamaged.",
            "visible_damage": False,
            "warranty_status": "expired",
            "verified_warranty_eligible": False,
            "repair_probability": 0.88,
            "estimated_repair_cost": 95.0,
            "estimated_repair_hours": 1.5,
            "potential_resale_value": 920.0,
            "parts_recovery_value": 310.0,
            "authenticity_risk": 0.01,
            "safety_hazard": False,
            "fraud_risk_score": 0.02,
            "assessor_notes": "High positive repair incremental benefit; secondary as-is sale would forfeit significant margin.",
        }
    },
    {
        "product_id": "SYNTH-BUDGET-A12",
        "product_name": "[Synthetic Demo] Entry-Level Budget Smartphone A12",
        "category": "Electronics",
        "purchase_price": 160.0,
        "customer_id": "CUST-DEMO-05",
        "order_id": "ORD-SYNTH-105",
        "return_reason": "Device dropped in sink; screen flickers and power button sticks",
        "assessment": {
            "product_condition": "defective",
            "defect_category": "electrical",
            "defect_description": "Extensive corrosion across logic board; liquid contact indicators red.",
            "visible_damage": True,
            "warranty_status": "none",
            "verified_warranty_eligible": False,
            "repair_probability": 0.35,  # Low success probability!
            "estimated_repair_cost": 75.0,  # Repair exceeds economic feasibility!
            "estimated_repair_hours": 2.0,
            "potential_resale_value": 85.0,
            "parts_recovery_value": 20.0,
            "authenticity_risk": 0.02,
            "safety_hazard": False,
            "fraud_risk_score": 0.05,
            "assessor_notes": "Repair economically unattractive. Parts harvest or recycle far superior to wasting bench time.",
        }
    },
    {
        "product_id": "SYNTH-WATCH-ACT5",
        "product_name": "[Synthetic Demo] Smartwatch Active 5 (Cellular, 44mm)",
        "category": "Electronics",
        "purchase_price": 320.0,
        "customer_id": "CUST-DEMO-06",
        "order_id": "ORD-SYNTH-106",
        "return_reason": "Customer dissatisfied with color; micro-abrasions on aluminum bezel",
        "assessment": {
            "product_condition": "like_new",
            "defect_category": "cosmetic",
            "defect_description": "Minor surface scuff on outer bezel; display, sensor suite, and battery 100% operational.",
            "visible_damage": False,
            "warranty_status": "active",
            "verified_warranty_eligible": False,
            "repair_probability": 1.0,
            "estimated_repair_cost": 85.0,
            "estimated_repair_hours": 1.0,
            "potential_resale_value": 240.0,
            "parts_recovery_value": 70.0,
            "authenticity_risk": 0.02,
            "safety_hazard": False,
            "fraud_risk_score": 0.02,
            "assessor_notes": "Refurbishment and repackaging strictly beats repair, freeing a bench slot for complex hardware.",
        }
    },
    {
        "product_id": "SYNTH-TOWER-CUSTOM",
        "product_name": "[Synthetic Demo] High-Performance Tower PC (Crushed Chassis)",
        "category": "Computers",
        "purchase_price": 1800.0,
        "customer_id": "CUST-DEMO-07",
        "order_id": "ORD-SYNTH-107",
        "return_reason": "Severe in-transit structural shock; metal case dented and tempered glass shattered",
        "assessment": {
            "product_condition": "major_damage",
            "defect_category": "functional",
            "defect_description": "Chassis crushed beyond repair; motherboard cracked. RTX 4070 GPU, 64GB RAM, and 2TB NVMe SSD tested undamaged.",
            "visible_damage": True,
            "warranty_status": "none",
            "verified_warranty_eligible": False,
            "repair_probability": 0.10,
            "estimated_repair_cost": 900.0,
            "estimated_repair_hours": 4.0,
            "potential_resale_value": 1100.0,
            "parts_recovery_value": 580.0,  # High reusable component salvage value!
            "authenticity_risk": 0.02,
            "safety_hazard": False,
            "fraud_risk_score": 0.03,
            "assessor_notes": "Parts harvesting captures $580 in modular components, vastly outperforming material recycling ($15).",
        }
    },
    {
        "product_id": "SYNTH-HUB-SMARTHOME",
        "product_name": "[Synthetic Demo] Smart Home Automation Hub Pro",
        "category": "Electronics",
        "purchase_price": 260.0,
        "customer_id": "CUST-DEMO-08",
        "order_id": "ORD-SYNTH-108",
        "return_reason": "Zigbee radio module unresponsive on boot",
        "assessment": {
            "product_condition": "defective",
            "defect_category": "electrical",
            "defect_description": "Factory defect in internal radio IC; verified invoice within 1-year manufacturer warranty.",
            "visible_damage": False,
            "warranty_status": "active",
            "verified_warranty_eligible": True,  # Verified manufacturer warranty!
            "repair_probability": 0.70,
            "estimated_repair_cost": 80.0,
            "estimated_repair_hours": 1.2,
            "potential_resale_value": 170.0,
            "parts_recovery_value": 45.0,
            "authenticity_risk": 0.01,
            "safety_hazard": False,
            "fraud_risk_score": 0.02,
            "assessor_notes": "Verified manufacturer warranty allows full supplier credit ($234). Return to Supplier saves internal repair costs.",
        }
    },
    {
        "product_id": "SYNTH-EARBUDS-SUSPECT",
        "product_name": "[Synthetic Demo] ANC Wireless Earbuds Pro (Counterfeit Suspect)",
        "category": "Accessories",
        "purchase_price": 280.0,
        "customer_id": "CUST-DEMO-09",
        "order_id": "ORD-SYNTH-109",
        "return_reason": "Sound quality muffled; packaging seal looks altered",
        "assessment": {
            "product_condition": "like_new",
            "defect_category": "none",
            "defect_description": "Serial number does not match factory database; charging case weight is 12g lighter than OEM.",
            "visible_damage": False,
            "warranty_status": "none",
            "verified_warranty_eligible": False,
            "repair_probability": 0.0,
            "estimated_repair_cost": 0.0,
            "estimated_repair_hours": 0.0,
            "potential_resale_value": 0.0,
            "parts_recovery_value": 0.0,
            "authenticity_risk": 0.94,  # High counterfeit score!
            "safety_hazard": False,
            "fraud_risk_score": 0.92,
            "fraud_flags": ["COUNTERFEIT_SUSPECTED", "SERIAL_MISMATCH"],
            "assessor_notes": "POLICY GUARDRAIL: Automated repair and resale prohibited. Flagged for legal and authenticity review.",
        }
    },
    {
        "product_id": "SYNTH-ULTRABOOK-SWELL",
        "product_name": "[Synthetic Demo] Ultra-Slim Laptop 14 (Swollen Lithium Cell)",
        "category": "Computers",
        "purchase_price": 950.0,
        "customer_id": "CUST-DEMO-10",
        "order_id": "ORD-SYNTH-110",
        "return_reason": "Trackpad will not click; bottom metal chassis is visibly bowing outward",
        "assessment": {
            "product_condition": "major_damage",
            "defect_category": "functional",
            "defect_description": "Lithium-ion polymer battery cell has swollen significantly, pushing trackpad up.",
            "visible_damage": True,
            "warranty_status": "expired",
            "verified_warranty_eligible": False,
            "repair_probability": 0.80,
            "estimated_repair_cost": 110.0,
            "estimated_repair_hours": 1.5,
            "potential_resale_value": 650.0,
            "parts_recovery_value": 200.0,
            "authenticity_risk": 0.02,
            "safety_hazard": True,  # Fire / thermal hazard!
            "fraud_risk_score": 0.04,
            "fraud_flags": ["HAZMAT_BATTERY_SWELL"],
            "assessor_notes": "POLICY GUARDRAIL: Fire hazard. Mandatory isolation protocol. Standard technician bench processing blocked.",
        }
    },
]

def seed_demo_dataset(db: Session) -> Dict[str, Any]:
    """
    Clears existing demonstration items and seeds the 10 representative electronic devices.
    Ensures complete end-to-end consistency for reverse logistics decision and optimization testing.
    """
    for prev_return in db.query(ReturnRecord).all():
        db.delete(prev_return)
    db.commit()

    created_return_ids = []

    for item in DEMO_DEVICES_SPEC:
        ret_id = f"ret_demo_{uuid.uuid4().hex[:8]}"

        db_return = ReturnRecord(
            id=ret_id,
            product_id=item["product_id"],
            product_name=item["product_name"],
            category=item["category"],
            purchase_price=item["purchase_price"],
            currency="USD",
            customer_id=item["customer_id"],
            order_id=item["order_id"],
            return_reason=item["return_reason"],
            status="assessed",
        )
        db.add(db_return)
        created_return_ids.append(ret_id)

        asm_data = item["assessment"]
        asm_id = f"asm_demo_{uuid.uuid4().hex[:8]}"
        db_assessment = AssessmentRecord(
            id=asm_id,
            return_id=ret_id,
            product_condition=asm_data["product_condition"],
            defect_category=asm_data["defect_category"],
            defect_description=asm_data["defect_description"],
            visible_damage=asm_data["visible_damage"],
            warranty_status=asm_data["warranty_status"],
            verified_warranty_eligible=asm_data["verified_warranty_eligible"],
            repair_probability=asm_data["repair_probability"],
            estimated_repair_cost=asm_data["estimated_repair_cost"],
            estimated_repair_hours=asm_data["estimated_repair_hours"],
            potential_resale_value=asm_data["potential_resale_value"],
            parts_recovery_value=asm_data["parts_recovery_value"],
            authenticity_risk=asm_data["authenticity_risk"],
            safety_hazard=asm_data["safety_hazard"],
            fraud_risk_score=asm_data["fraud_risk_score"],
            fraud_flags=asm_data.get("fraud_flags", []),
            assessor_notes=asm_data["assessor_notes"],
        )
        db.add(db_assessment)

    db.commit()

    return {
        "message": "Successfully seeded 10 synthetic demonstration devices.",
        "seeded_count": len(created_return_ids),
        "return_ids": created_return_ids,
        "repair_capacity_slots": 4,
    }
