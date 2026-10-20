#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/lexilearn-$(date +%F).sql"
docker compose exec -T postgres pg_dump -U lexi lexilearn > "$FILE"
echo "Backup written to $FILE"

ls -1t "$BACKUP_DIR"/lexilearn-*.sql | tail -n +8 | xargs -r rm -f
