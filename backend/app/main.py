from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import router_synthesis, router_glfi, router_files

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="GateScan - Fault Injection Scanner for FPGA and ASIC Designs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_synthesis.router, prefix="/api/synthesis", tags=["1. Logic Synthesis"])
app.include_router(router_glfi.router, prefix="/api/glfi", tags=["2. Fault Injection Campaign"])
app.include_router(router_files.router, prefix="/api/sessions", tags=["3. Session Files"])

@app.get("/api/health", tags=["Health Check"])
async def health():
    return {
        "status": "Online",
        "platform": settings.PROJECT_NAME,
        "message": "GateScan Backend Core is running."
    }

frontend_dir = settings.BASE_DIR / "frontend"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
