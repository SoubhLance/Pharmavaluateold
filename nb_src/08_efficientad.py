# %% [markdown]
# # 08 - EfficientAD-S and -M (global model, trained)
# One global model per stream trained on all known-product **gallery** images (+ photometric/rotation augmented copies, because there is ~1 reference per product). Checkpoint chosen on validation. 3 seeds.
# **Anomalib's API changes between versions** - this notebook targets `anomalib==1.2.0`. If an import or argument fails, fix it to match your installed version (ask Codex) but do not change the protocol.
# **Time:** this is the slowest notebook. Use `STEPS = 15000` for a first pass; `70000` only for final runs (see README time table).
# %%
import sys, os, shutil, time; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.features import to_tensor, load_rgb
from pv.metrics import auroc
import numpy as np, pandas as pd, cv2, torch, albumentations as A
from tqdm import tqdm
STREAM = "pill"; MODEL_SIZE = "S"; SEED = 0; STEPS = 15000; N_AUG = 8
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv")
D = ROOT / "data" / "anomalib" / STREAM
for sub in ("train/good", "val/good", "val/bad"): (D / sub).mkdir(parents=True, exist_ok=True)
# %%
aug = A.Compose([A.RandomBrightnessContrast(.25, .25, p=.8), A.HueSaturationValue(8, 20, 15, p=.6), A.GaussianBlur((3, 5), p=.3), A.Rotate(limit=10, border_mode=cv2.BORDER_REPLICATE, p=.5), A.ImageCompression(quality_range=(70, 95), p=.4)])
gal = all_df[all_df.split == "gallery"]
for i, r in enumerate(tqdm(gal.itertuples(), total=len(gal), desc="train/good")):
    im = cv2.imread(r.path); cv2.imwrite(str(D / "train/good" / f"{i}_orig.jpg"), im)
    for k in range(N_AUG):
        a = aug(image=cv2.cvtColor(np.ascontiguousarray(np.rot90(im, (k % 4))), cv2.COLOR_BGR2RGB))["image"]
        cv2.imwrite(str(D / "train/good" / f"{i}_a{k}.jpg"), cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
val = all_df[(all_df.split == "val") & (all_df.domain == "phone")].groupby(["product_id", "label"]).head(6)
for i, r in enumerate(val.itertuples()): shutil.copy(r.path, D / ("val/bad" if r.label else "val/good") / f"{i}.jpg")
print(len(list((D/'train/good').glob('*'))), "train images")
# %%
from anomalib.data import Folder
from anomalib.engine import Engine
from anomalib.models import EfficientAd
from anomalib.models.image.efficient_ad.torch_model import EfficientAdModelSize
from pytorch_lightning import seed_everything as pl_seed
pl_seed(SEED)
dm = Folder(name=f"pv_{STREAM}", root=str(D), normal_dir="train/good", abnormal_dir="val/bad", normal_test_dir="val/good",
            train_batch_size=1, eval_batch_size=8, num_workers=2)
model = EfficientAd(model_size=EfficientAdModelSize.S if MODEL_SIZE == "S" else EfficientAdModelSize.M)
engine = Engine(max_steps=STEPS, max_epochs=-1, accelerator="gpu", devices=1, default_root_dir=str(RES / "logs" / f"effad_{MODEL_SIZE}_{STREAM}_s{SEED}"),
                check_val_every_n_epoch=None, val_check_interval=min(5000, STEPS), enable_progress_bar=True)
t0 = time.time(); engine.fit(model=model, datamodule=dm); train_min = (time.time() - t0) / 60
print(f"trained in {train_min:.1f} min")
# %%
# score val + cal through the raw torch model (rank-based metrics do not need Anomalib's normalisation)
net = model.model.eval().cuda()
@torch.no_grad()
def eff_score(path):
    x = to_tensor([load_rgb(path, 256)]).cuda()
    try: o = net(x, normalize=False)
    except TypeError: o = net(x)
    return float(o.pred_score if hasattr(o, "pred_score") else o[0])
name = f"efficientad_{MODEL_SIZE.lower()}"
for sp in ("val", "cal"):
    d = all_df[(all_df.split == sp) & (all_df.domain == "phone")].copy(); d["score"] = [eff_score(p) for p in tqdm(d.path)]
    d.to_csv(SCORES / f"{name}__{STREAM}__{sp}_seed{SEED}.csv", index=False)
    if sp == "val": print("VAL AUROC", auroc(d.label, d.score))
pd.DataFrame([dict(model=name, stream=STREAM, seed=SEED, steps=STEPS, train_minutes=train_min, val_auroc=auroc(d.label, d.score) if sp == "val" else np.nan)]).to_csv(RES / "tables" / f"effad_{MODEL_SIZE}_{STREAM}_s{SEED}.csv", index=False)
torch.save(model.state_dict(), ROOT / "models" / f"{name}_{STREAM}_s{SEED}.pt")
# Repeat: change MODEL_SIZE ("S"/"M"), SEED (0,1,2), STREAM ("pill"/"pack"), then rerun from the data cell.
