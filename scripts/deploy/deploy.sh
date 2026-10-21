#!/usr/bin/env bash
# Deploy the imrul-deploy branch with the site staying up.
#
# The old sequence (`docker compose down; git pull; docker compose up --build`)
# took the site offline for the whole image build, several minutes of Cloudflare
# 502 for every visitor. This builds the new image while the old container keeps
# serving, swaps containers (a few seconds), waits for /api/health, and puts the
# previous image back if the new one never becomes healthy.
#
# Usage (on the server, from the repo checkout):  bash scripts/deploy/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/../.."

ENV_FILE="docker.env"
BRANCH="imrul-deploy"
SERVICE="grademax"
IMAGE="grademax:latest"
ROLLBACK_IMAGE="grademax:previous"
HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-180}"

[ -f "$ENV_FILE" ] || { echo "Missing $ENV_FILE (copy docker.env.example and fill it)" >&2; exit 1; }

PORT="$(grep -E '^GRADEMAX_PORT=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
PORT="${PORT:-3004}"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"

# --env-file is what feeds the NEXT_PUBLIC_* build args. Without it they fall
# back to placeholders and sign-in breaks (the Dockerfile now refuses to build).
compose() { docker compose --env-file "$ENV_FILE" "$@"; }

wait_healthy() {
  local deadline=$((SECONDS + HEALTH_WAIT_SECONDS))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}

echo "==> Updating code"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH"

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker tag "$IMAGE" "$ROLLBACK_IMAGE"
fi

echo "==> Building new image (the current container keeps serving)"
compose build "$SERVICE"

echo "==> Swapping container"
compose up -d --no-deps "$SERVICE"

echo "==> Waiting for $HEALTH_URL"
if wait_healthy; then
  echo "==> Deployed $(git rev-parse --short HEAD)"
  docker image prune -f >/dev/null
  exit 0
fi

echo "!! New container is not healthy. Last logs:" >&2
compose logs --tail 80 "$SERVICE" >&2 || true

if docker image inspect "$ROLLBACK_IMAGE" >/dev/null 2>&1; then
  echo "!! Rolling back to the previous image" >&2
  docker tag "$ROLLBACK_IMAGE" "$IMAGE"
  compose up -d --no-deps --force-recreate "$SERVICE"
  if wait_healthy; then
    echo "!! Rolled back; the site is on the previous build. Fix and redeploy." >&2
  else
    echo "!! Rollback is not healthy either. Check: docker compose logs $SERVICE" >&2
  fi
fi
exit 1
