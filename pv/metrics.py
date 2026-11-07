import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, roc_curve
def auroc(y, s): return float(roc_auc_score(y, s))
def auprc(y, s): return float(average_precision_score(y, s))
def tpr_at_fpr(y, s, fpr=0.05):
    f, t, _ = roc_curve(y, s); return float(np.interp(fpr, f, t))
def cluster_bootstrap(df, fn, cluster="product_id", n=1000, seed=0):
    """fn(df)->float. Resample whole products. Returns (mean, lo, hi)."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in df.groupby(cluster)}
    keys = np.array(list(groups)); vals = []
    for _ in range(n):
        pick = rng.choice(keys, size=len(keys), replace=True)
        try: vals.append(fn(pd.concat([groups[k] for k in pick])))
        except ValueError: pass   # resample with one class only
    v = np.array(vals); return float(v.mean()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
