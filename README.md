# PharmaValuate - training workspace
Genuine-only counterfeit-medicine screening (pill stream + packaging stream). See the project plan PDF for the full rationale.

## Setup (Windows 11 native or WSL2 Ubuntu; Python 3.12)

On this machine, the target environment is `D:\pharmavaluate\venv312` (Python 3.12.0). It was created, but package installation is pending because access to the official PyTorch wheel index was denied by the machine's network policy. Install only prebuilt wheels; do not build packages from source.
```powershell
python -m venv venv312
.\venv312\Scripts\Activate.ps1
python -m pip install --only-binary=:all: torch torchvision --index-url https://download.pytorch.org/whl/cu124
python -m pip install --only-binary=:all: -r requirements.txt
python -m pip install --only-binary=:all: psutil
python tools/build_notebooks.py
jupyter lab
```

For WSL2, create a Python 3.12 environment with `python3 -m venv venv312` and activate it with `source venv312/bin/activate`; use the matching CUDA-on-WSL PyTorch wheel index.
Then run `notebooks/00_env_check.ipynb`.

## Run the pill screening backend

From the project root, use the project environment and start the local API:

```powershell
.\venv\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the browser UI. The API docs are at http://127.0.0.1:8000/docs. The output is a screening aid; verify manually.

### Precomputed AnomalyDINO Reference Banks (`backend/banks/`)
To run full anomaly screening across all 480 known medicines without recomputing reference features:
1. **Download**: Download `banks.zip` (~2.76 GB) from [Google Drive Download Link](https://drive.google.com/file/d/1AJ7f2rv9zrWO57fUNIr-WXH61uIqND6u/view?usp=sharing).
2. **Extract**: Extract the 480 `.pt` files directly into `backend/banks/`.
3. *Alternative (offline build)*: If the genuine training images are available locally, you can also regenerate all banks in ~2 minutes with `python backend/build_banks.py`.

## Data (put under data/raw/)
- `data/raw/c3pi/`    NLM C3PI/RxImage (start with sampleData.zip, 493 MB; then the 6.8 GB reference zip). Check licence (ODbL).
- `data/raw/mendeley/` Mobile-Captured Drug Packs (DOI 10.17632/bsmy5jjysy.3). Check for product labels -> Case A or B.
- `data/raw/italian_otc/` HF dataset `mennox/Italian-OTC-medicines`.
- `data/raw/mvtec/`  MVTec AD (non-commercial), only for notebook 14.

## Run order (each notebook has a STREAM switch: run once with "pill", once with "pack")
| NB | Purpose | Needs GPU |
|----|---------|-----------|
| 00 | env check | yes |
| 01 | audit + raw manifest + dedupe groups | no |
| 02 | segment, crop, split, leakage assert | no (CPU heavy) |
| 03 | synthetic tampers + JPEG re-encode of everything | no |
| 04 | quality gate + perturbation set (T4) | no |
| 05 | product identification (DINOv2) + tau | yes |
| 06 | AnomalyDINO-style patch matching, tuning grid | yes |
| 07 | PatchCore, 4 backbones x 2 coreset ratios | yes |
| 08 | EfficientAD S/M (Anomalib) | yes, long |
| 09 | supervised reference, leave-one-tamper-out | yes |
| 10 | pick winner, Mondrian conformal calibration, FREEZE | no |
| 11 | OCR rules (T5) | yes (EasyOCR) |
| 12 | FINAL TEST, once (T1, T2, T3, T6, T8) | yes |
| 13 | cost / latency (T9) | yes |
| 14 | MVTec sanity (S0) - run early, right after 07 | yes |

## Estimated training / run time on this rig (ESTIMATES, not measurements)
Assumes RTX 4060 Laptop 8 GB plugged in, ~12k images per stream. Notebook 00 prints your real img/s so you can rescale. Replace this table with logged times (`fit_seconds`, `train_minutes` in results/tables).
| Step | Per stream | Notes |
|------|-----------|-------|
| Download C3PI reference zip | 0.5-1.5 h | network-bound |
| 01 audit + phash | 5-15 min | |
| 02 segmentation (GrabCut, CPU) | 1-2 h | cut with MAX_PRODUCTS; MobileSAM on GPU is faster |
| 03 tampers + re-encode | 20-40 min | |
| 04 gate + perturbations | ~10 min | |
| 05 DINOv2 identification | 10-20 min | |
| 06 AnomalyDINO grid (12 configs) | 30-60 min | no gradient training |
| 07 PatchCore grid (8 configs) + 3 seeds | 1-1.5 h | WRN50 slowest |
| 08 EfficientAD-S, 15k steps | 20-40 min / run | tuning |
| 08 EfficientAD-S, 70k steps | 1.5-3 h / run | final |
| 08 EfficientAD-M, 15k steps | 45-90 min / run | |
| 08 EfficientAD-M, 70k steps | 4-8 h / run | final; consider 1 seed only |
| 09 supervised (EffNet-B0, 6 folds x 8 epochs) | 35-60 min / seed | |
| 10 calibration | minutes | |
| 11 OCR (600 images) | 5-15 min | |
| 12 final test scoring | 0.5-1.5 h | |
| 13 cost | ~10 min | |
| 14 MVTec (5 categories) | 15-30 min | |

**Lean plan** (EffAD-S 15k + M 15k, 1 seed, both streams, supervised 1 seed): roughly 12-20 h of machine time, ~2-4 days of calendar time.
**Full plan** (3 seeds, EffAD S+M at 70k, both streams): roughly 55-80 h of GPU time, mostly EfficientAD-M. Do tuning at 15k steps and spend 70k steps only on the final models.
Laptop tips: close Chrome (16 GB RAM), keep `num_workers<=4`, plug in power, use a cooling pad; 8 GB VRAM is enough for everything here at the default sizes. Skip Dinomaly2 (needs more VRAM/time).
