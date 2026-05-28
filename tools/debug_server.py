import sys
sys.path.insert(0, r"c:\Users\Shadow\voice to text engine")
import uvicorn
from swarm_backend.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=58084, log_level="debug")
