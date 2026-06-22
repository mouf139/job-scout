#!/bin/bash
# Nightly PostgreSQL backup with 7-day rotation

BACKUP_DIR="/opt/jobscout/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER="jobagent-postgres-1"

mkdir -p "$BACKUP_DIR"

docker exec "$CONTAINER" pg_dump -U jobscout jobscout | gzip > "$BACKUP_DIR/jobscout_$TIMESTAMP.sql.gz"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: jobscout_$TIMESTAMP.sql.gz"
