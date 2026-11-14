# %% [markdown]
# # 11 - OCR + text rules (T5)
# EasyOCR reads the packaging crop; plain-Python rules check expiry/batch format and (if metadata exists) the product name. T5 asks: does OCR add recall that visual scoring misses? Evaluated on the **val** split here; repeat on test in notebook 12 if you keep it.
# %%
import sys, os; sys.path.insert(0, os.path.abspath(".."))
from pv.config import *
from pv.ocr_rules import check_text
import numpy as np, pandas as pd, cv2, easyocr
from tqdm import tqdm
STREAM = "pack"
reader = easyocr.Reader(["en"], gpu=True)
all_df = pd.read_csv(SPLITS / f"{STREAM}_all.csv")
val = all_df[(all_df.split == "val") & (all_df.domain == "phone")]
sub = pd.concat([val[val.label == 0].sample(min(300, (val.label == 0).sum()), random_state=0), val[val.tamper == "font_sub"].sample(min(300, (val.tamper == "font_sub").sum()), random_state=0)])
# %%
def read(path): return " ".join(reader.readtext(path, detail=0, paragraph=False))
rows = []
for r in tqdm(sub.itertuples(), total=len(sub)):
    txt = read(r.path); rows.append(dict(path=r.path, label=r.label, tamper=r.tamper, text=txt, flags=";".join(check_text(txt))))
o = pd.DataFrame(rows); o["ocr_flag"] = o.flags != ""
print("OCR flag rate  genuine:", o[o.label == 0].ocr_flag.mean(), " font_sub tamper:", o[o.label == 1].ocr_flag.mean())
o.to_csv(RES / "tables" / "ocr_val.csv", index=False)
# %% [markdown]
# Next: join with the visual detector's val scores (`results/scores/*__pack__val.csv`) and compute recall of tampers at the fixed visual threshold with and without `ocr_flag` (OR rule). Report both - if OCR false-alarms on many genuine images, say so.
# %%
vis = pd.read_csv(SCORES / "anomalydino_best__pack__val.csv").dropna(subset=["score"]).merge(o[["path", "ocr_flag"]], on="path", how="inner")
th = vis[vis.label == 0].score.quantile(0.99)
tam = vis[vis.label == 1]; gen = vis[vis.label == 0]
print(f"visual-only recall {(tam.score>th).mean():.3f}   visual+OCR recall {((tam.score>th)|tam.ocr_flag).mean():.3f}")
print(f"genuine false-alarm  visual {(gen.score>th).mean():.3f}   visual+OCR {((gen.score>th)|gen.ocr_flag).mean():.3f}")
