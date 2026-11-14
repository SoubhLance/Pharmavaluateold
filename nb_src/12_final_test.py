# %% [markdown]
# # 12 - FINAL TEST (run once)
# Reads `configs/frozen.yaml` and scores the **test** split + `unknown_test` products. Produces T1, T2, T3, T6, T8 tables with cluster-bootstrap CIs. Set `I_FROZE_EVERYTHING = True` only when no more tuning will happen. Every number printed here comes from saved score files.
# T4 (perturbations), T5 (OCR), T7 (supervised gap), T9 (cost) are produced by notebooks 04/11/09/13 using the same frozen rules.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.runner import run_method
from pv.conformal import pvalues, decide, fuse
from pv.metrics import auroc, tpr_at_fpr, cluster_bootstrap
import numpy as np, pandas as pd, yaml, json
I_FROZE_EVERYTHING = False
assert I_FROZE_EVERYTHING, "Set to True only after notebook 10 wrote frozen.yaml and you have committed it."
fz = yaml.safe_load(open(ROOT / "configs" / "frozen.yaml")); out = {}
for stream in [s for s in ("pill", "pack") if s in fz]:
    f = fz[stream]; cfg = f["method_cfg"]; cfg["rotations"] = tuple(cfg.get("rotations", (0,)))
    all_df = pd.read_csv(SPLITS / f"{stream}_all.csv")
    sub = all_df[(all_df.split == "gallery") | ((all_df.split == "test") & (all_df.domain == "phone"))]
    run_method(cfg, stream, sub, splits=("test",), tag="_FINAL")                                   # oracle product id (detector-level)
    # end-to-end: use retrieved product id; unknown products get "UNKNOWN" -> no bank -> NaN score
    ret = pd.read_csv(RES / "retrieval" / f"{stream}_pred.csv")
    e2e = all_df.merge(ret[["path", "pred_pid_final"]], on="path", how="inner")
    e2e = e2e[((e2e.split == "test") | (e2e.split == "unknown_test")) & (e2e.label == 0)]
    e2e = pd.concat([all_df[all_df.split == "gallery"].assign(pred_pid_final=lambda d: d.product_id), e2e])
    run_method(cfg, stream, e2e, splits=("test", "unknown_test"), pid_col="pred_pid_final", tag="_E2E_FINAL")
    out[stream] = f
# %%
def load(stream, tag, sp): return pd.read_csv(SCORES / f"{fz[stream]['method_cfg']['name']}__{stream}__{sp}{tag}.csv")
rows = []
for stream, f in out.items():
    cal = np.array(f["cal_scores"]); acf, agen = f["alpha_cf"], f["alpha_gen"]
    t = load(stream, "_FINAL", "test").dropna(subset=["score"]); t["p"] = pvalues(cal, t.score.to_numpy())
    g = t[t.label == 0]
    # T1 validity: share of genuine known-product test images with p <= alpha_cf (should be <= alpha_cf)
    fp = lambda d: (d[d.label == 0].p <= acf).mean() if (d.label == 0).any() else np.nan
    m, lo, hi = cluster_bootstrap(g.assign(label=0), lambda d: (d.p <= acf).mean(), n=500)
    rows.append(dict(test="T1", stream=stream, metric=f"false Likely-Counterfeit rate (target <= {acf})", value=(g.p <= acf).mean(), ci_lo=lo, ci_hi=hi))
    rows.append(dict(test="T1", stream=stream, metric="Inconclusive-or-worse rate on genuine", value=(g.p <= agen).mean(), ci_lo=np.nan, ci_hi=np.nan))
    # T3 detection per tamper type / severity (stress test, synthetic)
    for (tt, sv), d in t[t.label == 1].groupby(["tamper", "severity"]):
        dd = pd.concat([g, d]); a = auroc(dd.label, dd.score)
        rows.append(dict(test="T3", stream=stream, metric=f"AUROC {tt} sev{sv}", value=a, ci_lo=np.nan, ci_hi=np.nan))
    dd = t; m, lo, hi = cluster_bootstrap(dd, lambda d: auroc(d.label, d.score), n=300)
    rows.append(dict(test="T3", stream=stream, metric="AUROC all tampers (synthetic stress test)", value=m, ci_lo=lo, ci_hi=hi))
    rows.append(dict(test="T3", stream=stream, metric="TPR@5%FPR", value=tpr_at_fpr(t.label, t.score, .05), ci_lo=np.nan, ci_hi=np.nan))
    # T2 / T6 end-to-end with identification
    e = load(stream, "_E2E_FINAL", "test"); u = load(stream, "_E2E_FINAL", "unknown_test")
    u_rej = (u.pred_pid_final == "UNKNOWN").mean() if "pred_pid_final" in u else np.nan
    u_scored = u.dropna(subset=["score"]); u_fc = (pvalues(cal, u_scored.score.to_numpy()) <= acf).sum() / max(len(u), 1)
    rows.append(dict(test="T2", stream=stream, metric="Unknown-product rejection rate", value=u_rej, ci_lo=np.nan, ci_hi=np.nan))
    rows.append(dict(test="T2", stream=stream, metric="Unknown products wrongly called Likely Counterfeit", value=u_fc, ci_lo=np.nan, ci_hi=np.nan))
    ret = pd.read_csv(RES / "retrieval" / f"{stream}_pred.csv"); k = ret[ret.split == "test"]
    rows.append(dict(test="T6", stream=stream, metric="identification top-1 (test)", value=(k.pred_pid == k.product_id).mean(), ci_lo=np.nan, ci_hi=np.nan))
    rows.append(dict(test="T6", stream=stream, metric="identification top-5 (test)", value=np.mean([a in s.split(";") for a, s in zip(k.product_id, k.top5)]), ci_lo=np.nan, ci_hi=np.nan))
final = pd.DataFrame(rows); final.to_csv(RES / "tables" / "FINAL_tests.csv", index=False); print(final.to_string())
# %%
# T8: fusion simulation with ARBITRARY pill+pack pairs (not real pairs): label this "simulated" in the report
if len(out) == 2:
    rng = np.random.default_rng(0); P = {}
    for s in out:
        t = load(s, "_FINAL", "test").dropna(subset=["score"]); t["p"] = pvalues(np.array(out[s]["cal_scores"]), t.score.to_numpy()); P[s] = t
    n = 3000; gp = P["pill"][P["pill"].label == 0].p.to_numpy(); gk = P["pack"][P["pack"].label == 0].p.to_numpy(); tp = P["pill"][P["pill"].label == 1].p.to_numpy()
    a, b = rng.choice(gp, n), rng.choice(gk, n); acf = out["pill"]["alpha_cf"]
    fused_gen = np.array([fuse(x, y) for x, y in zip(a, b)])
    fused_tam = np.array([fuse(x, y) for x, y in zip(rng.choice(tp, n), b)])
    print(f"SIMULATED PAIRS  genuine+genuine fused false-alarm {(fused_gen<=acf).mean():.4f} (<= {acf}?)  | tampered pill + genuine pack detected {(fused_tam<=acf).mean():.3f} vs pill alone {(tp<=acf).mean():.3f}")
