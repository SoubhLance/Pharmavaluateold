import numpy as np
def conformal_pvalue(cal_scores, s):
    cal = np.asarray(cal_scores)
    return (1 + np.sum(cal >= s)) / (len(cal) + 1)

def pvalues(cal_scores, scores):
    cal = np.sort(np.asarray(cal_scores)); n = len(cal)
    ge = n - np.searchsorted(cal, np.asarray(scores), side="left")   # count(cal >= s)
    return (1 + ge) / (n + 1)

def min_cal_size(alpha):
    """Smallest calibration set for which p can reach alpha."""
    return int(np.ceil(1 / alpha - 1))

def decide(p, alpha_cf=0.01, alpha_gen=0.20):
    if p <= alpha_cf: return "Likely Counterfeit"
    if p <= alpha_gen: return "Inconclusive"
    return "Likely Genuine"

def fuse(p_a, p_b):
    return min(1.0, 2 * min(p_a, p_b))

class Mondrian:
    """Separate calibration per (stream, domain) cell."""
    def __init__(self): self.cells = {}
    def fit(self, df, score_col="score", keys=("stream", "domain")):
        for k, g in df.groupby(list(keys)):
            self.cells[k] = np.sort(g[score_col].to_numpy())
            if len(g) < min_cal_size(0.01):
                print(f"WARNING cell {k}: n={len(g)} < {min_cal_size(0.01)} -> alpha=0.01 unreachable")
        return self
    def p(self, key, s): return float(pvalues(self.cells[key], [s])[0])
