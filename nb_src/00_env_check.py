# %% [markdown]
# # 00 - Environment check
# Confirms the GPU is visible, VRAM/RAM are as expected, and times a quick forward pass.
# Expected rig: i7-13700HX, RTX 4060 Laptop 8 GB, 16 GB RAM. **Plug in the charger and set the laptop to its performance mode** before long runs.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
import torch, time, platform, psutil
print(platform.platform()); print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0); print(p.name, f"{p.total_memory/2**30:.1f} GB VRAM")
print(f"RAM {psutil.virtual_memory().total/2**30:.1f} GB, free {psutil.virtual_memory().available/2**30:.1f} GB, CPU threads {os.cpu_count()}")
# %%
import timm
m = timm.create_model("wide_resnet50_2", pretrained=True).cuda().eval()
x = torch.randn(16, 3, 256, 256).cuda()
with torch.no_grad():
    for _ in range(3): m(x)
    torch.cuda.synchronize(); t = time.time()
    for _ in range(10): m(x)
    torch.cuda.synchronize()
print(f"WRN50-2 fp32: {16*10/(time.time()-t):.0f} img/s at 256px (use this to rescale the time estimates in README)")
print("peak VRAM GB", torch.cuda.max_memory_allocated()/2**30)
# %%
from pv.config import *
seed_everything(0); print("repo root:", ROOT)
