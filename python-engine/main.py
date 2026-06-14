"""
main.py — Turing API Entry Point

Initialises the FastAPI application, registers all routers,
configures CORS middleware, database, and starts the Uvicorn server.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env before any other imports that might check env vars
load_dotenv()

# ---------------------------------------------------------------------------
# Single source of truth for the API version.
# Set APP_VERSION in .env or the deployment environment on each release.
# ---------------------------------------------------------------------------
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

from database.database import init_db
from routers import layer1, layer2, layer3, layer4, runs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise resources on startup, tear down on shutdown."""
    await init_db()
    yield


app = FastAPI(
    title="Turing - Causal Nexus API",
    description="Causal Graph Discovery Engine Backend",
    version=APP_VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js frontend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(layer1.router, prefix="/api/layer1", tags=["Layer 1 — Data Ingestion"])
app.include_router(layer2.router, prefix="/api/layer2", tags=["Layer 2 — Agent Simulation"])
app.include_router(layer3.router, prefix="/api/layer3", tags=["Layer 3 — Cross-Domain Search"])
app.include_router(layer4.router, prefix="/api/layer4", tags=["Layer 4 — Report Generation"])
app.include_router(runs.router,   prefix="/api/runs",   tags=["Runs — Session Management"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "turing-python-engine", "version": APP_VERSION}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Local development entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )