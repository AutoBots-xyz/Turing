from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import layer1
from routers import runs

app = FastAPI(
    title="Turing API",
    description="Causal Graph Discovery Engine Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(layer1.router)
app.include_router(runs.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "turing-python-engine"}
