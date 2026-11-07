import cv2, numpy as np
def quality_metrics(img_rgb):
    g = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    blur = cv2.Laplacian(g, cv2.CV_64F).var()
    glare = float((g >= 250).mean())
    return dict(blur=blur, glare=glare, mean_lum=float(g.mean()), dark=float((g <= 10).mean()))

def passes(q, th):
    return (q["blur"] >= th["blur_min"] and q["glare"] <= th["glare_max"]
            and th["lum_min"] <= q["mean_lum"] <= th["lum_max"])

def fit_thresholds(qdf, keep=0.95):
    """Pick thresholds on VALIDATION phone images so ~keep of good images pass (each criterion ~ keep^(1/3))."""
    p = (1 - keep ** (1 / 3))
    return dict(blur_min=float(qdf.blur.quantile(p)), glare_max=float(qdf.glare.quantile(1 - p)),
                lum_min=float(qdf.mean_lum.quantile(p / 2)), lum_max=float(qdf.mean_lum.quantile(1 - p / 2)))
