"""Product-first, group-aware splitting + leakage audit."""
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit

def make_splits(m: pd.DataFrame, unknown_frac=0.2, val=0.15, cal=0.25, seed=0):
    """m columns: path, product_id, group_id, domain ('ref'|'phone'), stream.
    Returns m with 'split' in {gallery, val, cal, test, unknown_val, unknown_test}."""
    m = m.copy()
    rng = np.random.default_rng(seed)
    prods = np.array(sorted(m.product_id.unique()))
    rng.shuffle(prods)
    n_unk = int(round(len(prods) * unknown_frac))
    unk = set(prods[:n_unk])
    m["split"] = ""
    # Unknown products are split BY PRODUCT: half set the identification threshold tau (val),
    # the other half are touched only in the final test. Reusing the same unknowns for both would leak.
    unk_l = sorted(unk); unk_val = set(unk_l[: len(unk_l) // 2])
    m.loc[m.product_id.isin(unk_val), "split"] = "unknown_val"
    m.loc[m.product_id.isin(unk - unk_val), "split"] = "unknown_test"
    known = m[~m.product_id.isin(unk)]
    # reference-domain images of known products -> gallery (fit, no anomalies)
    m.loc[known.index[known.domain == "ref"], "split"] = "gallery"
    ph = known[known.domain == "phone"]
    idx = ph.index.to_numpy()
    grp = ph.group_id.to_numpy()
    # test gets the remainder; val/cal are carved (by group) from the rest
    gss = GroupShuffleSplit(n_splits=1, test_size=1 - (val + cal), random_state=seed)
    vc_pos, test_pos = next(gss.split(idx, groups=grp))
    m.loc[idx[test_pos], "split"] = "test"
    vc_idx = idx[vc_pos]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=cal / (val + cal), random_state=seed)
    v, c = next(gss2.split(vc_idx, groups=m.loc[vc_idx, "group_id"].to_numpy()))
    m.loc[vc_idx[v], "split"] = "val"
    m.loc[vc_idx[c], "split"] = "cal"
    return m

def assert_no_leak(m: pd.DataFrame):
    """No group may sit in two splits; no unknown product may appear in a known split."""
    g = m.groupby("group_id").split.nunique()
    bad = g[g > 1]
    assert bad.empty, f"{len(bad)} groups straddle splits, e.g. {list(bad.index[:5])}"
    unk = set(m[m.split.isin(["unknown_val", "unknown_test"])].product_id)
    leak = m[~m.split.isin(["unknown_val", "unknown_test"]) & m.product_id.isin(unk)]
    both = set(m[m.split == "unknown_val"].product_id) & set(m[m.split == "unknown_test"].product_id)
    assert not both, "a product is in both unknown_val and unknown_test"
    assert leak.empty, "unknown products leaked into known splits"
    assert (m.split != "").all(), "unassigned rows"
    return True
