# PharmaValuate six-medicine showcase

This is a separate visual screening showcase and synthetic stress-test collection. Model labels below are raw responses from the running FastAPI backend; no expected classification was forced. Backend device: `cuda`. Disclaimer: `screening aid, verify manually`.

Calibration and validation samples retain their original split labels and are **not independent test results**. The collection includes `unknown_val` samples so product-identification failures and `Unknown Product` outcomes remain visible. No `test` split sample was selected. Source gallery, calibration, validation, and test datasets remain untouched.

## Six verified candidates

- `000009` ? `00002-3250` ? `cal` ? group `00002-3250_g9`
- `000018` ? `00004-0260` ? `cal` ? group `00004-0260_g18`
- `000004` ? `00002-3239` ? `val` ? group `00002-3239_g4`
- `000013` ? `00002-4771` ? `val` ? group `00002-4771_g13`
- `000010` ? `00002-4462` ? `unknown_val` ? group `00002-4462_g10`
- `000038` ? `00007-4640` ? `unknown_val` ? group `00007-4640_g38`

## Files

- `report.html` ? visual comparison for all six medicines, with source split provenance and expandable raw API responses.
- `candidates.json` ? verified split and raw-manifest provenance plus retained-original hashes.
- `predictions.json` ? exact backend response objects plus image and split metadata.
- `summary.json` ? generated collection counts and raw response label counts.
- `images/<image_id>/original.jpg` ? retained original for each medicine.
- `images/<image_id>/*_s*.jpg` ? deterministic synthetic pill modifications for calibration and validation samples.
- `images/<image_id>/*_mask.png` ? corresponding synthetic modification masks.

## Raw backend labels

- `Inconclusive`: 9 raw responses
- `Likely Genuine`: 4 raw responses
- `Retake Required`: 2 raw responses
- `Unknown Product`: 3 raw responses

Synthetic modifications use the configured pill tamper types/severities and existing deterministic CRC32 seed recipe. They are screening stress tests, not claims about real-counterfeit accuracy.
