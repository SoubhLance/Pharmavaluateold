# %% [markdown]
# # 14 - S0 sanity check on MVTec AD
# Does your PatchCore code reproduce published image-AUROC? Put MVTec AD (non-commercial licence, download from mvtec.com) in `data/raw/mvtec/<category>/{train/good,test/...}`. Expect to land within a couple of points of the paper's numbers for the same backbone/coreset (look them up in the paper's table; don't trust numbers from memory). If you are far off, you have a preprocessing or scoring bug - fix before trusting any pill/pack result.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.features import CNNPatch, to_tensor, load_rgb
from pv.patchmem import PatchMemory
from pv.metrics import auroc
import numpy as np, pandas as pd, torch
from tqdm import tqdm
CATS = ["bottle", "hazelnut", "screw", "pill", "capsule"]; SIZE = 224; RATIO = 0.10
ext = CNNPatch("wide_resnet50_2", out_dim=1024, device="cuda")
def feats(path):
    f, _ = ext(to_tensor([load_rgb(path, SIZE)])); return f[0].cpu()
rows = []
for c in CATS:
    root = ROOT / "data" / "raw" / "mvtec" / c
    if not root.exists(): print("missing", c); continue
    tr = sorted((root / "train" / "good").glob("*.png"))
    mem = PatchMemory(RATIO, topfrac=0.0, device="cuda").fit(torch.cat([feats(p) for p in tqdm(tr, desc=c)]))
    te = [(p, 0 if p.parent.name == "good" else 1) for p in sorted((root / "test").rglob("*.png"))]
    s = [mem.score(feats(p))[0] for p, _ in te]
    rows.append(dict(category=c, image_auroc=auroc([y for _, y in te], s), bank=mem.size)); print(rows[-1])
t = pd.DataFrame(rows); t.to_csv(RES / "tables" / "S0_mvtec.csv", index=False); print("mean image AUROC", t.image_auroc.mean())
