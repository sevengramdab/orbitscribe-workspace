FROM python:3.13-slim

# Install system deps for cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --no-cache-dir cryptography

WORKDIR /opt/mesh

# Copy the swarm backend and node bootstrap reference
COPY swarm-backend/ /opt/mesh/swarm-backend/
COPY node_bootstrap.py /opt/mesh/

ENV PYTHONPATH=/opt/mesh/swarm-backend:/opt/mesh
ENV PYTHONUNBUFFERED=1
ENV RUST_LOG=info

# Entrypoint runs the aquaculture mesh directly (no FastAPI server needed inside container)
CMD ["python", "-m", "modes.aquaculture_mesh_mode"]
