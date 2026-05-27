#!/bin/bash
set -e
docker-compose down || true
docker-compose up --build -d
echo "Deployed custom_5d2afaba"
