# %% [markdown]
# # 02 - Segment, crop, split, leakage audit
# 1. Segment the object (GrabCut by default; optional MobileSAM cell), crop with margin, pad to square, save 512 px PNG + object mask.
# 2. Split **by product, then by group**. Unknown products are split into `unknown_val` (sets tau) and `unknown_test` (final test only).
# 3. Assert no leakage and commit `data/splits/<stream>_splits.csv`.
# For packaging **Case B** the phone-style domain is created by degrading reference images (cell 4).
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.splits import make_splits, assert_no_leak
import numpy as np, pandas as pd, cv2
from tqdm import tqdm
STREAM = "pill"; PACK_CASE = "B"
OUT = PROC / STREAM; (OUT / "clean").mkdir(parents=True, exist_ok=True); (OUT / "mask").mkdir(exist_ok=True)
m = pd.read_csv(PROC / f"{STREAM}_raw_manifest.csv"); print(len(m))
# %%
def grabcut_mask(im):
    h, w = im.shape[:2]; s = 512 / max(h, w); sm = cv2.resize(im, None, fx=s, fy=s) if s < 1 else im.copy()
    mask = np.zeros(sm.shape[:2], np.uint8); H, W = sm.shape[:2]; rect = (int(W*.05), int(H*.05), int(W*.9), int(H*.9))
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    try: cv2.grabCut(cv2.cvtColor(sm, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
    except cv2.error: mask[:] = 3
    fg = ((mask == 1) | (mask == 3)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n > 1: fg = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    return cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
# Optional: better masks with MobileSAM (pip install git+https://github.com/ChaoningZhang/MobileSAM.git ; download mobile_sam.pt)
# from mobile_sam import sam_model_registry, SamAutomaticMaskGenerator ... -> replace grabcut_mask with a function returning a bool mask.
def crop_square(im, mask, size=512, margin=0.08):
    ys, xs = np.where(mask)
    if len(ys) < 50: ys, xs = np.array([0, im.shape[0]-1]), np.array([0, im.shape[1]-1]); mask = np.ones_like(mask)
    y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1; side = int(max(y1-y0, x1-x0)*(1+2*margin)); cy, cx = (y0+y1)//2, (x0+x1)//2
    pad = side
    imp = cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_REPLICATE); mp = cv2.copyMakeBorder(mask.astype(np.uint8), pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    ya, xa = cy - side//2 + pad, cx - side//2 + pad
    c, cm = imp[ya:ya+side, xa:xa+side], mp[ya:ya+side, xa:xa+side]
    return cv2.resize(c, (size, size), interpolation=cv2.INTER_AREA), cv2.resize(cm, (size, size), interpolation=cv2.INTER_NEAREST) > 0
# %%
# Case B only: create phone-style genuine variants from clean reference images (blur, exposure, glare, rotation, noise)
def degrade(im, rng):
    im = im.astype(np.float32)
    ang = rng.uniform(-12, 12); M = cv2.getRotationMatrix2D((im.shape[1]/2, im.shape[0]/2), ang, rng.uniform(.95, 1.05)); im = cv2.warpAffine(im, M, im.shape[1::-1], borderMode=cv2.BORDER_REPLICATE)
    im = cv2.GaussianBlur(im, (0, 0), rng.uniform(0, 1.6)); im = im * rng.uniform(.7, 1.25) + rng.uniform(-18, 18)
    if rng.random() < .3:
        g = np.zeros(im.shape[:2], np.float32); cv2.circle(g, (int(rng.integers(0, im.shape[1])), int(rng.integers(0, im.shape[0]))), int(rng.integers(20, 60)), 1, -1)
        im += cv2.GaussianBlur(g, (0, 0), 25)[..., None] * rng.uniform(40, 110)
    im += rng.normal(0, rng.uniform(0, 5), im.shape)
    return np.clip(im, 0, 255).astype(np.uint8)
N_VARIANTS = 6
# %%
rows = []
rng = np.random.default_rng(0)
for i, r in tqdm(m.iterrows(), total=len(m)):
    im = cv2.cvtColor(cv2.imread(r.path), cv2.COLOR_BGR2RGB); mk = grabcut_mask(im); c, cm = crop_square(im, mk)
    base = f"{i:06d}"; cv2.imwrite(str(OUT/"clean"/f"{base}.png"), cv2.cvtColor(c, cv2.COLOR_RGB2BGR)); cv2.imwrite(str(OUT/"mask"/f"{base}.png"), cm.astype(np.uint8)*255)
    rows.append(dict(path=str(OUT/"clean"/f"{base}.png"), obj_mask=str(OUT/"mask"/f"{base}.png"), product_id=r.product_id, group_id=r.group_id, domain=r.domain, stream=STREAM))
    if STREAM == "pack" and PACK_CASE == "B":
        for k in range(N_VARIANTS):
            v = degrade(c, rng); vb = f"{base}_v{k}"
            cv2.imwrite(str(OUT/"clean"/f"{vb}.png"), cv2.cvtColor(v, cv2.COLOR_RGB2BGR)); cv2.imwrite(str(OUT/"mask"/f"{vb}.png"), cm.astype(np.uint8)*255)
            rows.append(dict(path=str(OUT/"clean"/f"{vb}.png"), obj_mask=str(OUT/"mask"/f"{vb}.png"), product_id=r.product_id, group_id=f"{r.product_id}_var{k//2}", domain="phone", stream=STREAM))
proc = pd.DataFrame(rows)
# %%
sp = make_splits(proc, CFG["unknown_fraction"], CFG["split_fractions"]["val"], CFG["split_fractions"]["cal"], seed=0)
assert_no_leak(sp)      # raises if a group straddles splits or an unknown product leaks
print(sp.split.value_counts()); print(sp.groupby(["split", "domain"]).size())
SPLITS.mkdir(parents=True, exist_ok=True); sp.to_csv(SPLITS / f"{STREAM}_splits.csv", index=False)
print("saved; COMMIT this csv. Re-running with a different seed changes the split - do not do that after you start tuning.")
