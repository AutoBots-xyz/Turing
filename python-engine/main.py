from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import layer2

app = FastAPI(
    title="Turing - Causal Nexus API",
    description="Python backend for the Causal Nexus architecture.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all Layer 2 routes
app.include_router(layer2.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "turing-python-engine"}
