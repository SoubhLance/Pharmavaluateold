# PharmaValuate approved-candidate showcase

This isolated collection uses the six approved candidates after validating their image IDs, original splits, product IDs, raw manifest groups, and `table.csv` NDC/name entries. Predictions are preserved as returned by the live backend; no target label was imposed. Backend device: `cuda`. Disclaimer: `screening aid, verify manually`.

## Verified candidates

- **Warfarin Sodium 1 mg** — NDC `00555-0831`, image `000664`, split `val`
- **Avandia / Rosiglitazone 8 mg** — NDC `00029-3160`, image `000070`, split `cal`
- **Avodart / Dutasteride 0.5 mg** — NDC `00173-0712`, image `000516`, split `cal`
- **Combivir** — NDC `49702-0202`, image `000950`, split `val`
- **Dyazide** — NDC `00007-3650`, image `000032`, split `val`
- **Metoclopramide 5 mg** — NDC `00093-2204`, image `000246`, split `cal`

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

- `Inconclusive`: 4 raw API responses
- `Likely Genuine`: 2 raw API responses
- `Retake Required`: 4 raw API responses
- `Unknown Product`: 14 raw API responses

## Product identification mismatches

- `000246` Metoclopramide 5 mg (00093-2204) → `59630-0701` prednisolone 15 MG Disintegrating Oral Tablet [Orapred] (Inconclusive)
- `000246` Metoclopramide 5 mg (00093-2204) → `59630-0701` prednisolone 15 MG Disintegrating Oral Tablet [Orapred] (Inconclusive)

Synthetic modifications are screening stress tests, not claims about real-counterfeit accuracy. `Unknown Product` means identification failed; it is not a counterfeit result. `Retake Required` means the image quality gate did not pass.
