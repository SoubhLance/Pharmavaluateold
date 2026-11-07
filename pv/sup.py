"""Supervised reference (row E): genuine vs ON-THE-FLY synthetic tampers. Lives in a module so DataLoader workers can pickle it on Windows."""
import cv2, numpy as np, torch, timm, pandas as pd
from torch.utils.data import Dataset
from .tamper import TAMPERS
from .features import to_tensor

class TamperDataset(Dataset):
    def __init__(self, df, allowed_types, size=256, n=12800, p_tamper=0.5, seed=0):
        self.df, self.types, self.size, self.n, self.p, self.seed = df.reset_index(drop=True), list(allowed_types), size, n, p_tamper, seed
    def __len__(self): return self.n
    def __getitem__(self, i):
        rng = np.random.default_rng(self.seed * 1_000_003 + i)
        r = self.df.iloc[int(rng.integers(0, len(self.df)))]
        im = cv2.cvtColor(cv2.imread(r.path), cv2.COLOR_BGR2RGB); im = cv2.resize(im, (self.size, self.size))
        y = 0
        if rng.random() < self.p:
            om = cv2.imread(r.obj_mask, 0); om = cv2.resize(om, (self.size, self.size), interpolation=cv2.INTER_NEAREST) > 0
            t = self.types[int(rng.integers(0, len(self.types)))]; sev = int(rng.integers(1, 4))
            im, _ = TAMPERS[t](im, om, sev, rng); y = 1
        # identical re-encode for BOTH classes (no JPEG shortcut)
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        im = cv2.cvtColor(cv2.imdecode(buf, 1), cv2.COLOR_BGR2RGB)
        if rng.random() < 0.5: im = np.ascontiguousarray(im[:, ::-1])
        return to_tensor([im])[0], torch.tensor(float(y))

def make_model(name="efficientnet_b0"):
    return timm.create_model(name, pretrained=True, num_classes=1)
