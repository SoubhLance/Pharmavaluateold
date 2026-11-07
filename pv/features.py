import torch, timm, torch.nn.functional as F, numpy as np, cv2
from PIL import Image

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1); STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

BACKBONES = {   # timm name -> out_indices for stride-8 and stride-16 maps
    "resnet18": (2, 3), "wide_resnet50_2": (2, 3), "efficientnet_b0": (2, 3), "convnext_tiny": (1, 2),
}

def to_tensor(imgs_rgb):
    x = torch.from_numpy(np.stack(imgs_rgb)).permute(0, 3, 1, 2).float() / 255.0
    return (x - MEAN) / STD

def load_rgb(path, size=None):
    im = np.array(Image.open(path).convert("RGB"))
    return cv2.resize(im, (size, size), interpolation=cv2.INTER_AREA) if size else im

class CNNPatch(torch.nn.Module):
    """PatchCore-style local features: two layers, 3x3 avg-pool, upsample, concat, optional dim reduction."""
    def __init__(self, name="wide_resnet50_2", out_dim=512, device="cuda"):
        super().__init__()
        self.m = timm.create_model(name, pretrained=True, features_only=True, out_indices=BACKBONES[name]).eval().to(device)
        self.device, self.out_dim = device, out_dim
    @torch.no_grad()
    def forward(self, x):
        fs = [F.avg_pool2d(f, 3, 1, 1) for f in self.m(x.to(self.device))]
        sz = fs[0].shape[-2:]
        fs = [fs[0]] + [F.interpolate(f, size=sz, mode="bilinear", align_corners=False) for f in fs[1:]]
        f = torch.cat(fs, 1); B, C, H, W = f.shape
        f = f.permute(0, 2, 3, 1).reshape(B, H * W, C)
        if self.out_dim and C != self.out_dim:
            f = F.adaptive_avg_pool1d(f, self.out_dim)
        return f, (H, W)

class DinoPatch(torch.nn.Module):
    """Frozen DINOv2 ViT-S/14: patch tokens + CLS embedding."""
    def __init__(self, device="cuda", name="dinov2_vits14"):
        super().__init__()
        self.m = torch.hub.load("facebookresearch/dinov2:main", name, trust_repo=True, skip_validation=True).eval().to(device); self.device = device
    @torch.no_grad()
    def forward(self, x):
        o = self.m.forward_features(x.to(self.device))
        return o["x_norm_patchtokens"], o["x_norm_clstoken"]
