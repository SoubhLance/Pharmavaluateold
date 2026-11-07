"""Run a patch-matching detector (PatchCore-style CNN or AnomalyDINO-style DINOv2) and log scores.
method_cfg example:
  dict(name="anomalydino", kind="dino", size=448, topfrac=0.01, ratio=1.0, rotations=(0,90,180,270))
  dict(name="patchcore_wrn50", kind="cnn", backbone="wide_resnet50_2", size=256, topfrac=0.01, ratio=0.1, rotations=(0,))
Gallery = reference-domain genuine images of KNOWN products only. Nothing here trains on anomalies."""
import time, numpy as np, pandas as pd, torch
from tqdm import tqdm
from .config import SCORES, seed_everything
from .features import CNNPatch, DinoPatch, to_tensor, load_rgb
from .patchmem import PatchMemory

DEV = "cuda" if torch.cuda.is_available() else "cpu"

def make_featfn(cfg):
    size = cfg["size"]
    if cfg["kind"] == "cnn":
        ext = CNNPatch(cfg["backbone"], out_dim=cfg.get("out_dim", 512), device=DEV)
        def fn(img):
            f, _ = ext(to_tensor([img])); return f[0]
    else:
        ext = DinoPatch(device=DEV)
        def fn(img):
            p, _ = ext(to_tensor([img])); return p[0]
    return fn, ext

def build_banks(gallery_df, cfg, featfn, seed=0):
    banks = {}
    for pid, g in tqdm(gallery_df.groupby("product_id"), desc="banks"):
        feats = []
        for p in g.path:
            im = load_rgb(p, cfg["size"])
            for r in cfg.get("rotations", (0,)):
                feats.append(featfn(np.ascontiguousarray(np.rot90(im, r // 90))).cpu())
        banks[pid] = PatchMemory(cfg.get("ratio", 1.0), cfg.get("topfrac", 0.01), DEV, seed).fit(torch.cat(feats))
    return banks

def score_df(df, banks, cfg, featfn, pid_col="product_id"):
    out = []
    for r in tqdm(df.itertuples(index=False), total=len(df), desc="scoring"):
        pid = getattr(r, pid_col)
        if pid not in banks: out.append(np.nan); continue      # e.g. "Unknown"
        s, _ = banks[pid].score(featfn(load_rgb(r.path, cfg["size"])))
        out.append(s)
    return np.array(out)

def run_method(cfg, stream, all_df, splits=("val", "cal"), seed=0, pid_col="product_id", tag=""):
    """all_df: rows (genuine + tampered) with columns path, product_id, split, label, tamper, severity, domain.
    Gallery rows are those with split == 'gallery'. Writes results/scores/<name>__<stream>__<split><tag>.csv"""
    seed_everything(seed); t0 = time.time()
    featfn, ext = make_featfn(cfg)
    gal = all_df[all_df.split == "gallery"]
    banks = build_banks(gal, cfg, featfn, seed); fit_s = time.time() - t0
    info = dict(method=cfg["name"], stream=stream, fit_seconds=fit_s, n_products=len(banks),
                bank_patches_mean=float(np.mean([b.size for b in banks.values()])), seed=seed)
    for sp in splits:
        d = all_df[all_df.split == sp].copy()
        t1 = time.time(); d["score"] = score_df(d, banks, cfg, featfn, pid_col)
        info[f"score_seconds_{sp}"] = time.time() - t1
        SCORES.mkdir(parents=True, exist_ok=True)
        d.to_csv(SCORES / f"{cfg['name']}__{stream}__{sp}{tag}.csv", index=False)
    return info
