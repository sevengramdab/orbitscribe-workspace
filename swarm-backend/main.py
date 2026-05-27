"""
OrbitScribe Swarm Backend
FastAPI service for multi-agent LLM orchestration.
"""
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.monetization_routes import router as monetization_router
from core import config
from core.discovery import get_discovery_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle events."""
    # Startup
    discovery = get_discovery_service({
        "node_id": f"orbitscribe-local-{config.PORT}",
        "name": "Local OrbitScribe",
        "endpoint": f"http://{config.HOST}:{config.PORT}",
        "tier": "shadow",
        "version": "3.0.0",
    })
    discovery.start()
    print(f"[Discovery] UDP broadcast listener started on port {discovery.port}")
    yield
    # Shutdown
    discovery = get_discovery_service()
    if discovery:
        discovery.stop()
        print("[Discovery] UDP broadcast listener stopped")


app = FastAPI(title="OrbitScribe Swarm", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(monetization_router, prefix="/api")

# Serve monetization dashboard
import os
from fastapi.responses import FileResponse
_DASHBOARD_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "monetization_dashboard.html")
@app.get("/monetization")
async def monetization_dashboard():
    return FileResponse(_DASHBOARD_PATH)

# Legacy direct endpoints for OrbitScribe HTML compatibility
@app.get("/api/health")
async def health():
    return {"status": "ok", "api_mode": config.API_MODE, "version": "3.0.0"}

@app.get("/api/mode")
async def get_mode():
    return {"mode": config.API_MODE}

if __name__ == "__main__":
    import uvicorn

    # Create socket with SO_REUSEADDR so we can rebind immediately after restart
    # (prevents "address already in use" errors on Windows when old sockets are in TIME_WAIT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((config.HOST, config.PORT))
    except OSError as e:
        print(f"[FATAL] Could not bind to {config.HOST}:{config.PORT} — {e}")
        raise

    uvicorn_config = uvicorn.Config(app, log_level="info")
    server = uvicorn.Server(uvicorn_config)
    server.run(sockets=[sock])
