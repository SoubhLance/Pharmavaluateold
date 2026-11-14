"""
Test client for PharmaValuate FastAPI inference backend.
Sends 3 images from data/processed/pill/jpg (val/cal images, NOT test):
  1. data/processed/pill/jpg/000009.jpg (cal split, known product 00002-3250)
  2. data/processed/pill/jpg/000004.jpg (val split, known product)
  3. data/processed/pill/jpg/000010.jpg (unknown_val split, unknown product)

Can query a live running server (http://127.0.0.1:8000) or test directly in-process.
Wording: "screening aid, verify manually". Never claim a pill is authentic.
"""

import sys, os, json, argparse
from pathlib import Path
import requests

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_IMAGES = [
    {
        "name": "Image 1 (Calibration Genuine)",
        "path": ROOT / "data" / "processed" / "pill" / "jpg" / "000009.jpg",
        "expected_split": "cal",
        "expected_product": "00002-3250"
    },
    {
        "name": "Image 2 (Validation Genuine)",
        "path": ROOT / "data" / "processed" / "pill" / "jpg" / "000004.jpg",
        "expected_split": "val",
        "expected_product": "00002-3239"
    },
    {
        "name": "Image 3 (Unknown-Product Validation)",
        "path": ROOT / "data" / "processed" / "pill" / "jpg" / "000010.jpg",
        "expected_split": "unknown_val",
        "expected_product": "Unknown Product (< tau)"
    }
]

def run_tests_http(base_url: str):
    print(f"============================================================")
    print(f"Testing PharmaValuate Inference Server at {base_url}")
    print(f"Notice: screening aid, verify manually")
    print(f"============================================================")

    # 1. Health check
    try:
        health_resp = requests.get(f"{base_url}/health", timeout=10)
        print(f"\n[GET /health] Status: {health_resp.status_code}")
        print(json.dumps(health_resp.json(), indent=2))
        if health_resp.status_code != 200:
            print("[!] Health check failed. Exiting.")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[!] Could not connect to {base_url}. Server may not be running.")
        return False

    # 2. Test /screen with 3 images
    print(f"\n[POST /screen] Sending 3 validation/calibration images...")
    for idx, item in enumerate(TEST_IMAGES, 1):
        img_path = item["path"]
        print(f"\n" + "-" * 55)
        print(f"[{idx}/3] {item['name']}")
        print(f"Path:  {img_path}")
        print(f"Split: {item['expected_split']} (Expected: {item['expected_product']})")

        if not img_path.exists():
            print(f"[ERROR] Image file does not exist: {img_path}")
            continue

        with open(img_path, "rb") as f:
            files = {"file": (img_path.name, f, "image/jpeg")}
            resp = requests.post(f"{base_url}/screen", files=files, timeout=30)
        
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Response:")
            print(json.dumps(data, indent=2))
            print(f"-> Decision Label:  {data.get('label')}")
            print(f"-> Product ID:      {data.get('product_id')}")
            print(f"-> Anomaly Score:   {data.get('anomaly_score')}")
            print(f"-> Conformal p-val: {data.get('p_value')}")
            print(f"-> Disclaimer:      {data.get('disclaimer')}")
        else:
            print(f"Error response: {resp.text}")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED (screening aid, verify manually)")
    print("=" * 60)
    return True

def run_tests_direct():
    """Fallback in-process test using FastAPI TestClient when live server isn't running."""
    print("Running in-process FastAPI TestClient...")
    from fastapi.testclient import TestClient
    from backend.app import app

    with TestClient(app) as client:
        # 1. Health
        health_resp = client.get("/health")
        print("\n[GET /health] Status:", health_resp.status_code)
        print(json.dumps(health_resp.json(), indent=2))

        # 2. Images
        for idx, item in enumerate(TEST_IMAGES, 1):
            img_path = item["path"]
            print(f"\n" + "-" * 55)
            print(f"[{idx}/3] {item['name']}")
            print(f"Path: {img_path}")
            with open(img_path, "rb") as f:
                resp = client.post("/screen", files={"file": (img_path.name, f, "image/jpeg")})
            print(f"HTTP Status: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test PharmaValuate Screening API")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of the running API")
    args = parser.parse_args()

    # Try live HTTP first, fallback to TestClient if not running
    success = run_tests_http(args.url)
    if not success:
        print("\n[*] Live server not reachable. Launching in-process test client...")
        run_tests_direct()

