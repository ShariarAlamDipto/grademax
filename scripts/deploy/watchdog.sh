#!/usr/bin/env bash
# Restarts the app container when it stops answering.
#
# `restart: unless-stopped` only covers a process that exits. Docker never
# restarts a container that is running but hung or marked "unhealthy", so a
# stuck Node process meant 502s until someone logged in. Run this from cron
# every minute; it restarts after 3 consecutive failed checks (~3 minutes).
#
#   * * * * * /home/ubuntu/dipto/grademax/scripts/deploy/watchdog.sh >> /home/ubuntu/dipto/grademax-watchdog.log 2>&1
set -uo pipefail

cd "$(dirname "$0")/../.."

ENV_FILE="docker.env"
CONTAINER="grademax-app"
MAX_FAILURES=3
STATE_FILE="${TMPDIR:-/tmp}/grademax-watchdog.failures"

# Never fight a deploy that is in progress.
if pgrep -f "scripts/deploy/deploy.sh" >/dev/null 2>&1; then
  exit 0
fi

PORT="$(grep -E '^GRADEMAX_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
PORT="${PORT:-3004}"

if curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  rm -f "$STATE_FILE"
  exit 0
fi

failures=$(( $(cat "$STATE_FILE" 2>/dev/null || echo 0) + 1 ))
echo "$failures" > "$STATE_FILE"
echo "$(date -u +%FT%TZ) health check failed ($failures/$MAX_FAILURES)"

if [ "$failures" -ge "$MAX_FAILURES" ]; then
  echo "$(date -u +%FT%TZ) restarting $CONTAINER; last logs:"
  docker logs --tail 40 "$CONTAINER" 2>&1 | sed 's/^/    /'
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    docker restart "$CONTAINER"
  else
    docker compose --env-file "$ENV_FILE" up -d --no-deps grademax
  fi
  rm -f "$STATE_FILE"
fi
