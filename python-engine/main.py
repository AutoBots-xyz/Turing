from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import layer1

app = FastAPI(
    title="Turing Nexus API",
    description="Causal Graph Discovery Engine Backend",
    version="1.0.0"
)

# Configure CORS for Next.js frontend (defaulting to localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(layer1.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
