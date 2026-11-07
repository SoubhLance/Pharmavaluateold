"""Synthetic tamper generator. Every tamper returns (image, mask) with a fixed rng.
Genuine images MUST also go through reencode() so detectors cannot learn JPEG traces."""
import cv2, numpy as np

def _bbox(obj_mask, shape):
    if obj_mask is None or obj_mask.sum() == 0:
        h, w = shape[:2]; return 0, 0, w, h
    ys, xs = np.where(obj_mask); return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

def _rand_rect(rng, bb, frac, obj_mask=None):
    x0, y0, x1, y1 = bb; w, h = x1 - x0, y1 - y0
    rw, rh = max(6, int(w * frac)), max(6, int(h * frac * 0.6))
    for _ in range(30):
        x = int(rng.integers(x0, max(x0 + 1, x1 - rw))); y = int(rng.integers(y0, max(y0 + 1, y1 - rh)))
        if obj_mask is None or obj_mask[y:y + rh, x:x + rw].mean() > 0.8: break
    return x, y, rw, rh

def _rect_mask(shape, x, y, w, h):
    m = np.zeros(shape[:2], bool); m[y:y + h, x:x + w] = True; return m

SEV_FRAC = {1: 0.18, 2: 0.30, 3: 0.45}

def imprint(img, obj_mask, sev, rng):
    """Blur / smear a region (stand-in for altered engraving or print)."""
    x, y, w, h = _rand_rect(rng, _bbox(obj_mask, img.shape), SEV_FRAC[sev], obj_mask)
    out = img.copy(); k = 3 + 4 * sev
    roi = out[y:y + h, x:x + w]; out[y:y + h, x:x + w] = cv2.GaussianBlur(roi, (k | 1, k | 1), 0)
    if sev >= 2:   # inpaint random strokes
        st = np.zeros(img.shape[:2], np.uint8)
        for _ in range(3 * sev):
            p1 = (int(rng.integers(x, x + w)), int(rng.integers(y, y + h)))
            p2 = (int(rng.integers(x, x + w)), int(rng.integers(y, y + h)))
            cv2.line(st, p1, p2, 255, 1 + sev)
        out = cv2.inpaint(out, st, 3, cv2.INPAINT_TELEA)
    return out, _rect_mask(img.shape, x, y, w, h)

def font_sub(img, obj_mask, sev, rng):
    """Cover a region with text drawn in a different font/size (batch/expiry/name tamper)."""
    x, y, w, h = _rand_rect(rng, _bbox(obj_mask, img.shape), SEV_FRAC[sev] + 0.1, obj_mask)
    out = img.copy(); roi = out[y:y + h, x:x + w]
    bg = np.median(roi.reshape(-1, 3), 0).astype(np.uint8); out[y:y + h, x:x + w] = bg
    fonts = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_COMPLEX, cv2.FONT_HERSHEY_TRIPLEX, cv2.FONT_HERSHEY_SCRIPT_SIMPLEX]
    txt = "B" + str(int(rng.integers(1000, 9999))) + " EXP 08/27"
    col = tuple(int(c) for c in (255 - bg))
    scale = max(0.3, min(w / 180, h / 20)) * (0.8 + 0.1 * sev)
    cv2.putText(out, txt, (x + 2, y + h - max(2, h // 4)), fonts[int(rng.integers(0, len(fonts)))], scale, col, 1, cv2.LINE_AA)
    return out, _rect_mask(img.shape, x, y, w, h)

def color_gloss(img, obj_mask, sev, rng):
    m = obj_mask if obj_mask is not None else np.ones(img.shape[:2], bool)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
    sign = rng.choice([-1, 1])
    hsv[..., 0] = np.where(m, (hsv[..., 0] + sign * 3 * sev) % 180, hsv[..., 0])
    hsv[..., 1] = np.where(m, np.clip(hsv[..., 1] * (1 + sign * 0.08 * sev), 0, 255), hsv[..., 1])
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    if sev >= 2:   # specular highlight
        bb = _bbox(m, img.shape); cx = int(rng.integers(bb[0], bb[2])); cy = int(rng.integers(bb[1], bb[3]))
        hl = np.zeros(img.shape[:2], np.float32); cv2.circle(hl, (cx, cy), 6 * sev, 1.0, -1)
        hl = cv2.GaussianBlur(hl, (0, 0), 4) * 120 * (m)
        out = np.clip(out.astype(np.float32) + hl[..., None], 0, 255).astype(np.uint8)
    return out, m.copy()

def edge_chip(img, obj_mask, sev, rng):
    assert obj_mask is not None, "edge_chip needs an object mask"
    cnts, _ = cv2.findContours(obj_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=cv2.contourArea)[:, 0, :]; px, py = c[int(rng.integers(0, len(c)))]
    r = int(4 + 4 * sev * max(1, min(obj_mask.shape) / 128))
    chip = np.zeros(img.shape[:2], np.uint8); cv2.circle(chip, (int(px), int(py)), r, 1, -1)
    chip = chip.astype(bool) & obj_mask
    ring = cv2.dilate(obj_mask.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~obj_mask
    bg = np.median(img[ring].reshape(-1, 3), 0).astype(np.uint8) if ring.any() else np.array([128] * 3, np.uint8)
    out = img.copy(); out[chip] = bg
    return out, chip

def misregistration(img, obj_mask, sev, rng):
    x, y, w, h = _rand_rect(rng, _bbox(obj_mask, img.shape), SEV_FRAC[sev] + 0.1, obj_mask)
    out = img.copy(); ch = int(rng.integers(0, 3)); dx = int(rng.choice([-1, 1])) * sev
    roi = out[y:y + h, x:x + w, ch]; out[y:y + h, x:x + w, ch] = np.roll(roi, dx, axis=1)
    return out, _rect_mask(img.shape, x, y, w, h)

def texture(img, obj_mask, sev, rng):
    bb = _bbox(obj_mask, img.shape)
    x, y, w, h = _rand_rect(rng, bb, SEV_FRAC[sev], obj_mask); sx, sy, _, _ = _rand_rect(rng, bb, SEV_FRAC[sev], obj_mask)
    patch = img[sy:sy + h, sx:sx + w]; patch = cv2.resize(patch, (w, h))
    patch = cv2.resize(cv2.resize(patch, (max(2, w // (1 + sev)), max(2, h // (1 + sev)))), (w, h), interpolation=cv2.INTER_NEAREST)
    out = img.copy(); out[y:y + h, x:x + w] = patch
    return out, _rect_mask(img.shape, x, y, w, h)

TAMPERS = dict(imprint=imprint, font_sub=font_sub, color_gloss=color_gloss, edge_chip=edge_chip,
               misregistration=misregistration, texture=texture)

def apply(name, img, obj_mask, sev, seed):
    return TAMPERS[name](img, obj_mask, sev, np.random.default_rng(seed))

def reencode(img_rgb, path, quality=92):
    """Identical save pipeline for genuine AND tampered images."""
    cv2.imwrite(str(path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
