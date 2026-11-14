# %% [markdown]
# # 09 - Supervised reference model (leave-one-tamper-type-out)
# Binary classifier (genuine vs synthetic tamper), trained on **gallery images with tampers generated on the fly**. For each tamper type: train on the others, evaluate on val tampers of the held-out type. The gap seen-vs-unseen AUROC is T7.
# This is the *only* model allowed to train on tampers.
# %%
import sys, os, time; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.sup import TamperDataset, make_model
from pv.features import to_tensor, load_rgb
from pv.metrics import auroc
import numpy as np, pandas as pd, torch
from torch.utils.data import DataLoader
from tqdm import tqdm
STREAM = "pill"; BACKBONE = "efficientnet_b0"; SEEDS = [0]; EPOCHS = 8; SAMPLES_PER_EPOCH = 12800; BS = 32
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv"); types = CFG["tamper_types"][STREAM]
gal = all_df[all_df.split == "gallery"]; val = all_df[(all_df.split == "val") & (all_df.domain == "phone")]
@torch.no_grad()
def predict(model, df, bs=64):
    model.eval(); out = []
    for i in range(0, len(df), bs):
        x = to_tensor([load_rgb(p, 256) for p in df.path.iloc[i:i+bs]]).cuda()
        with torch.autocast("cuda", dtype=torch.float16): out.append(model(x).float().squeeze(1).cpu())
    return torch.cat(out).numpy()
def train(train_types, seed):
    seed_everything(seed); model = make_model(BACKBONE).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4); steps = EPOCHS * SAMPLES_PER_EPOCH // BS
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-4, total_steps=steps); scaler = torch.cuda.amp.GradScaler()
    for ep in range(EPOCHS):
        dl = DataLoader(TamperDataset(gal, train_types, n=SAMPLES_PER_EPOCH, seed=seed * 100 + ep), batch_size=BS, shuffle=False, num_workers=4, persistent_workers=False)
        model.train(); tot = 0
        for x, y in dl:
            x, y = x.cuda(), y.cuda()
            with torch.autocast("cuda", dtype=torch.float16): loss = torch.nn.functional.binary_cross_entropy_with_logits(model(x).squeeze(1), y)
            opt.zero_grad(); scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step(); tot += loss.item()
        print(f"  epoch {ep} loss {tot/len(dl):.4f}")
    return model
# %%
rows = []
for held in types:
    for sd in SEEDS:
        t0 = time.time(); model = train([t for t in types if t != held], sd); mins = (time.time() - t0) / 60
        d = val.copy(); d["score"] = predict(model, d)
        gen = d[d.label == 0]
        res = dict(held_out=held, seed=sd, train_min=mins)
        for t in types:
            sub = pd.concat([gen, d[d.tamper == t]]); res[("unseen_" if t == held else "seen_") + t] = auroc(sub.label, sub.score)
        rows.append(res); print(res)
tab = pd.DataFrame(rows); tab.to_csv(RES / "tables" / f"supervised_lotyo_{STREAM}_{BACKBONE}.csv", index=False)
seen = tab.filter(like="seen_").drop(columns=[c for c in tab if c.startswith("unseen_")]).mean(axis=1); unseen = tab.filter(like="unseen_").bfill(axis=1).iloc[:, 0]
print("mean seen AUROC", seen.mean(), " mean UNSEEN AUROC", unseen.mean())
