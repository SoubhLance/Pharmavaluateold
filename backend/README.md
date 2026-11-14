# PharmaValuate Inference Backend (Pill Stream)

> **Important Clinical & Regulatory Notice**: All predictions and model outputs are a **screening aid, verify manually**. Never claim or assume a medicine/pill is authentic.

This directory contains the production-grade inference service and offline reference bank builder for the PharmaValuate genuine-only anomaly detection system (`frozen-pill-v1`).

---

## 1. Architecture & Pipeline Overview

The backend executes a 4-stage pipeline matching the validated protocol in `configs/frozen.yaml`:

```
Uploaded Image
      │
      ▼
[Stage 1: Capture Quality Gate]
  ├── Evaluates blur variance, glare fraction, mean luminance, and darkness.
  └── Thresholds from configs/frozen.yaml:
        • blur_min: 2.1704
        • glare_max: 0.0000
        • lum_min: 93.3991
        • lum_max: 161.0481
  └── Result: If gate fails ──► Label: "Retake Required"
      │
      ▼ (passes)
[Stage 2: Product Identification]
  ├── Model: Frozen DINOv2 ViT-S/14 (resolution 224x224).
  ├── Cosine similarity against 4 rotations of reference gallery (4,064 embeddings).
  └── Threshold from configs/frozen.yaml:
        • tau = 0.8538
  └── Result: If best similarity < tau ──► Label: "Unknown Product"
      │
      ▼ (best similarity >= tau)
[Stage 3: Patch-level Anomaly Scoring]
  ├── Model: AnomalyDINO c8 (resolution 448x448, topfrac 0.01).
  ├── Loaded per-product reference bank (saved as float16 in backend/banks/{product_id}.pt).
  └── Distance calculation using PatchMemory with nearest-neighbor patch distances.
      │
      ▼
[Stage 4: Conformal p-Value & Calibration Decision]
  ├── Calibrated against 260 calibration genuine phone scores in configs/frozen.yaml.
  ├── Uses pv.conformal.pvalues: p = (1 + count(cal >= score)) / (n + 1).
  └── Decision thresholds:
        • p <= alpha_cf (0.01)  ──► "Likely Counterfeit"
        • p <= alpha_gen (0.50) ──► "Inconclusive"
        • p > alpha_gen         ──► "Likely Genuine"
```

---

## 2. Directory Layout

```
backend/
├── banks/                     # Serialized reference banks (generated offline)
│   ├── gallery_product_id.pt  # float32 DINOv2 CLS embeddings for 480 products x 4 rotations
│   └── {product_id}.pt        # Per-product float16 patch token banks for AnomalyDINO
├── app.py                     # FastAPI application (GET /health, POST /screen)
├── service.py                 # Core screening engine wrapping pv/ modules
├── build_banks.py             # Offline bank generation script
├── test_client.py             # Validation test script (sends 3 val/cal images)
├── requirements.txt           # Backend dependency specifications
└── README.md                  # This file
```

---

## 3. Setup & Installation

Ensure you are in the workspace root with the project virtual environment activated:

```powershell
# From D:\pharmavaluate
.\venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

---

## 4. Precomputed Reference Banks & Offline Generation

The backend uses precomputed patch feature banks for AnomalyDINO nearest-neighbor matching across all 480 known products:

### Option A: Download Precomputed Banks (Recommended)
1. Download `banks.zip` (~2.76 GB) from [Google Drive Download Link](https://drive.google.com/file/d/1AJ7f2rv9zrWO57fUNIr-WXH61uIqND6u/view?usp=sharing).
2. Unzip all `.pt` files directly into `backend/banks/`.

### Option B: Build Offline from Dataset
If you have the genuine training dataset locally, you can build the reference banks:

```powershell
python backend/build_banks.py
```

- **Runtime**: ~1.5 - 2.0 minutes on RTX 4060 Laptop GPU.
- **Output**: 481 `.pt` files saved under `backend/banks/`; the product-ID gallery is float32, and per-product patch banks are float16.
- **RAM Efficiency**: Images are processed and serialized incrementally by product ID, keeping memory overhead minimal.

---

## 5. Running the FastAPI Server

Start the API server using Uvicorn:

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

The application loads the DINOv2 ViT-S/14 backbone and gallery embeddings once into GPU memory at startup. Product banks are loaded on-demand per request.

---

## 6. API Reference

### `GET /health`
Verifies backend service status and hardware accelerator.

**Response**:
```json
{
  "status": "healthy",
  "device": "cuda",
  "stream": "pill",
  "gallery_products": 480,
  "disclaimer": "screening aid, verify manually"
}
```

---

### `POST /screen`
Upload an image of a pill (`multipart/form-data`, field name `file`).

**Sample Request (cURL)**:
```bash
curl -X POST "http://127.0.0.1:8000/screen" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@data/processed/pill/jpg/000009.jpg"
```

**Sample Response (Likely Genuine)**:
```json
{
  "label": "Likely Genuine",
  "p_value": 0.94636,
  "anomaly_score": 37.040901,
  "product_id": "00002-3250",
  "top5": [
    "00002-3250",
    "00591-0370",
    "00378-6201",
    "00555-0324",
    "00093-3196"
  ],
  "top5_details": [
    {"product_id": "00002-3250", "similarity": 0.877},
    {"product_id": "00591-0370", "similarity": 0.862},
    {"product_id": "00378-6201", "similarity": 0.8544},
    {"product_id": "00555-0324", "similarity": 0.8538},
    {"product_id": "00093-3196", "similarity": 0.847}
  ],
  "quality": {
    "passed": true,
    "blur": 61.6723,
    "glare": 0.0,
    "mean_lum": 121.5404,
    "dark": 0.002174,
    "thresholds": {
      "blur_min": 2.1704256134864566,
      "glare_max": 0.0,
      "lum_max": 161.04805908265507,
      "lum_min": 93.39914719920536
    }
  },
  "disclaimer": "screening aid, verify manually"
}
```

---

## 7. Running the Test Suite

The test client verifies the pipeline across 3 calibration/validation images (`data/processed/pill/jpg`):
1. `000009.jpg` (cal split, genuine pill of known product `00002-3250`)
2. `000004.jpg` (val split, genuine pill of known product `00002-3229`)
3. `000010.jpg` (unknown_val split, genuine pill of unknown product)

Run against a running server:
```powershell
python backend/test_client.py --url http://127.0.0.1:8000
```

Or run directly (self-contained in-process test):
```powershell
python backend/test_client.py
```

---

## 8. Protocol & Integrity Compliance

- **Zero modifications to `pv/` modules**: All detectors (`DinoPatch`, `PatchMemory`), quality checkers (`quality_metrics`, `passes`), and conformal calibration tools (`pvalues`, `decide`) are wrapped without editing source files.
- **Strict adherence to frozen parameters**: All thresholds (`tau`, `gate`, `alpha_cf`, `alpha_gen`, `cal_scores`, `method_cfg`) are read strictly from `configs/frozen.yaml`.
- **Test split isolation**: No test images are accessed or referenced by the backend or test suite.

