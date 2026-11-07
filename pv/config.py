import pathlib
from pathlib import Path
import yaml, random, numpy as np
ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "configs" / "default.yaml"))
PROC = ROOT / "data" / "processed"
SPLITS = ROOT / "data" / "splits"
SYNTH = ROOT / "synth"
RES = ROOT / "results"
SCORES = RES / "scores"

def seed_everything(seed=0):
    random.seed(seed); np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
