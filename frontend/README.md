# PharmaValuate Frontend (Pill Stream)

> **Notice:** Screening aid, verify manually. Never claim a pill is authentic or safe.

Polished React + TypeScript + Vite frontend for **PharmaValuate** (pill stream), connected to the FastAPI inference backend. Evaluates uploaded medicine photos against a frozen reference catalog using OpenCV quality checks, DINOv2 retrieval, AnomalyDINO patch memory matching, and split-conformal p-values.

---

## Architecture & Features

- **No external runtime CDN:** Self-contained bundle with zero external runtime stylesheets or scripts.
- **Upload Area:** Supports file picker (`.jpg`, `.jpeg`, `.png`, `.webp`), drag-and-drop, clipboard paste (`Ctrl+V`), image preview with dimensions/size, Screen button, and Clear button.
- **Result Card:**
  - Large color-coded label badges:
    - **Likely Genuine** (Green): *"Consistent with genuine references, not a guarantee."*
    - **Inconclusive** (Amber): *"Anomaly score is borderline; inspection cannot confirm consistency with references. Manual verification required."*
    - **Likely Counterfeit** (Red): *"Significant visual deviation detected compared to genuine product references. Manual verification required."*
    - **Retake Required** (Grey): *"Image failed capture quality gate (blur, glare, or improper lighting). Please retake a clear photo."*
    - **Unknown Product** (Grey): *"Product could not be identified against reference catalog with sufficient confidence (best similarity below &tau; = 0.8538)."*
- **P-Value Decision Bands:** Horizontal bar displaying the three conformal bands (`p <= 0.01` Counterfeit, `0.01 < p <= 0.50` Inconclusive, `p > 0.50` Genuine) with a pinpoint marker. Hidden when `p_value` is `null`.
- **Quality Gate Panel:** Evaluates blur sharpness against `blur_min`, glare against `glare_max`, mean luminance against `[lum_min, lum_max]`, and dark fraction.
- **Product Identification Panel:** Top-5 candidate products with horizontal similarity bars, an explicit threshold line drawn at `&tau; = 0.8538`, and a warning note when best match falls below threshold.
- **Raw JSON Viewer:** Collapsible `<details>` section (collapsed by default) with syntax-styled code and a **Copy JSON** button with feedback.
- **In-Memory Session History:** Keeps the last 10 screenings in React memory only (no `localStorage`). Click any thumbnail to reload that screening result.
- **Method & Evaluation Page:** Tab with full 4-step pipeline details, clearly labeled "Evaluation (synthetic stress test)" table with frozen v1 numbers, and a limitations list.
- **Offline Health Polling:** Background poller checks `GET /health` every 10 seconds. If backend is offline, surfaces a sticky offline banner with a manual retry button.
- **Accessible & Responsive:** WCAG AA/AAA contrast ratios, keyboard navigation, focus rings, responsive on mobile (tested at 390px), and dark mode via `prefers-color-scheme` or theme toggle button.

---

## Windows PowerShell Quickstart

### 1. Start the FastAPI Backend

Open Windows PowerShell and run:

```powershell
cd D:\pharmavaluate
D:\pharmavaluate\venv\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Verify backend health:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected output:
```json
{
  "status": "healthy",
  "device": "cuda",
  "stream": "pill",
  "gallery_products": 480,
  "disclaimer": "screening aid, verify manually"
}
```

---

### 2. Development Mode (Vite Dev Server)

In a new Windows PowerShell terminal:

```powershell
cd D:\pharmavaluate\frontend
npm install
npm run dev
```

Open your browser at **http://127.0.0.1:5173**.
Requests to `/health` and `/screen` are automatically proxied by Vite to `http://127.0.0.1:8000`.

---

### 3. Production Build & FastAPI Serving

To build the production bundle:

```powershell
cd D:\pharmavaluate\frontend
npm run build
```

This compiles optimized static assets into `D:\pharmavaluate\frontend\dist\`.

FastAPI serves the built frontend directly:
- **Main App:** Open **http://127.0.0.1:8000/** in your browser.
- **Legacy Demo:** Reachable at **http://127.0.0.1:8000/demo**.
- **Interactive OpenAPI Docs:** Reachable at **http://127.0.0.1:8000/docs**.

---

### 4. Running Automated Verification & Capturing Screenshots

To run the automated Puppeteer end-to-end verification and generate screenshots:

```powershell
cd D:\pharmavaluate\frontend
node scripts/verify_and_screenshot.cjs
node scripts/test_offline_banner.cjs
```

Generated screenshots are saved in `frontend/screenshots/`:
- `likely_genuine.png` (Likely Genuine result with calibration image)
- `inconclusive.png` (Inconclusive result with validation image)
- `unknown_product.png` (Unknown product rejection below &tau;)
- `retake_required.png` (Quality gate failure with blank/blurred image)
- `about_page.png` (Methodology, benchmark evaluation table, and limitations)
- `mobile_layout.png` (Responsive mobile viewport at 390&times;844)
- `backend_offline.png` (Backend offline alert banner state)

---

## API Configuration

The API configuration is located in a single file:
- `src/config.ts`

```typescript
export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';

export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/health`,
  screen: `${API_BASE_URL}/screen`,
} as const;

export const FROZEN_THRESHOLDS = {
  tau: 0.8538,
  alpha_cf: 0.01,
  alpha_gen: 0.50,
} as const;
```

---

## Evaluation Benchmark (v1 Synthetic Stress Test)

| Metric | Result | Context |
| :--- | :--- | :--- |
| **AUROC** | `0.734` | Area under ROC curve |
| **TPR at 5% FPR** | `0.353 (35.3%)` | True positive rate at 5% false positive rate |
| **False Likely-Counterfeit on Genuine** | `0.32%` | Genuine samples incorrectly labeled counterfeit |
| **Genuine Not Called Likely Genuine** | `52.3%` | Conservative calibration (inconclusive / retake) |
| **Product ID Top-1 Accuracy** | `68.5%` | DINOv2 cosine retrieval top-1 correctness |
| **Product ID Top-5 Accuracy** | `80.8%` | Correct product within top-5 gallery candidates |
| **Unknown-Product Rejection Rate** | `50.0%` | Rejection of uncataloged products at &tau; = 0.8538 |

---

## Limitations

1. **Synthetic tampers only:** Evaluated exclusively on synthetic tamperings. Not validated against real-world illicit manufacturing counterfeits.
2. **Known products only:** Operates exclusively across the 480 products in the frozen reference catalog.
3. **Weak product ID:** Top-1 product ID retrieval accuracy is 68.5%. Misidentification can route a pill to the wrong product memory bank.
4. **Screening aid only:** Strictly a screening aid; verify manually. Never claim a pill is authentic or safe.
