"""
Inference engine wrapper for PharmaValuate (pill stream).
Wraps existing pv/ modules without modifying them.
Enforces frozen protocol parameters and disclaimers.

Wording: "screening aid, verify manually". Never claim a pill is authentic.
"""

import sys, os, io, time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml, numpy as np, torch, cv2
from PIL import Image

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pv import quality, conformal
from pv.features import DinoPatch, to_tensor
from pv.patchmem import PatchMemory

STREAM = "pill"
DISCLAIMER = "screening aid, verify manually"

class PharmaValuateScreener:
    """
    Production screening service for PharmaValuate pill stream.
    Reuses frozen configurations and precomputed banks.
    """
    def __init__(self, device: Optional[str] = None, banks_dir: Optional[Path] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.banks_dir = banks_dir or (Path(__file__).resolve().parent / "banks")
        
        # 1. Load frozen settings
        frozen_file = ROOT / "configs" / "frozen.yaml"
        if not frozen_file.exists():
            raise FileNotFoundError(f"Missing frozen config: {frozen_file}")
        
        with open(frozen_file, "r") as f:
            fz = yaml.safe_load(f)[STREAM]
        
        self.gate_thresholds = fz["gate"]
        self.tau = float(fz["tau"])
        self.cal_scores = np.sort(np.asarray(fz["cal_scores"], dtype=np.float32))
        self.alpha_cf = float(fz["alpha_cf"])
        self.alpha_gen = float(fz["alpha_gen"])
        self.method_cfg = fz["method_cfg"]
        self.patch_size = int(self.method_cfg.get("size", 448))
        self.topfrac = float(self.method_cfg.get("topfrac", 0.01))
        self.coreset_ratio = float(self.method_cfg.get("ratio", 1.0))
        
        # 2. Load DINOv2 backbone once
        self.dino = DinoPatch(device=self.device)
        self.dino.eval()
        
        # 3. Load Gallery embeddings for Product ID
        gallery_file = self.banks_dir / "gallery_product_id.pt"
        if not gallery_file.exists():
            raise FileNotFoundError(f"Missing Product ID gallery: {gallery_file}. Run build_banks.py first.")
        
        gal_data = torch.load(gallery_file, map_location=self.device, weights_only=False)
        self.gallery_embeddings = gal_data["embeddings"].to(self.device).float()
        self.gallery_pids = np.array(gal_data["product_ids"])
        self.unique_products = np.array(gal_data["unique_products"])
        self.prod_id_size = int(gal_data.get("size", 224))
        
        # Precompute tensor index masks per product for fast similarity lookup on device
        self.prod_indices = [
            torch.from_numpy(np.where(self.gallery_pids == p)[0]).to(self.device)
            for p in self.unique_products
        ]
        
    def check_quality(self, img_rgb: np.ndarray) -> Tuple[bool, Dict[str, Any]]:
        """Step 1: Capture-quality gate."""
        metrics = quality.quality_metrics(img_rgb)
        passed = bool(quality.passes(metrics, self.gate_thresholds))
        quality_info = {
            "passed": passed,
            "blur": round(float(metrics["blur"]), 4),
            "glare": round(float(metrics["glare"]), 6),
            "mean_lum": round(float(metrics["mean_lum"]), 4),
            "dark": round(float(metrics["dark"]), 6),
            "thresholds": self.gate_thresholds
        }
        return passed, quality_info

    @torch.no_grad()
    def identify_product(self, img_rgb: np.ndarray) -> Tuple[str, float, List[str], List[Dict[str, Any]]]:
        """Step 2: Product ID with frozen DINOv2 ViT-S/14 vs gallery (4 rotations)."""
        im_224 = cv2.resize(img_rgb, (self.prod_id_size, self.prod_id_size), interpolation=cv2.INTER_AREA)
        _, cls = self.dino(to_tensor([im_224]))
        Q = torch.nn.functional.normalize(cls, dim=1) # (1, 384)
        
        # Cosine similarity against all gallery embeddings (all images x 4 rotations)
        S = Q @ self.gallery_embeddings.T # (1, N_gal)
        
        # Max similarity per known product
        best_sims = torch.zeros(len(self.unique_products), device=self.device, dtype=torch.float32)
        for j, idxs in enumerate(self.prod_indices):
            best_sims[j] = S[0, idxs].max()
            
        top_k = min(5, len(self.unique_products))
        top_vals, top_indices = torch.topk(best_sims, k=top_k)
        
        top5_pids = [str(self.unique_products[i.item()]) for i in top_indices]
        top5_sims = [float(v.item()) for v in top_vals]
        
        top5_details = [
            {"product_id": pid, "similarity": round(sim, 4)}
            for pid, sim in zip(top5_pids, top5_sims)
        ]
        
        best_pid = top5_pids[0]
        best_sim = top5_sims[0]
        return best_pid, best_sim, top5_pids, top5_details

    @torch.no_grad()
    def compute_anomaly_score(self, img_rgb: np.ndarray, product_id: str) -> float:
        """Step 3: AnomalyDINO c8 vs product's genuine bank."""
        bank_file = self.banks_dir / f"{product_id}.pt"
        if not bank_file.exists():
            raise FileNotFoundError(f"Reference bank file for product {product_id} not found at {bank_file}")
        
        # Load only the needed product bank
        bank_feats = torch.load(bank_file, map_location=self.device, weights_only=True).to(self.device).float()
        
        mem = PatchMemory(coreset_ratio=self.coreset_ratio, topfrac=self.topfrac, device=self.device, seed=0)
        mem.bank = bank_feats
        
        im_448 = cv2.resize(img_rgb, (self.patch_size, self.patch_size), interpolation=cv2.INTER_AREA)
        patch_tokens, _ = self.dino(to_tensor([im_448]))
        
        score, _ = mem.score(patch_tokens[0])
        return float(score)

    def decide_conformal(self, anomaly_score: float) -> Tuple[float, str]:
        """Step 4: Conformal p-value and screening decision."""
        p_val = float(conformal.pvalues(self.cal_scores, [anomaly_score])[0])
        
        if p_val <= self.alpha_cf:
            label = "Likely Counterfeit"
        elif p_val <= self.alpha_gen:
            label = "Inconclusive"
        else:
            label = "Likely Genuine"
            
        return p_val, label

    def screen(self, img_rgb: np.ndarray) -> Dict[str, Any]:
        """
        Full 4-step pipeline per request:
        1. Quality gate -> "Retake Required" if fail
        2. Product ID -> "Unknown Product" if best similarity < tau
        3. AnomalyDINO c8 vs genuine product bank
        4. Conformal p-value -> "Likely Counterfeit", "Inconclusive", or "Likely Genuine"
        """
        # Step 1: Quality gate
        passed, quality_info = self.check_quality(img_rgb)
        if not passed:
            return {
                "label": "Retake Required",
                "p_value": None,
                "anomaly_score": None,
                "product_id": None,
                "best_similarity": None,
                "top5": None,
                "quality": quality_info,
                "disclaimer": DISCLAIMER
            }

        # Step 2: Product ID
        best_pid, best_sim, top5_pids, top5_details = self.identify_product(img_rgb)
        if best_sim < self.tau:
            return {
                "label": "Unknown Product",
                "p_value": None,
                "anomaly_score": None,
                "product_id": "Unknown Product",
                "best_similarity": round(best_sim, 8),
                "top5": top5_pids,
                "top5_details": top5_details,
                "quality": quality_info,
                "disclaimer": DISCLAIMER
            }

        # Step 3: Anomaly score
        anomaly_score = self.compute_anomaly_score(img_rgb, best_pid)

        # Step 4: Conformal p-value & Decision
        p_val, label = self.decide_conformal(anomaly_score)

        return {
            "label": label,
            "p_value": round(p_val, 6),
            "anomaly_score": round(anomaly_score, 6),
            "product_id": best_pid,
            "best_similarity": round(best_sim, 8),
            "top5": top5_pids,
            "top5_details": top5_details,
            "quality": quality_info,
            "disclaimer": DISCLAIMER
        }

