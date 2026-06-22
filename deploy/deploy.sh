#!/bin/bash
set -e

cd /opt/jobscout

git pull origin main

docker compose up -d --build

docker compose exec backend alembic upgrade head

echo "Deploy complete."
