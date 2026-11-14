"""Convert nb_src/*.py (percent format) into notebooks/*.ipynb. Run: python tools/build_notebooks.py"""
import json, re, ast, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
def convert(src):
    cells, cur, kind = [], [], "code"
    def flush():
        nonlocal cur
        body = "\n".join(cur).strip("\n")
        if body.strip():
            if kind == "markdown":
                body = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in body.split("\n"))
                cells.append({"cell_type": "markdown", "metadata": {}, "source": body.splitlines(True)})
            else:
                ast.parse(body)   # syntax check
                cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": body.splitlines(True)})
        cur = []
    for line in src.split("\n"):
        if line.startswith("# %%"):
            flush(); kind = "markdown" if "[markdown]" in line else "code"
        else: cur.append(line)
    flush()
    return {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks"; out.mkdir(exist_ok=True)
for f in sorted((ROOT / "nb_src").glob("*.py")):
    nb = convert(f.read_text()); (out / (f.stem + ".ipynb")).write_text(json.dumps(nb, indent=1)); print("built", f.stem, len(nb["cells"]), "cells")
