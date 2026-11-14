You are working in the repo `pharmavaluate/` (read AGENTS.md first). Machine: Windows 11 (or WSL2), i7-13700HX, RTX 4060 Laptop 8 GB VRAM, 16 GB RAM.
Tasks, in order:
1. Verify the folder tree below exists; create anything missing (with .gitkeep in empty dirs). Do not delete or rename anything.
2. Create a Python 3.10/3.11 venv, install the CUDA build of PyTorch (cu124) then `requirements.txt`; run `python tools/build_notebooks.py`.
3. Run a smoke test: `python -c "import torch;print(torch.cuda.is_available())"` and execute `notebooks/00_env_check.ipynb` headless (jupyter nbconvert --execute). Report VRAM/RAM and the printed img/s.
4. Write a pytest file `tests/test_core.py` covering pv/splits.py (assert_no_leak), pv/conformal.py (validity on synthetic Gaussian data), pv/tamper.py (all tampers return a non-empty mask for severities 1-3). Run it.
5. Run `git init`, add a .gitignore (data/raw, data/processed, synth, models, results/scores, .venv), commit.
6. Do NOT run notebooks 01-14 (the data is not downloaded yet) and do NOT change the protocol in AGENTS.md. List any API mismatches you foresee (esp. anomalib==1.2.0 in nb_src/08_efficientad.py) and propose fixes as a diff, don't apply silently.
Tree:
pharmavaluate/{AGENTS.md,README.md,requirements.txt,configs/,data/{raw/{c3pi,mendeley,italian_otc,mvtec},processed,splits}/,synth/,quality/,detectors/,retrieval/,calibration/,region/,ocr/,eval/,app/,report/,models/,results/{scores,tables,figures,logs}/,pv/,nb_src/,notebooks/,tools/,tests/}
