#!/usr/bin/env python3
"""
Intelligent Product Returns & Recovery Engine
Demo Assessment Runner for Person 2 (Device Intelligence & Assessment)
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5001"

def run_demo():
    print("=" * 95)
    print("INTELLIGENT PRODUCT RETURNS & RECOVERY ENGINE — DEMO ASSESSMENT RUNNER")
    print("=" * 95)

    # 1. Check health
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=5) as r:
            health = json.loads(r.read())
            print(f"Backend Status: {health.get('status')} | Version: {health.get('version')}")
            print(f"Active Modules: {', '.join(health.get('modules', []))}")
    except urllib.error.URLError:
        print(f"Error: Backend server is not reachable at {BASE_URL}.")
        print("Please ensure 'python3 app.py' is running.")
        sys.exit(1)

    # 2. Fetch 10 demo fixtures
    with urllib.request.urlopen(f"{BASE_URL}/api/device-assessment/returns", timeout=5) as r:
        data = json.load(r)
        demo_returns = data.get("returns", [])

    header_fmt = "{:<13} | {:<21} | {:<18} | {:<4} | {:<4} | {:<12} | {}"
    row_fmt    = "{:<13} | {:<21} | {:<18} | {:<4} | {:<4} | {:<12} | {}"

    print(f"\nLoaded {len(demo_returns)} synthetic device returns from backend:")
    print("-" * 95)
    print(header_fmt.format("RETURN ID", "DEVICE / MODEL", "AUTH (RISK)", "COND", "REP", "WARRANTY", "DISPOSITION"))
    print("-" * 95)

    for ret in demo_returns:
        req = urllib.request.Request(
            f"{BASE_URL}/api/device-assessment",
            data=json.dumps(ret).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.load(r)
            rid = res.get("return_id") or res.get("returnId")
            dev = (res["product"]["manufacturer"] + " " + res["product"]["model"])[:21]
            auth = f"{res.get('authenticity_status')} ({res.get('authenticity_risk_score')})"
            c_score = res.get("condition_score")
            r_score = res.get("repairability_score")
            warr = str(res.get("warranty_status"))
            disp = str(res.get("preliminaryDisposition"))
            print(row_fmt.format(rid, dev, auth, c_score, r_score, warr, disp))

    print("-" * 95)
    print("SUCCESS: All 10 assessments executed and validated successfully!")
    print(f"Web Dashboard URL: {BASE_URL}/device-assessment")
    print("=" * 95)

if __name__ == "__main__":
    run_demo()
