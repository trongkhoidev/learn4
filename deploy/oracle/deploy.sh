#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STATE=${STATE:-"$ROOT/deploy/oracle/state.json"}
SSH_KEY=${SSH_KEY:-"$ROOT/.oci-private/learn4-oracle"}

[[ -f "$STATE" ]] || { echo "Missing $STATE; run provision.py first" >&2; exit 2; }
[[ -f "$SSH_KEY" ]] || { echo "Missing $SSH_KEY" >&2; exit 2; }
[[ -f "$ROOT/.env" ]] || { echo "Missing $ROOT/.env" >&2; exit 2; }

read -r PUBLIC_IP BACKEND_HOST SSH_USER < <(python3 - "$STATE" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))
print(s["public_ip"], s["backend_host"], s["ssh_user"])
PY
)
REMOTE="${SSH_USER}@${PUBLIC_IP}"
SSH=(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=15 "$REMOTE")
RSYNC_SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=15"

echo "Waiting for cloud-init on $REMOTE..."
"${SSH[@]}" 'sudo cloud-init status --wait && sudo mkdir -p /opt/learn4 /opt/learn4-data/storage && sudo chown -R ubuntu:ubuntu /opt/learn4 /opt/learn4-data'

rsync -az --delete \
  --exclude '.git/' --exclude '.env' --exclude '.oci-private/' \
  --exclude 'node_modules/' --exclude '.venv/' --exclude 'venv/' \
  --exclude 'frontend/dist/' --exclude 'test-results/' \
  --exclude 'storage/' --exclude '*.db' --exclude '*.sqlite*' \
  -e "$RSYNC_SSH" "$ROOT/" "$REMOTE:/opt/learn4/"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$ROOT/.env" "$REMOTE:/opt/learn4/.env"
"${SSH[@]}" 'chmod 600 /opt/learn4/.env'

if [[ -f "$ROOT/lexilearn.db" ]]; then
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$ROOT/lexilearn.db" "$REMOTE:/tmp/learn4-seed.db"
  "${SSH[@]}" 'if [[ ! -f /opt/learn4-data/lexilearn.db ]]; then mv /tmp/learn4-seed.db /opt/learn4-data/lexilearn.db; else rm -f /tmp/learn4-seed.db; fi'
fi
if [[ -d "$ROOT/storage" ]]; then
  rsync -az -e "$RSYNC_SSH" "$ROOT/storage/" "$REMOTE:/opt/learn4-data/storage/"
fi

"${SSH[@]}" "cat > /opt/learn4/deploy/oracle/.env.runtime <<EOF
BACKEND_HOST=$BACKEND_HOST
LEARN4_DATA_DIR=/opt/learn4-data
EOF
cd /opt/learn4
docker compose --env-file deploy/oracle/.env.runtime -f deploy/oracle/compose.yml up -d --build
docker compose --env-file deploy/oracle/.env.runtime -f deploy/oracle/compose.yml ps"

echo "Waiting for https://$BACKEND_HOST/ready ..."
for _ in $(seq 1 90); do
  if curl -fsS --max-time 10 "https://$BACKEND_HOST/ready" >/tmp/learn4-oracle-ready.json 2>/dev/null; then
    cat /tmp/learn4-oracle-ready.json
    echo
    echo "Oracle backend ready: https://$BACKEND_HOST"
    exit 0
  fi
  sleep 10
done

"${SSH[@]}" 'cd /opt/learn4 && docker compose --env-file deploy/oracle/.env.runtime -f deploy/oracle/compose.yml logs --tail=200'
echo "Backend did not become ready within 15 minutes" >&2
exit 1
