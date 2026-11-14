# %% [markdown]
# # 10 - Pick winners, conformal calibration, FREEZE
# 1. Per stream, choose the winning patch-matching config from `results/tables/grid_*.csv` by the metric fixed in advance: **validation image AUROC** (tie-break TPR@5%FPR).
# 2. Mondrian conformal calibration on **cal** genuine phone images (cell = stream x domain).
# 3. Choose `alpha_gen` on **cal tampers** (target: 95% of synthetic tampers get p <= alpha_gen). This has NO guarantee on real counterfeits.
# 4. Write `configs/frozen.yaml`. After this you do not tune anything. Notebook 12 reads this file.
# %%
import sys, os, glob; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.conformal import Mondrian, pvalues, min_cal_size
import numpy as np, pandas as pd, json, yaml, matplotlib.pyplot as plt
STREAM = "pill"; TARGET_TAMPER_FLAG = 0.95
grids = pd.concat([pd.read_csv(f) for f in glob.glob(str(RES / "tables" / f"grid_*_{STREAM}.csv"))])
grids = grids.sort_values(["val_auroc", "tpr_at_5fpr"], ascending=False); print(grids[["cfg", "val_auroc", "tpr_at_5fpr"]].head(5).to_string())
winner_cfg = json.loads(grids.iloc[0].cfg); print("WINNER:", winner_cfg["name"])
# Scores for the winner were saved by notebooks 06/07 under the *_best name of its family:
family = "anomalydino" if winner_cfg["name"].startswith("anomalydino") else "patchcore"
cal = pd.read_csv(SCORES / f"{family}_best__{STREAM}__cal.csv").dropna(subset=["score"])
cal_gen = cal[(cal.label == 0) & (cal.domain == "phone")].copy(); cal_gen["stream"] = STREAM
cal_tam = cal[cal.label == 1]
print(len(cal_gen), "calibration genuine; need >=", min_cal_size(CFG["alpha_cf"]), "for alpha_cf =", CFG["alpha_cf"])
mon = Mondrian().fit(cal_gen); cells = mon.cells[(STREAM, "phone")]
# %%
p_t = pvalues(cells, cal_tam.score.to_numpy())
alpha_gen = float(np.quantile(p_t, TARGET_TAMPER_FLAG))       # 95% of cal tampers have p <= alpha_gen
alpha_gen = min(max(alpha_gen, CFG["alpha_cf"] * 2), 0.5)
print("alpha_gen =", alpha_gen, "| share of cal tampers p<=alpha_cf:", (p_t <= CFG["alpha_cf"]).mean())
# coverage-vs-error curve (cal): abstention vs error as alpha_gen varies
al = np.linspace(0.01, 0.6, 60)
miss = [(p_t > a).mean() for a in al]; inc = [(pvalues(cells, cal_gen.score.to_numpy()) <= a).mean() for a in al]
plt.plot(inc, miss); plt.xlabel("share of genuine flagged Inconclusive-or-worse"); plt.ylabel("share of tampers called Likely Genuine"); plt.title("calibration-set trade-off (synthetic tampers)")
plt.savefig(RES / "figures" / f"coverage_error_{STREAM}.png", dpi=110)
# %%
frozen_path = ROOT / "configs" / "frozen.yaml"
frozen = yaml.safe_load(open(frozen_path)) if frozen_path.exists() else {}
frozen[STREAM] = dict(method_cfg=winner_cfg, cal_scores=[float(x) for x in np.sort(cells)], alpha_cf=CFG["alpha_cf"], alpha_gen=alpha_gen,
                      tau=json.load(open(ROOT / "configs" / f"tau_{STREAM}.json"))["tau"], gate=json.load(open(ROOT / "configs" / f"gate_{STREAM}.json")))
yaml.safe_dump(frozen, open(frozen_path, "w")); print("FROZEN. Commit configs/frozen.yaml and git tag it before running notebook 12.")
