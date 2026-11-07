import torch
class PatchMemory:
    """Reference patch bank + nearest-neighbour scoring. No gradient training.
    Uses torch.cdist in chunks (no FAISS needed; fine for per-product banks)."""
    def __init__(self, coreset_ratio=1.0, topfrac=0.01, device="cuda", seed=0):
        self.ratio, self.topfrac, self.device, self.seed = coreset_ratio, topfrac, device, seed
        self.bank = None
    @torch.no_grad()
    def _coreset(self, X):
        n = X.shape[0]; k = max(1, int(n * self.ratio))
        if k >= n: return X
        g = torch.Generator(device="cpu").manual_seed(self.seed)
        P = torch.randn(X.shape[1], 128, generator=g).to(X.device); Z = X @ P
        sel = [int(torch.randint(0, n, (1,), generator=g))]
        d = torch.cdist(Z, Z[sel[0]][None]).squeeze(1)
        for _ in range(k - 1):
            i = int(torch.argmax(d)); sel.append(i)
            d = torch.minimum(d, torch.cdist(Z, Z[i][None]).squeeze(1))
        return X[sel]
    def fit(self, feats):               # feats (N, D)
        X = feats.to(self.device).float()
        self.bank = self._coreset(X); return self
    @torch.no_grad()
    def patch_dist(self, q, chunk=4096):  # q (N, D) -> (N,)
        q = q.to(self.device).float(); out = []
        for i in range(0, q.shape[0], chunk):
            out.append(torch.cdist(q[i:i + chunk], self.bank).min(1).values)
        return torch.cat(out)
    def score(self, q):                 # q (N, D) -> (image_score, patch_dist)
        d = self.patch_dist(q); k = max(1, int(len(d) * self.topfrac))
        return float(d.topk(k).values.mean()), d
    @property
    def size(self): return 0 if self.bank is None else int(self.bank.shape[0])
