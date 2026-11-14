# %% [markdown]
# # 13 - Cost and deployment timing (T9)
# Parameters, FLOPs, latency (GPU + CPU), peak VRAM and memory-bank size for each feature extractor. EfficientAD rows: load the saved state dict from `models/` if you trained it.
# %%
import sys, os, time; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.features import CNNPatch, DinoPatch, BACKBONES
import numpy as np, pandas as pd, torch
from torch.utils.flop_counter import FlopCounterMode
def bench(fn, x, n=30, warm=5, cuda=True):
    for _ in range(warm): fn(x)
    if cuda: torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(n): fn(x)
    if cuda: torch.cuda.synchronize()
    return (time.perf_counter() - t) / n * 1000
rows = []
for dev in ("cuda", "cpu"):
    torch.set_num_threads(os.cpu_count() // 2 if dev == "cpu" else torch.get_num_threads())
    models = {b: CNNPatch(b, device=dev) for b in BACKBONES}; models["dinov2_vits14"] = DinoPatch(device=dev)
    for name, m in models.items():
        size = 448 if name.startswith("dino") else 256; x = torch.randn(1, 3, size, size)
        params = sum(p.numel() for p in m.m.parameters()) / 1e6
        with FlopCounterMode(display=False) as fc: m(x.to(dev))
        if dev == "cuda": torch.cuda.reset_peak_memory_stats()
        ms = bench(lambda z: m(z.to(dev)), x, cuda=(dev == "cuda"), n=30 if dev == "cuda" else 8)
        rows.append(dict(model=name, device=dev, input=size, params_M=round(params, 1), GFLOPs=round(fc.get_total_flops() / 1e9, 1), latency_ms=round(ms, 1),
                         peak_vram_GB=round(torch.cuda.max_memory_allocated() / 2**30, 2) if dev == "cuda" else np.nan))
        print(rows[-1])
t = pd.DataFrame(rows); t.to_csv(RES / "tables" / "T9_cost.csv", index=False); t
# %% [markdown]
# Add to the table by hand-free means: bank sizes from `results/tables/grid_*.csv` (`bank_patches_mean`), EfficientAD latency by timing `model.model` the same way, and optional ONNX export (`torch.onnx.export`) + `onnxruntime` timing for the deployable candidate.
