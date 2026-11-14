# %% [markdown]
# # 04 - Quality gate + capture-perturbation set (T4)
# Thresholds are fitted on **validation phone images only** so ~95% of good images pass. Then a perturbation set (blur, low light, glare, rotation, JPEG) is made from *test* genuine images for the T4 test (generation only; no tuning on it).
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv import quality, tamper
import numpy as np, pandas as pd, cv2, json
from tqdm import tqdm
STREAM = "pill"
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv")
val = all_df[(all_df.split == "val") & (all_df.label == 0) & (all_df.domain == "phone")].sample(frac=1, random_state=0).head(1500)
q = pd.DataFrame([quality.quality_metrics(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)) for p in tqdm(val.path)])
th = quality.fit_thresholds(q, keep=0.95); print(th)
json.dump(th, open(ROOT / "configs" / f"gate_{STREAM}.json", "w"), indent=1)
print("pass rate on val genuine:", np.mean([quality.passes(r, th) for r in q.to_dict("records")]))
# %%
def perturb(im, kind, rng):
    if kind == "blur": return cv2.GaussianBlur(im, (0, 0), rng.uniform(2.5, 5))
    if kind == "lowlight": return np.clip(im.astype(np.float32) * rng.uniform(.25, .5), 0, 255).astype(np.uint8)
    if kind == "glare":
        g = np.zeros(im.shape[:2], np.float32); cv2.circle(g, (int(rng.integers(100, 412)), int(rng.integers(100, 412))), 70, 1, -1)
        return np.clip(im + cv2.GaussianBlur(g, (0, 0), 20)[..., None] * 220, 0, 255).astype(np.uint8)
    if kind == "rotation": M = cv2.getRotationMatrix2D((im.shape[1]/2, im.shape[0]/2), rng.uniform(15, 40), 1); return cv2.warpAffine(im, M, im.shape[1::-1], borderMode=cv2.BORDER_REPLICATE)
    if kind == "jpeg":
        _, b = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(10, 30))]); return cv2.imdecode(b, 1)
test = all_df[(all_df.split == "test") & (all_df.label == 0) & (all_df.domain == "phone")].sample(frac=1, random_state=0).head(500)
PD = SYNTH / STREAM / "perturb"; PD.mkdir(parents=True, exist_ok=True); rows = []; rng = np.random.default_rng(0)
for r in tqdm(test.itertuples(), total=len(test)):
    im = cv2.cvtColor(cv2.imread(r.src_path), cv2.COLOR_BGR2RGB)
    for kind in ["blur", "lowlight", "glare", "rotation", "jpeg"]:
        out = PD / f"{pathlib.Path(r.src_path).stem}_{kind}.jpg"; tamper.reencode(perturb(im, kind, rng), out)
        rows.append(dict(path=str(out), product_id=r.product_id, group_id=r.group_id, domain="phone", split="test", label=0, tamper="none", severity=0, perturb=kind))
pd.DataFrame(rows).to_csv(SPLITS / f"{STREAM}_perturb.csv", index=False)
qp = pd.DataFrame(rows); qp["pass"] = [quality.passes(quality.quality_metrics(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)), th) for p in qp.path]
print(qp.groupby("perturb")["pass"].mean().rename("share passing gate (low = gate catches it)"))
