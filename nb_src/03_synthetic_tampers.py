# %% [markdown]
# # 03 - Synthetic tampers + re-encoding of ALL images
# Every image (genuine and tampered, every split) goes through the **same** JPEG q92 save. Tampers are made from the clean PNG, so genuine and tampered files carry identical compression traces.
# Tampers are created only for val / cal / test (known products, phone domain). Genuine-only detectors never train on them.
# Output: `data/splits/<stream>_all.csv` (genuine label 0, tampered label 1) + masks in `synth/<stream>/masks`.
# %%
import sys, os, zlib; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv import tamper
import numpy as np, pandas as pd, cv2
from tqdm import tqdm
STREAM = "pill"
MAX_TAMPER_IMAGES = {"val": 1500, "cal": 1500, "test": 4000}     # cap per split (images that get tampers)
sp = pd.read_csv(SPLITS / f"{STREAM}_splits.csv"); types = CFG["tamper_types"][STREAM]
JPG = PROC / STREAM / "jpg"; MASKS = SYNTH / STREAM / "masks"; TJ = SYNTH / STREAM / "img"
for d in (JPG, MASKS, TJ): d.mkdir(parents=True, exist_ok=True)
print("tamper types:", types)
# %%
rows = []
for r in tqdm(sp.itertuples(), total=len(sp), desc="genuine re-encode"):
    im = cv2.cvtColor(cv2.imread(r.path), cv2.COLOR_BGR2RGB); out = JPG / (pathlib.Path(r.path).stem + ".jpg")
    tamper.reencode(im, out); rows.append(dict(path=str(out), src_path=r.path, obj_mask=r.obj_mask, product_id=r.product_id, group_id=r.group_id,
        domain=r.domain, split=r.split, label=0, tamper="none", severity=0, mask_path=""))
gen = pd.DataFrame(rows)
# %%
trows = []
for split, cap in MAX_TAMPER_IMAGES.items():
    src = gen[(gen.split == split) & (gen.domain == "phone")]
    src = src.sample(min(cap, len(src)), random_state=0)
    for i, r in enumerate(tqdm(src.itertuples(), total=len(src), desc=f"tamper {split}")):
        im = cv2.cvtColor(cv2.imread(r.src_path), cv2.COLOR_BGR2RGB); om = cv2.imread(r.obj_mask, 0) > 0
        for ti, t in enumerate(types):
            sev = (i + ti) % 3 + 1                        # balanced severities
            seed = zlib.crc32(f"{r.src_path}|{t}|{sev}".encode())
            out, mk = tamper.apply(t, im, om, sev, seed)
            stem = f"{pathlib.Path(r.src_path).stem}__{t}{sev}"
            tamper.reencode(out, TJ / f"{stem}.jpg"); cv2.imwrite(str(MASKS / f"{stem}.png"), mk.astype(np.uint8) * 255)
            trows.append(dict(path=str(TJ / f"{stem}.jpg"), src_path=r.src_path, obj_mask=r.obj_mask, product_id=r.product_id, group_id=r.group_id,
                domain=r.domain, split=split, label=1, tamper=t, severity=sev, mask_path=str(MASKS / f"{stem}.png")))
all_df = pd.concat([gen, pd.DataFrame(trows)], ignore_index=True)
all_df.to_csv(SPLITS / f"{STREAM}_all.csv", index=False)
print(all_df.groupby(["split", "label"]).size())
# %%
# eyeball a few tampers (always do this: wrong-looking tampers = meaningless results)
sample = all_df[all_df.label == 1].sample(8, random_state=1)
fig, ax = plt.subplots(2, 8, figsize=(24, 6))
for k, r in enumerate(sample.itertuples()):
    ax[0, k].imshow(cv2.cvtColor(cv2.imread(r.path), cv2.COLOR_BGR2RGB)); ax[0, k].set_title(f"{r.tamper} s{r.severity}"); ax[0, k].axis("off")
    ax[1, k].imshow(cv2.imread(r.mask_path, 0), cmap="gray"); ax[1, k].axis("off")
plt.tight_layout(); plt.savefig(RES / "figures" / f"tamper_examples_{STREAM}.png", dpi=100)
