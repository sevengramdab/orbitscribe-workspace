"""SimplePod configuration."""
import os
import socket

# Discovery
DISCOVERY_PORT = int(os.environ.get("SIMPLEPOD_DISCOVERY_PORT", "58090"))
DISCOVERY_INTERVAL = 3.0  # seconds between broadcast beacons
DISCOVERY_TIMEOUT = 10.0  # peer TTL before removal

# Remote API
API_PORT = int(os.environ.get("SIMPLEPOD_API_PORT", "58091"))
API_TOKEN = os.environ.get("SIMPLEPOD_TOKEN", "simplepod-default-token")

# Identity
NODE_ID = os.environ.get("SIMPLEPOD_NODE_ID", socket.gethostname())
NODE_NAME = os.environ.get("SIMPLEPOD_NODE_NAME", NODE_ID)
NODE_ROLE = os.environ.get("SIMPLEPOD_ROLE", "shadow")  # 'shadow' or 'local'
