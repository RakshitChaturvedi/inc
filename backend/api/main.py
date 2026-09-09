# backend/api/main.py

from __future__ import annotations

from fastapi import FastAPI

from .router import router


app = FastAPI(
    title="OceanEmbed API",
    description="Backend API for OceanEmbed ocean reconstruction and analysis data.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "service": "OceanEmbed API",
        "version": "1.0.0",
        "status": "ok",
    }