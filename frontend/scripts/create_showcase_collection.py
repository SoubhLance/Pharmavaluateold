"""Create the isolated, provenance-checked six-medicine showcase.

The script reads the project manifests and split table, writes only within the
frontend directory, and stores the backend responses without rewriting them.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import shutil
import sys
import urllib.request
import zlib
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAME = os.environ.get("PHARMAVALUATE_SHOWCASE_DIR", "showcase")
OUTPUT_ROOT = FRONTEND_ROOT / OUTPUT_NAME
SPLIT_CSV = PROJECT_ROOT / "data" / "splits" / "pill_splits.csv"
RAW_MANIFEST = PROJECT_ROOT / "data" / "processed" / "pill_raw_manifest.csv"
TABLE_CSV = PROJECT_ROOT / "data" / "raw" / "c3pi_full" / "extracted" / "table.csv"
PILL_ROOT = PROJECT_ROOT / "data" / "processed" / "pill"
CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"
API_BASE = os.environ.get("PHARMAVALUATE_API", "http://127.0.0.1:8000").rstrip("/")

# Approved identity is the primary key. The image ID and split are explicit
# assertions that must agree with both source manifests before any output is made.
APPROVED_CANDIDATES = [
    {
        "medicine_name": "Warfarin Sodium 1 mg",
        "ndc": "00555-0831",
        "image_id": "000664",
        "expected_split": "val",
        "table_name_terms": ["Warfarin Sodium 1 MG"],
    },
    {
        "medicine_name": "Avandia / Rosiglitazone 8 mg",
        "ndc": "00029-3160",
        "image_id": "000070",
        "expected_split": "cal",
        "table_name_terms": ["rosiglitazone 8 MG", "[Avandia]"],
    },
    {
        "medicine_name": "Avodart / Dutasteride 0.5 mg",
        "ndc": "00173-0712",
        "image_id": "000516",
        "expected_split": "cal",
        "table_name_terms": ["Dutasteride 0.5 MG", "[Avodart]"],
    },
    {
        "medicine_name": "Combivir",
        "ndc": "49702-0202",
        "image_id": "000950",
        "expected_split": "val",
        "table_name_terms": ["Lamivudine 150 MG", "Zidovudine 300 MG", "[Combivir]"],
    },
    {
        "medicine_name": "Dyazide",
        "ndc": "00007-3650",
        "image_id": "000032",
        "expected_split": "val",
        "table_name_terms": ["Hydrochlorothiazide 25 MG", "Triamterene 37.5 MG", "[Dyazide]"],
    },
    {
        "medicine_name": "Metoclopramide 5 mg",
        "ndc": "00093-2204",
        "image_id": "000246",
        "expected_split": "cal",
        "table_name_terms": ["Metoclopramide 5 MG"],
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tamper_config() -> tuple[list[str], list[int]]:
    import yaml

    with CONFIG_PATH.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    types = list(config["tamper_types"]["pill"])
    severities = list(config["severities"])
    if not types or not severities:
        raise RuntimeError("The configured pill tamper list or severity list is empty")
    return types, severities


def load_table_by_product(table_rows: list[dict[str, str]]) -> dict[str, str]:
    """Map a project product ID to the source name in table.csv."""
    mapped: dict[str, set[str]] = {}
    for row in table_rows:
        ndc11 = row["ndc11"]
        parts = ndc11.rsplit("-", 1)
        if len(parts) == 2:
            mapped.setdefault(parts[0], set()).add(row["name"])
    return {product_id: " / ".join(sorted(names)) for product_id, names in mapped.items()}


def verify_candidates() -> list[dict]:
    split_rows = read_csv(SPLIT_CSV)
    manifest_rows = read_csv(RAW_MANIFEST)
    table_rows = read_csv(TABLE_CSV)
    split_by_stem = {Path(row["path"]).stem: row for row in split_rows}
    manifest_by_group = {row["group_id"]: row for row in manifest_rows}
    verified: list[dict] = []

    for approved in APPROVED_CANDIDATES:
        ndc = approved["ndc"]
        image_id = approved["image_id"]
        expected_split = approved["expected_split"]
        row = split_by_stem.get(image_id)
        if row is None:
            raise RuntimeError(f"No split entry for approved image ID {image_id} ({ndc})")
        if row["split"] != expected_split:
            raise RuntimeError(
                f"Split mismatch for {image_id}: {row['split']} != {expected_split}"
            )
        if row["split"] == "test":
            raise RuntimeError(f"Test-split candidate is prohibited: {image_id}")
        if row["product_id"] != ndc:
            raise RuntimeError(
                f"Approved NDC {ndc} does not match split product {row['product_id']} "
                f"for image {image_id}"
            )
        manifest = manifest_by_group.get(row["group_id"])
        if manifest is None:
            raise RuntimeError(f"No raw manifest entry for group {row['group_id']}")
        if manifest["product_id"] != ndc:
            raise RuntimeError(
                f"Approved NDC {ndc} does not match raw-manifest product "
                f"{manifest['product_id']} for group {row['group_id']}"
            )

        ndc_rows = [r for r in table_rows if r["ndc11"].startswith(ndc + "-")]
        names = {r["name"] for r in ndc_rows}
        if not ndc_rows or len(names) != 1:
            raise RuntimeError(f"Missing or ambiguous table.csv entry for approved NDC {ndc}")
        table_name = next(iter(names))
        missing_terms = [
            term for term in approved["table_name_terms"] if term.casefold() not in table_name.casefold()
        ]
        if missing_terms:
            raise RuntimeError(
                f"table.csv name mismatch for {ndc}: {table_name!r}; "
                f"missing expected terms {missing_terms}"
            )

        paths = {
            "clean": PILL_ROOT / "clean" / f"{image_id}.png",
            "mask": PILL_ROOT / "mask" / f"{image_id}.png",
            "original": PILL_ROOT / "jpg" / f"{image_id}.jpg",
        }
        for label, path in paths.items():
            if not path.is_file():
                raise RuntimeError(f"Missing {label} image asset for {ndc}: {path}")
        if Path(row["path"]).resolve() != paths["clean"].resolve():
            raise RuntimeError(f"Split image path mismatch for {image_id}")
        if Path(row["obj_mask"]).resolve() != paths["mask"].resolve():
            raise RuntimeError(f"Object mask path mismatch for {image_id}")

        verified.append(
            {
                "medicine_name": approved["medicine_name"],
                "ndc": ndc,
                "product_id": row["product_id"],
                "image_id": image_id,
                "split": row["split"],
                "group_id": row["group_id"],
                "domain": row["domain"],
                "stream": row["stream"],
                "table_ndc11": sorted(r["ndc11"] for r in ndc_rows),
                "table_name": table_name,
                "manifest_source": manifest["path"],
                "clean_source": str(paths["clean"]),
                "mask_source": str(paths["mask"]),
                "original_source": str(paths["original"]),
                "original_sha256": sha256(paths["original"]),
            }
        )

    if len({item["ndc"] for item in verified}) != len(APPROVED_CANDIDATES):
        raise RuntimeError("Approved candidates do not contain six distinct NDCs")
    return verified


def split_order_positions() -> dict[str, int]:
    # Mirror notebook 03's deterministic random_state=0 ordering and its
    # per-split phone sample order for severity assignment.
    import pandas as pd

    frame = pd.read_csv(SPLIT_CSV)
    positions: dict[str, int] = {}
    for split in ("val", "cal"):
        subset = frame[(frame["split"] == split) & (frame["domain"] == "phone")]
        ordered = subset.sample(frac=1, random_state=0)
        for position, path in enumerate(ordered["path"].tolist()):
            positions[f"{split}:{Path(path).stem}"] = position
    return positions


def get_health() -> dict:
    request = urllib.request.Request(f"{API_BASE}/health", method="GET")
    with urllib.request.urlopen(request, timeout=15) as response:
        health = json.loads(response.read().decode("utf-8"))
    if health.get("status") != "healthy":
        raise RuntimeError(f"Backend is not healthy: {health}")
    return health


def screen(path: Path) -> dict:
    boundary = "----PharmaValuateShowcaseBoundary"
    payload = path.read_bytes()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("ascii")
    body = head + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(
        f"{API_BASE}/screen",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def identify_result(candidate: dict, raw: dict, product_names: dict[str, str]) -> dict:
    outcome = raw.get("label")
    returned = raw.get("product_id")
    if outcome == "Retake Required":
        status = "not_attempted_quality_gate"
        predicted_id = None
    elif outcome == "Unknown Product" or returned == "Unknown Product":
        status = "identification_failure"
        predicted_id = None
    elif returned is None:
        status = "unavailable"
        predicted_id = None
    else:
        predicted_id = str(returned)
        status = "match" if predicted_id == candidate["ndc"] else "mismatch"
    return {
        "backend_predicted_product_id": predicted_id,
        "backend_predicted_product_label": product_names.get(predicted_id) if predicted_id else None,
        "identification_status": status,
        "screening_outcome": outcome,
    }


def write_report(items: list[dict], predictions: list[dict], health: dict, summary: dict) -> None:
    by_item: dict[str, list[dict]] = {}
    for prediction in predictions:
        by_item.setdefault(prediction["source_image_id"], []).append(prediction)

    cards = []
    for item in items:
        figures = []
        for row in by_item[item["image_id"]]:
            image_rel = Path(row["image_path"]).relative_to(OUTPUT_ROOT).as_posix()
            status = row["identification_status"]
            status_class = "mismatch" if status == "mismatch" else (
                "failure" if status in ("identification_failure", "not_attempted_quality_gate") else "match"
            )
            predicted_id = row["backend_predicted_product_id"] or (
                "Unknown Product" if status == "identification_failure" else "Not produced"
            )
            predicted_name = row["backend_predicted_product_label"] or "No identified product label"
            figures.append(
                "<figure>"
                f'<img src="{html.escape(image_rel)}" alt="{html.escape(row["synthetic_modification_type"])} image of {html.escape(item["medicine_name"])}">'
                '<figcaption>'
                f'<strong>{html.escape(row["synthetic_modification_type"])}</strong>'
                f'<span class="field"><b>Backend product ID:</b> {html.escape(str(predicted_id))}</span>'
                f'<span class="field"><b>Backend product label:</b> {html.escape(predicted_name)}</span>'
                f'<span class="field"><b>Identification:</b> <em class="{status_class}">{html.escape(status.replace("_", " "))}</em></span>'
                f'<span class="field"><b>Screening outcome:</b> {html.escape(str(row["screening_outcome"]))}</span>'
                '</figcaption><details><summary>Raw API response</summary><pre>'
                + html.escape(json.dumps(row["raw_response"], indent=2, ensure_ascii=False))
                + '</pre></details></figure>'
            )
        cards.append(
            '<article class="medicine">'
            '<header><div><span class="split">'
            f'{html.escape(item["split"])} split</span><h2>{html.escape(item["medicine_name"])}</h2>'
            f'<p>Approved NDC {html.escape(item["ndc"])} · Source image {html.escape(item["image_id"])} · Group {html.escape(item["group_id"])}</p>'
            f'<p class="table-name">Source table: {html.escape(item["table_name"])}</p></div></header>'
            '<div class="gallery">' + "".join(figures) + '</div>'
            f'<details class="provenance"><summary>Manifest provenance</summary><p>Raw source: <code>{html.escape(item["manifest_source"])}</code></p>'
            f'<p>Original SHA-256: <code>{item["original_sha256"]}</code></p></details>'
            '</article>'
        )

    label_counts = summary["screening_outcome_counts"]
    status_counts = summary["identification_status_counts"]
    cards_html = "\n".join(cards)
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PharmaValuate approved medicine showcase</title>
<style>
:root{{color-scheme:light;--ink:#142b3a;--muted:#63798a;--line:#dce6eb;--teal:#087f83;--wash:#f2f7f8;--amber:#b97612;--red:#b43d49;--green:#087d56}}
*{{box-sizing:border-box}}body{{margin:0;background:#f4f7fa;color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{width:min(1600px,calc(100% - 40px));margin:32px auto 64px}}h1{{margin:8px 0;font-size:32px}}h2{{margin:5px 0;font-size:22px}}p{{margin:4px 0;color:var(--muted)}}
.eyebrow{{color:var(--teal);font:700 12px/1.4 ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase}}
.notice,.summary,.medicine{{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 28px #122d3a0a}}
.notice{{padding:16px 18px;margin:20px 0;border-left:4px solid var(--amber)}}.summary{{padding:18px;margin:20px 0;display:flex;flex-wrap:wrap;gap:18px 30px}}.summary strong{{font-size:20px;display:block}}
.medicine{{margin:18px 0;padding:20px}}.medicine header{{margin-bottom:16px}}.split{{display:inline-block;border-radius:999px;padding:5px 10px;background:#eaf5f5;color:var(--teal);font-size:12px;font-weight:700}}
.table-name{{font-size:13px}}.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
figure{{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--wash)}}figure img{{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:#e9eff2}}
figcaption{{padding:11px 12px;font-size:13px;color:var(--muted)}}figcaption strong{{font-size:15px;color:var(--ink);display:block;margin-bottom:6px}}.field{{display:block;margin-top:3px}}em{{font-style:normal;font-weight:700;text-transform:capitalize}}.match{{color:var(--green)}}.mismatch{{color:var(--red)}}.failure{{color:var(--amber)}}
details{{margin-top:10px;border-top:1px solid var(--line);padding:9px 12px}}summary{{cursor:pointer;font-weight:700;color:var(--teal)}}code,pre{{font:12px/1.5 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}}pre{{max-height:380px;overflow:auto;padding:12px;background:#f2f6f8;border-radius:8px}}
@media(max-width:600px){{main{{width:calc(100% - 24px);margin-top:18px}}h1{{font-size:27px}}.medicine{{padding:14px}}.gallery{{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}figcaption{{padding:8px;font-size:12px}}}}
</style></head><body><main>
<div class="eyebrow">PharmaValuate · Visual screening showcase</div><h1>Approved medicine image comparisons</h1>
<p>Frozen-model screening aid and synthetic stress-test examples. Model outputs are raw backend responses; no expected classification was imposed.</p>
<section class="notice"><strong>Split integrity:</strong> Calibration and validation examples retain their original split labels and are showcase examples, not independent test results. No test-split image was selected. A product identification mismatch is reported separately from the screening outcome.</section>
<section class="summary"><div><strong>{summary['candidate_count']}</strong> approved medicines</div><div><strong>{summary['prediction_count']}</strong> raw backend responses</div><div><strong>{status_counts.get('mismatch', 0)}</strong> product ID mismatches</div><div><strong>{status_counts.get('identification_failure', 0)}</strong> identification failures</div><div><strong>{html.escape(str(health.get('device', 'unknown')))}</strong> backend device</div></section>
<p class="eyebrow">Raw screening outcomes: {html.escape(json.dumps(label_counts, ensure_ascii=False))}</p>
{cards_html}
<p class="eyebrow">Screening aid only · Verify manually</p>
</main></body></html>"""
    (OUTPUT_ROOT / "report.html").write_text(html_doc, encoding="utf-8")


def main() -> None:
    if OUTPUT_ROOT.resolve().parent != FRONTEND_ROOT.resolve():
        raise RuntimeError("Showcase output must remain directly inside the frontend workspace")
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Output directory exists; refusing to overwrite: {OUTPUT_ROOT}")

    # All six candidate identities are validated before the output directory is created.
    items = verify_candidates()
    health = get_health()
    project_parent = str(PROJECT_ROOT)
    if project_parent not in sys.path:
        sys.path.insert(0, project_parent)
    from pv import tamper

    tamper_types, severities = load_tamper_config()
    positions = split_order_positions()
    table_rows = read_csv(TABLE_CSV)
    product_names = load_table_by_product(table_rows)
    OUTPUT_ROOT.mkdir(parents=True)
    predictions: list[dict] = []

    for item in items:
        candidate_dir = OUTPUT_ROOT / "images" / item["image_id"]
        candidate_dir.mkdir(parents=True)
        original = candidate_dir / "original.jpg"
        shutil.copy2(item["original_source"], original)
        variants: list[tuple[str, int | None, Path]] = [("original", None, original)]

        if item["split"] in ("cal", "val"):
            clean_path = Path(item["clean_source"])
            mask_path = Path(item["mask_source"])
            clean_bgr = cv2.imread(str(clean_path), cv2.IMREAD_COLOR)
            mask_gray = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if clean_bgr is None or mask_gray is None:
                raise RuntimeError(f"Image/mask decode error for {item['image_id']}")
            object_mask = mask_gray > 0
            image_rgb = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2RGB)
            if object_mask.shape != image_rgb.shape[:2]:
                raise RuntimeError(f"Image/mask shape mismatch for {item['image_id']}")
            position = positions[f"{item['split']}:{item['image_id']}"]
            for type_index, tamper_name in enumerate(tamper_types):
                severity = severities[(position + type_index) % len(severities)]
                seed = zlib.crc32(
                    f"{item['clean_source']}|{tamper_name}|{severity}".encode("utf-8")
                )
                changed, changed_mask = tamper.apply(
                    tamper_name, image_rgb, object_mask, severity, seed
                )
                variant_path = candidate_dir / f"{tamper_name}_s{severity}.jpg"
                tamper.reencode(changed, variant_path)
                mask_out = candidate_dir / f"{tamper_name}_s{severity}_mask.png"
                cv2.imwrite(str(mask_out), changed_mask.astype("uint8") * 255)
                variants.append((tamper_name, severity, variant_path))

        for modification, severity, image_path in variants:
            raw = screen(image_path)
            inferred = identify_result(item, raw, product_names)
            predictions.append(
                {
                    "source_medicine_name": item["medicine_name"],
                    "source_ndc": item["ndc"],
                    "source_product_id": item["product_id"],
                    "source_image_id": item["image_id"],
                    "original_split": item["split"],
                    "group_id": item["group_id"],
                    "synthetic_modification_type": modification,
                    "synthetic_modification_severity": severity,
                    "image_path": str(image_path),
                    "image_sha256": sha256(image_path),
                    **inferred,
                    "raw_response": raw,
                }
            )
            print(
                f"{item['medicine_name']} [{item['split']}] {modification}: "
                f"{inferred['screening_outcome']} / {inferred['identification_status']}"
            )

    outcome_counts: dict[str, int] = {}
    id_counts: dict[str, int] = {}
    for row in predictions:
        outcome = str(row["screening_outcome"] or "<missing>")
        status = row["identification_status"]
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        id_counts[status] = id_counts.get(status, 0) + 1
    mismatches = [
        {
            "source_medicine_name": row["source_medicine_name"],
            "source_ndc": row["source_ndc"],
            "source_image_id": row["source_image_id"],
            "synthetic_modification_type": row["synthetic_modification_type"],
            "backend_predicted_product_id": row["backend_predicted_product_id"],
            "backend_predicted_product_label": row["backend_predicted_product_label"],
            "screening_outcome": row["screening_outcome"],
        }
        for row in predictions
        if row["identification_status"] == "mismatch"
    ]
    summary = {
        "health": health,
        "candidate_count": len(items),
        "prediction_count": len(predictions),
        "source_split_counts": {
            split: sum(1 for item in items if item["split"] == split)
            for split in sorted({item["split"] for item in items})
        },
        "tamper_types": tamper_types,
        "configured_severities": severities,
        "screening_outcome_counts": outcome_counts,
        "identification_status_counts": id_counts,
        "identification_mismatches": mismatches,
        "source_data_modified": False,
        "test_split_used": False,
        "calibration_validation_are_independent_test_results": False,
    }
    (OUTPUT_ROOT / "candidates.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_ROOT / "predictions.json").write_text(
        json.dumps(predictions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_report(items, predictions, health, summary)

    candidate_lines = "\n".join(
        f"- **{item['medicine_name']}** — NDC `{item['ndc']}`, image `{item['image_id']}`, split `{item['split']}`"
        for item in items
    )
    outcome_lines = "\n".join(
        f"- `{label}`: {count} raw API responses"
        for label, count in sorted(outcome_counts.items())
    )
    mismatch_lines = "\n".join(
        f"- `{m['source_image_id']}` {m['source_medicine_name']} ({m['source_ndc']}) → "
        f"`{m['backend_predicted_product_id']}` {m['backend_predicted_product_label']} "
        f"({m['screening_outcome']})"
        for m in mismatches
    ) or "- None recorded."
    readme = f"""# PharmaValuate approved-candidate showcase

This isolated collection uses the six approved candidates after validating their image IDs, original splits, product IDs, raw manifest groups, and `table.csv` NDC/name entries. Predictions are preserved as returned by the live backend; no target label was imposed. Backend device: `{health.get('device', 'unknown')}`. Disclaimer: `{health.get('disclaimer', '')}`.

## Verified candidates

{candidate_lines}

Calibration and validation samples are showcase examples, **not independent test results**. No test image was selected. Original project datasets, split assignments, frozen models, calibration values, and thresholds were not modified.

## Files

- `report.html` — visual comparisons with source identity, backend-predicted identity, identification status, screening outcome, and expandable raw response per image.
- `candidates.json` — approved identity and source-manifest provenance.
- `predictions.json` — source fields, derived identification comparison, synthetic-modification metadata, and exact raw API responses.
- `summary.json` — generated split/outcome/identification counts and mismatch list.
- `images/<image_id>/original.jpg` — retained original image.
- `images/<image_id>/*_s*.jpg` — deterministic synthetic pill variants for cal/val samples, using configured types and severities.
- `images/<image_id>/*_mask.png` — synthetic modification masks.

## Raw backend screening outcomes

{outcome_lines}

## Product identification mismatches

{mismatch_lines}

Synthetic modifications are screening stress tests, not claims about real-counterfeit accuracy. `Unknown Product` means identification failed; it is not a counterfeit result. `Retake Required` means the image quality gate did not pass.
"""
    (OUTPUT_ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Showcase report: {OUTPUT_ROOT / 'report.html'}")


if __name__ == "__main__":
    main()
