# %% [markdown]
# # 05 - Product identification (frozen DINOv2 ViT-S/14, no training)
# Gallery = reference images of known products. Query -> cosine similarity -> best product. If best similarity < tau -> "Unknown Product".
# tau is set on **val known + unknown_val** products. Predictions are saved for all splits, but only validation numbers are inspected here; the test numbers are read in notebook 12.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.features import DinoPatch, to_tensor, load_rgb
from pv.metrics import auroc
import numpy as np, pandas as pd, torch, json
from tqdm import tqdm
STREAM = "pill"; SIZE = 224
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv"); g = all_df[all_df.label == 0].copy()
dino = DinoPatch(device="cuda")
@torch.no_grad()
def embed(paths, rot=0, bs=32):
    out = []
    for i in range(0, len(paths), bs):
        ims = [np.ascontiguousarray(np.rot90(load_rgb(p, SIZE), rot // 90)) for p in paths[i:i+bs]]
        _, cls = dino(to_tensor(ims)); out.append(torch.nn.functional.normalize(cls, dim=1).cpu())
    return torch.cat(out)
# %%
gal = g[g.split == "gallery"]
rots = (0, 90, 180, 270) if STREAM == "pill" else (0,)
G = torch.cat([embed(gal.path.tolist(), r) for r in rots]); Gp = np.tile(gal.product_id.to_numpy(), len(rots))
prods = np.unique(Gp); print(len(prods), "known products,", len(G), "gallery embeddings")
def identify(paths):
    Q = embed(paths); S = Q @ G.T
    best = np.zeros((len(paths), len(prods)), np.float32)
    for j, p in enumerate(prods): best[:, j] = S[:, torch.from_numpy(Gp == p)].max(1).values.numpy()
    order = np.argsort(-best, 1); return prods[order[:, :5]], np.take_along_axis(best, order[:, :5], 1)
def run(df):
    top, sim = identify(df.path.tolist()); d = df[["path", "product_id", "split", "domain"]].copy()
    d["pred_pid"] = top[:, 0]; d["sim"] = sim[:, 0]; d["top5"] = [";".join(t) for t in top]; return d
# %%
val_known = g[(g.split == "val") & (g.domain == "phone")].drop_duplicates("src_path").head(2000)
val_unk = g[(g.split == "unknown_val") & (g.domain == "phone")].head(1000)
if len(val_unk) == 0: val_unk = g[g.split == "unknown_val"].head(1000)
rk, ru = run(val_known), run(val_unk)
top1 = (rk.pred_pid == rk.product_id).mean(); top5 = np.mean([a in t.split(";") for a, t in zip(rk.product_id, rk.top5)])
print(f"VAL top-1 {top1:.3f}  top-5 {top5:.3f}")
y = np.r_[np.zeros(len(rk)), np.ones(len(ru))]; s = -np.r_[rk.sim, ru.sim]      # unknown = low similarity
print("Unknown-vs-known AUROC (val):", auroc(y, s))
from sklearn.metrics import roc_curve
f, t, th = roc_curve(y, s); j = np.argmax(t - f); tau = float(-th[j])
print(f"tau={tau:.3f}  known kept={(rk.sim>=tau).mean():.3f}  unknown rejected={(ru.sim<tau).mean():.3f}")
json.dump(dict(tau=tau, size=SIZE), open(ROOT / "configs" / f"tau_{STREAM}.json", "w"))
# %%
(RES / "retrieval").mkdir(exist_ok=True, parents=True)
# predictions for every non-gallery split, saved but NOT evaluated here (test = notebook 12)
rest = g[(g.split != "gallery") & (g.domain == "phone")]
pred = pd.concat([run(rest.iloc[i:i+2000]) for i in range(0, len(rest), 2000)], ignore_index=True)
pred["pred_pid_final"] = np.where(pred.sim >= tau, pred.pred_pid, "UNKNOWN")
pred.to_csv(RES / "retrieval" / f"{STREAM}_pred.csv", index=False); print("saved", len(pred))
