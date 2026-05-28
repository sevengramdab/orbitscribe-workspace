"""
Lightweight dashboard server for OrbitScribe.
Serves templates/ and proxies API calls to the main backend on 58081.
"""
import os
import urllib.request
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).parent.parent
TEMPLATES = ROOT / "templates"
MAIN_BACKEND = "http://127.0.0.1:58081"

app = FastAPI(title="OrbitScribe Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index():
    path = TEMPLATES / "monetization_dashboard.html"
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/monetization")
async def monetization():
    path = TEMPLATES / "monetization_dashboard.html"
    if path.exists():
        return FileResponse(path)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_api(path: str):
    """Proxy API calls to the main backend."""
    url = f"{MAIN_BACKEND}/api/{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return HTMLResponse(resp.read().decode("utf-8"), status_code=resp.status)
    except Exception as e:
        return HTMLResponse(f"Proxy error: {e}", status_code=502)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
