# %% [markdown]
# # 07 - PatchCore backbone comparison (CNN baseline)
# Backbones: ResNet-18, WideResNet-50-2, EfficientNet-B0, ConvNeXt-Tiny. Layers = stride-8 + stride-16 maps. Coreset ratio 1% vs 10%. Score = max patch distance (PatchCore). Records memory-bank size and timing for the cost table (T9).
# 4 backbones x 2 ratios = 8 configs (within the 20-config budget). Coreset seeds are repeated for the winner.
# %%
import sys, os, itertools; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.runner import run_method
from pv.metrics import auroc, tpr_at_fpr
import numpy as np, pandas as pd, json
STREAM = "pill"
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv")
val_sub = all_df[(all_df.split == "val") & (all_df.domain == "phone")].groupby(["product_id", "label"]).head(6)
tuning_df = pd.concat([all_df[all_df.split == "gallery"], val_sub])
ROT = (0, 90, 180, 270) if STREAM == "pill" else (0,)
grid = [dict(backbone=b, ratio=r) for b, r in itertools.product(["resnet18", "wide_resnet50_2", "efficientnet_b0", "convnext_tiny"], [0.01, 0.10])]
# %%
res = []
for i, g in enumerate(grid):
    cfg = dict(name=f"patchcore_{g['backbone']}_r{int(g['ratio']*100)}", kind="cnn", size=256, topfrac=0.0, rotations=ROT, out_dim=512, **g)
    info = run_method(cfg, STREAM, tuning_df, splits=("val",), tag="_tune")
    d = pd.read_csv(SCORES / f"{cfg['name']}__{STREAM}__val_tune.csv").dropna(subset=["score"])
    res.append(dict(cfg=json.dumps({k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}), backbone=g["backbone"], ratio=g["ratio"],
                    val_auroc=auroc(d.label, d.score), tpr_at_5fpr=tpr_at_fpr(d.label, d.score, .05), **{k: info[k] for k in ("fit_seconds", "score_seconds_val", "bank_patches_mean")}))
    print(cfg["name"], f"AUROC {res[-1]['val_auroc']:.3f}  bank~{info['bank_patches_mean']:.0f} patches")
tab = pd.DataFrame(res).sort_values("val_auroc", ascending=False); tab.to_csv(RES / "tables" / f"grid_patchcore_{STREAM}.csv", index=False); tab
# %%
# score full val + cal with the best config, over 3 coreset seeds (seed affects greedy start point)
best = json.loads(tab.iloc[0].cfg); best["rotations"] = tuple(best["rotations"])
full = all_df[(all_df.split.isin(["gallery", "val", "cal"])) & ((all_df.split == "gallery") | (all_df.domain == "phone"))]
for sd in CFG["seeds"]:
    cfg = dict(best, name="patchcore_best"); run_method(cfg, STREAM, full, splits=("val", "cal"), seed=sd, tag=f"_seed{sd}")
cfg = dict(best, name="patchcore_best"); run_method(cfg, STREAM, full, splits=("val", "cal"), seed=0)   # seed-0 copy used by calibration
json.dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}, open(ROOT / "configs" / f"best_patchcore_{STREAM}.json", "w"), indent=1)
