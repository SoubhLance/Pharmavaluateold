"""
Offline script to build and save reference banks and gallery embeddings.
Stream: pill (frozen-pill-v1)

Outputs:
  - backend/banks/gallery_product_id.pt (float32 DINOv2 CLS embeddings for product ID)
  - backend/banks/{product_id}.pt (float16 patch tokens for AnomalyDINO)

Wording: screening aid, verify manually.
"""

import sys, os, time, math
from pathlib import Path
import yaml, numpy as np, pandas as pd, torch
from tqdm import tqdm

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pv.features import DinoPatch, to_tensor, load_rgb
from pv.patchmem import PatchMemory

STREAM = "pill"
PROD_ID_SIZE = 224

def build_product_gallery(gal_df, dino, banks_dir, tau, rotations, size=224):
    """Build the phase 5 product gallery without reducing normalized vectors to float16."""
    gal_paths = gal_df.path.tolist()
    gal_pids = gal_df.product_id.tolist()
    G_list = []
    Gp_list = []
    bs = 32
    for rot in rotations:
        print(f"    - Processing rotation {rot} deg...")
        for i in range(0, len(gal_paths), bs):
            batch_paths = gal_paths[i:i + bs]
            ims = [np.ascontiguousarray(np.rot90(load_rgb(p, size), rot // 90)) for p in batch_paths]
            with torch.no_grad():
                _, cls = dino(to_tensor(ims))
                # Phase 5 keeps normalized gallery and query embeddings in float32.
                norm_cls = torch.nn.functional.normalize(cls, dim=1).cpu()
            G_list.append(norm_cls)
            Gp_list.extend(gal_pids[i:i + bs])

    G = torch.cat(G_list, dim=0)
    Gp = np.asarray(Gp_list)
    unique_prods = np.unique(Gp)
    gallery_save_path = banks_dir / "gallery_product_id.pt"
    torch.save({
        "embeddings": G,
        "product_ids": Gp.tolist(),
        "unique_products": unique_prods.tolist(),
        "tau": tau,
        "size": size,
        "rotations": list(rotations),
        "dtype": "float32",
    }, gallery_save_path)
    print(f"    Saved Product ID Gallery to {gallery_save_path} ({G.shape[0]} embeddings, dtype={G.dtype})")


def build_all_banks(gallery_only=False):
    t_start = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] PharmaValuate (pill stream) - Bank Builder")
    print(f"[*] Device: {device}")
    print(f"[*] Disclaimer: screening aid, verify manually")

    frozen_path = ROOT / "configs" / "frozen.yaml"
    if not frozen_path.exists():
        raise FileNotFoundError(f"Missing frozen config: {frozen_path}")
    
    with open(frozen_path, "r") as f:
        fz = yaml.safe_load(f)[STREAM]
    
    method_cfg = fz["method_cfg"]
    tau = float(fz["tau"])
    patch_size = int(method_cfg.get("size", 448))
    rotations = tuple(method_cfg.get("rotations", [0, 90, 180, 270]))
    coreset_ratio = float(method_cfg.get("ratio", 1.0))
    topfrac = float(method_cfg.get("topfrac", 0.01))

    print(f"[*] Configuration: patch_size={patch_size}, topfrac={topfrac}, ratio={coreset_ratio}, rotations={rotations}, tau={tau:.4f}")

    splits_path = ROOT / "data" / "splits" / f"{STREAM}_all.csv"
    if not splits_path.exists():
        raise FileNotFoundError(f"Missing splits file: {splits_path}")

    all_df = pd.read_csv(splits_path)
    gal_df = all_df[(all_df.split == "gallery") & (all_df.label == 0)].copy()
    prods = np.sort(gal_df.product_id.unique())
    n_images = len(gal_df)
    n_prods = len(prods)
    print(f"[*] Gallery set: {n_images} images across {n_prods} known products")

    banks_dir = Path(__file__).resolve().parent / "banks"
    banks_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Loading DINOv2 ViT-S/14 backbone onto {device}...")
    dino = DinoPatch(device=device)

    # -------------------------------------------------------------
    # 1. Build Product Identification Gallery (SIZE = 224)
    # -------------------------------------------------------------
    print(f"\n[1/2] Building Product ID Gallery embeddings (size={PROD_ID_SIZE}, rotations={rotations})...")
    t_gal_start = time.time()
    build_product_gallery(gal_df, dino, banks_dir, tau, rotations, size=PROD_ID_SIZE)
    print(f"    Product ID gallery build time: {time.time() - t_gal_start:.2f}s")
    if gallery_only:
        return

    # -------------------------------------------------------------
    # 2. Build AnomalyDINO Product Banks (SIZE = 448)
    # -------------------------------------------------------------
    print(f"\n[2/2] Building AnomalyDINO product banks (size={patch_size}, rotations={rotations})...")
    t_banks_start = time.time()

    for pid in tqdm(prods, desc="Product Banks"):
        prod_rows = gal_df[gal_df.product_id == pid]
        feats = []
        for img_path in prod_rows.path:
            im = load_rgb(img_path, patch_size)
            # Batch 4 rotations together for efficiency
            rot_ims = [np.ascontiguousarray(np.rot90(im, r // 90)) for r in rotations]
            with torch.no_grad():
                patch_tokens, _ = dino(to_tensor(rot_ims))
                # patch_tokens shape: (len(rotations), 1024, 384)
                feats.append(patch_tokens.reshape(-1, patch_tokens.shape[-1]).half().cpu())
        
        prod_feats = torch.cat(feats, dim=0) # (N_patches, 384), float16
        
        # If coreset ratio < 1.0, downsample
        if coreset_ratio < 1.0:
            mem = PatchMemory(coreset_ratio=coreset_ratio, topfrac=topfrac, device=device, seed=0)
            mem.fit(prod_feats.float())
            prod_feats = mem.bank.half().cpu()

        bank_file = banks_dir / f"{pid}.pt"
        torch.save(prod_feats, bank_file)

    t_banks_end = time.time()
    print(f"    Product banks build time: {t_banks_end - t_banks_start:.2f}s")

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    total_time = time.time() - t_start
    total_bytes = sum(f.stat().st_size for f in banks_dir.glob("*.pt"))
    total_mb = total_bytes / (1024 ** 2)
    total_gb = total_bytes / (1024 ** 3)
    num_files = len(list(banks_dir.glob("*.pt")))

    print("\n" + "=" * 60)
    print("BANK GENERATION COMPLETE (screening aid, verify manually)")
    print(f"  Total files saved: {num_files} ({n_prods} product banks + 1 gallery file)")
    print(f"  Total disk size:   {total_mb:.2f} MB ({total_gb:.3f} GB)")
    print(f"  Total wall time:   {total_time:.2f} seconds ({total_time / 60:.2f} minutes)")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build frozen PharmaValuate reference banks")
    parser.add_argument("--gallery-only", action="store_true", help="Rebuild only the phase 5 product-ID gallery")
    build_all_banks(gallery_only=parser.parse_args().gallery_only)

