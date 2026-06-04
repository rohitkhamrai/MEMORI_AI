"""FastAPI application — MemoriaAI API server."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from memoria.api.store import init_db
from memoria.api.routes import health, metrics, research, graph, reports, memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    await init_db()
    yield


app = FastAPI(
    title="MemoriaAI API",
    description="Adaptive AI Research Memory System — REST API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3030", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(graph.router, prefix="/api", tags=["graph"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(memory.router, prefix="/api", tags=["memory"])


@app.get("/")
async def root():
    return {"message": "MemoriaAI API is running", "docs": "/docs"}
