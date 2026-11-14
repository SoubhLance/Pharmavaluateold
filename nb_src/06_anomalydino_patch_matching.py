# %% [markdown]
# # 06 - AnomalyDINO-style patch matching (lead candidate)
# Frozen DINOv2 ViT-S/14 patch tokens; reference memory per product (with rotation augmentation for pills); image score = mean of the top `topfrac` patch distances. **No gradient training.**
# Tuning budget: <= 20 configs, scored on a **validation subsample** (genuine phone vs synthetic tampers). No test data here.
# %%
import sys, os, itertools, time; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.runner import run_method
from pv.metrics import auroc, tpr_at_fpr
import numpy as np, pandas as pd, json
STREAM = "pill"
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv")
val_all = all_df[(all_df.split == "val") & (all_df.domain == "phone")]
# subsample for tuning speed: up to 6 images per (product, label)
val_sub = val_all.groupby(["product_id", "label"]).head(6)
tuning_df = pd.concat([all_df[all_df.split == "gallery"], val_sub]); print(len(val_sub), "val rows for tuning")
ROT = (0, 90, 180, 270) if STREAM == "pill" else (0,)
grid = [dict(size=s, topfrac=t, rotations=r) for s, t, r in itertools.product([336, 448], [0.005, 0.01, 0.05], [ROT, (0,)])]
assert len(grid) <= CFG["tuning_budget_per_method"]; print(len(grid), "configs")
# %%
res = []
for i, g in enumerate(grid):
    cfg = dict(name=f"anomalydino_c{i}", kind="dino", ratio=1.0, **g)
    info = run_method(cfg, STREAM, tuning_df, splits=("val",), tag="_tune")
    d = pd.read_csv(SCORES / f"{cfg['name']}__{STREAM}__val_tune.csv").dropna(subset=["score"])
    row = dict(cfg=json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}), val_auroc=auroc(d.label, d.score),
               tpr_at_5fpr=tpr_at_fpr(d.label, d.score, .05), **{k: info[k] for k in ("fit_seconds", "score_seconds_val", "bank_patches_mean")})
    res.append(row); print(i, g["size"], g["topfrac"], len(g["rotations"]), f"AUROC {row['val_auroc']:.3f}")
tab = pd.DataFrame(res).sort_values("val_auroc", ascending=False); tab.to_csv(RES / "tables" / f"grid_anomalydino_{STREAM}.csv", index=False); tab.head()
# %% [markdown]
# Winner is chosen later by notebook 10 from all `grid_*.csv` files using the metric fixed in advance (validation image AUROC; tie-break TPR@5%FPR). Now score the full **val** and **cal** splits with the best config so calibration (notebook 10) has what it needs.
# %%
best = json.loads(tab.iloc[0].cfg); best["rotations"] = tuple(best["rotations"]); best["name"] = "anomalydino_best"
full = all_df[(all_df.split.isin(["gallery", "val", "cal"])) & ((all_df.split == "gallery") | (all_df.domain == "phone"))]
print(run_method(best, STREAM, full, splits=("val", "cal")))
json.dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in best.items()}, open(ROOT / "configs" / f"best_anomalydino_{STREAM}.json", "w"), indent=1)
