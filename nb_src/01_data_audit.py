# %% [markdown]
# # 01 - Download audit + raw manifest (per stream)
# Put the downloaded data under `data/raw/` first (see README). Run this notebook once per stream (`STREAM = "pill"`, then `"pack"`).
# **The filename/folder rules below are guesses - open a few files and ADAPT `product_of` and `domain_of`.**
# Writes `data/processed/<stream>_raw_manifest.csv` with columns: path, product_id, group_id, domain, stream.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
import re, numpy as np, pandas as pd, imagehash
from PIL import Image
from tqdm import tqdm
STREAM = "pill"            # "pill" or "pack"
PACK_CASE = "B"            # "A": Mendeley has product labels (>=3 imgs/product); "B": it does not -> Italian-OTC is the reference set
SRC = {"pill": [ROOT/"data/raw/c3pi"], "pack": [ROOT/"data/raw/mendeley"] if PACK_CASE == "A" else [ROOT/"data/raw/italian_otc"]}[STREAM]
MAX_PER_PRODUCT = 20       # subsample for speed/RAM; set None for everything
MAX_PRODUCTS = 600         # None = all. 16 GB RAM / 8 GB VRAM: start modest
files = [p for s in SRC for p in s.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
print(len(files), "images found"); print(files[:5])
# %%
# ---- ADAPT THESE TWO FUNCTIONS TO THE REAL FOLDER / FILE NAMES ----
def product_of(p):
    m = re.match(r"^(\d{4,5}-\d{3,4})", p.name)          # C3PI-style NDC prefix (verify!)
    return m.group(1) if m else p.parent.name            # fallback: folder name = product
def domain_of(p):
    s = str(p).lower()
    if STREAM == "pack" and PACK_CASE == "B": return "ref"   # Italian-OTC clean box shots
    return "ref" if any(k in s for k in ("reference", "controlled", "/ref")) else "phone"
df = pd.DataFrame({"path": [str(p) for p in files]})
df["product_id"] = [product_of(pathlib.Path(p)) for p in df.path]; df["domain"] = [domain_of(pathlib.Path(p)) for p in df.path]
if MAX_PER_PRODUCT: df = df.groupby(["product_id", "domain"]).head(MAX_PER_PRODUCT)
if MAX_PRODUCTS: keep = df.product_id.drop_duplicates().sample(min(MAX_PRODUCTS, df.product_id.nunique()), random_state=0); df = df[df.product_id.isin(keep)]
df = df.reset_index(drop=True); print(df.domain.value_counts().to_dict(), df.product_id.nunique(), "products")
# %%
# near-duplicate groups: perceptual hash, clustered inside each product (hamming <= 6) with union-find
df["ph"] = [imagehash.phash(Image.open(p).convert("RGB")) for p in tqdm(df.path)]
gid = np.empty(len(df), dtype=object)
for pid, g in df.groupby("product_id"):
    idx = g.index.to_list(); parent = {i: i for i in idx}
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if df.ph[idx[a]] - df.ph[idx[b]] <= 6: parent[find(idx[a])] = find(idx[b])
    for i in idx: gid[i] = f"{pid}_g{find(i)}"
df["group_id"] = gid; df["stream"] = STREAM
# %%
# audit table (write this into your report)
sizes = [Image.open(p).size for p in df.path.sample(min(200, len(df)), random_state=0)]
audit = dict(stream=STREAM, n_images=len(df), n_products=df.product_id.nunique(), n_groups=df.group_id.nunique(),
             imgs_per_product_median=float(df.groupby("product_id").size().median()),
             products_lt3=int((df.groupby("product_id").size() < 3).sum()),
             median_w=int(np.median([s[0] for s in sizes])), median_h=int(np.median([s[1] for s in sizes])))
print(audit)
(PROC).mkdir(parents=True, exist_ok=True)
df.drop(columns="ph").to_csv(PROC / f"{STREAM}_raw_manifest.csv", index=False)
pd.DataFrame([audit]).to_csv(RES / "tables" / f"audit_{STREAM}.csv", index=False)
