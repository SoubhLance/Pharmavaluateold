"""
FastAPI Backend for PharmaValuate (pill stream).

Endpoints:
  - GET  /health -> Service status, device, stream info
  - POST /screen -> Screening aid endpoint for pill images

Wording: "screening aid, verify manually". Never claim a pill is authentic.
"""

import sys, os, io
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
from PIL import Image
from starlette.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.service import PharmaValuateScreener, DISCLAIMER

screener: Optional[PharmaValuateScreener] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global screener
    print("[*] Initializing PharmaValuate inference engine at startup...")
    screener = PharmaValuateScreener()
    print(f"[*] Engine ready on device: {screener.device} with {len(screener.unique_products)} known products.")
    yield
    print("[*] Shutting down PharmaValuate inference engine.")
    screener = None

app = FastAPI(
    title="PharmaValuate Screening API",
    description="Genuine-only anomaly detection screening aid for medicine photos (pill stream).",
    version="1.0.0",
    lifespan=lifespan
)

# The demo is intended for local use. Keep the allowlist narrow and explicit.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEMO_FILE = Path(__file__).resolve().parent / "demo.html"
FRONTEND_DIST = ROOT / "frontend" / "dist"

class HealthResponse(BaseModel):
    status: str
    device: str
    stream: str
    gallery_products: int
    disclaimer: str

class QualityDetails(BaseModel):
    passed: bool
    blur: float
    glare: float
    mean_lum: float
    dark: float
    thresholds: Dict[str, float]

class ScreenResponse(BaseModel):
    label: str
    p_value: Optional[float] = None
    anomaly_score: Optional[float] = None
    product_id: Optional[str] = None
    best_similarity: Optional[float] = None
    top5: Optional[List[str]] = None
    top5_details: Optional[List[Dict[str, Any]]] = None
    quality: QualityDetails
    disclaimer: str

@app.get("/demo", include_in_schema=False)
def demo_legacy():
    """Serve the legacy self-contained browser demo."""
    return FileResponse(DEMO_FILE, media_type="text/html")

@app.get("/", include_in_schema=False)
def root():
    """Serve the built production frontend if available, else fallback to legacy demo."""
    dist_index = FRONTEND_DIST / "index.html"
    if dist_index.is_file():
        return FileResponse(dist_index, media_type="text/html")
    return FileResponse(DEMO_FILE, media_type="text/html")

@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    fav = FRONTEND_DIST / "favicon.svg"
    if fav.is_file():
        return FileResponse(fav, media_type="image/svg+xml")
    raise HTTPException(status_code=404)

@app.get("/icons.svg", include_in_schema=False)
def icons_svg():
    icons = FRONTEND_DIST / "icons.svg"
    if icons.is_file():
        return FileResponse(icons, media_type="image/svg+xml")
    raise HTTPException(status_code=404)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint confirming model status and hardware backend."""
    if screener is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference engine is not yet initialized."
        )
    return HealthResponse(
        status="healthy",
        device=str(screener.device),
        stream="pill",
        gallery_products=len(screener.unique_products),
        disclaimer=DISCLAIMER
    )

@app.post("/screen", response_model=ScreenResponse)
async def screen(file: UploadFile = File(...)):
    """
    Screen an uploaded pill image:
    1. Capture quality gate check
    2. Product identification against frozen gallery
    3. AnomalyDINO patch matching against product reference bank
    4. Conformal p-value prediction and screening classification

    Screening aid only; verify manually.
    """
    try:
        # Read in bounded chunks so a large multipart upload is rejected without
        # buffering its full contents in memory.
        chunks = []
        size = 0
        while True:
            chunk = await file.read(min(1024 * 1024, MAX_UPLOAD_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image is too large. Maximum upload size is 10 MB.",
                )
        contents = b"".join(chunks)
        if not contents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        
        # Load image via PIL to validate image integrity
        try:
            with Image.open(io.BytesIO(contents)) as source:
                source.verify()
            with Image.open(io.BytesIO(contents)) as source:
                pil_img = source.convert("RGB")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file. Upload a valid JPEG, PNG, or WebP image."
            )

        if screener is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Inference engine is not ready."
            )
        
        img_rgb = np.array(pil_img)
        
        # Execute screening pipeline
        result = screener.screen(img_rgb)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}"
        )
    finally:
        await file.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)

