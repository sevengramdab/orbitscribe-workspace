#!/bin/bash
set -e
docker-compose down || true
docker-compose up --build -d
echo "Deployed json_formatter_5825a715"
