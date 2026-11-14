# AGENTS.md - rules for any coding agent working in this repo
Project: PharmaValuate (genuine-only anomaly detection screening for medicine photos). Hardware: i7-13700HX, RTX 4060 Laptop 8 GB VRAM, 16 GB RAM, Windows/WSL2.
Windows environment target: `D:\pharmavaluate\venv312`, Python 3.12.0. Package installation is currently incomplete; use prebuilt wheels only.
1. Do NOT change the protocol: product-first + group splits, `assert_no_leak`, unknown products split into unknown_val/unknown_test, tampers only for val/cal/test, genuine-only detectors, identical JPEG re-encoding for genuine and tampered, test set touched once (notebook 12).
2. Never hand-type result numbers. Every table is generated from files in `results/`.
3. Never tune on test data or on tampers made from test images.
4. Memory limits: <= 4 DataLoader workers, never load a whole dataset into RAM, batch sizes per `configs/default.yaml`; if CUDA OOM, lower batch size / input size and note it in `results/logs/CHANGES.md`.
5. Edit `nb_src/*.py` (percent-format sources), then run `python tools/build_notebooks.py` to regenerate notebooks. Keep notebooks and sources in sync.
6. If a library API differs from the installed version (Anomalib especially), adapt the call, keep the logic, and log the change.
7. All outputs are "screening aid / synthetic stress test" - never write claims of real-counterfeit accuracy.
