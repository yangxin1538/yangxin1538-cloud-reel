#!/bin/sh
# CloudReel - docker run install, any NAS or cloud server.
# Usage:
#   DATA_DIR=/data/cloud-reel/data STRM_DIR=/data/strm \
#   CLOUDNAS_DIR=/mnt/CloudNAS ./deploy/docker-run.sh
# Or edit the defaults below. No Synology-only paths.
set -eu

IMAGE="${IMAGE:-cloud-reel:latest}"
PORT="${PORT:-8088}"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
DATA_DIR="${DATA_DIR:-./data}"
CONFIG_DIR="${CONFIG_DIR:-./config}"
STRM_DIR="${STRM_DIR:-./strm}"
CLOUDNAS_DIR="${CLOUDNAS_DIR:-./CloudNAS}"
SOURCE_ROOT="${SOURCE_ROOT:-/CloudNAS}"

# Build the image first (from the repo root), or set IMAGE to a
# published image and skip the build.
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  docker build -t "$IMAGE" .
fi

# Cloud server with no local mount: set CLOUDNAS_DIR="" to skip it.
if [ -n "$CLOUDNAS_DIR" ]; then
  MOUNT_CLOUDNAS="-v $CLOUDNAS_DIR:/CloudNAS:ro"
else
  MOUNT_CLOUDNAS=""
fi

# shellcheck disable=SC2086
docker run -d \
  --name cloud-reel \
  --restart unless-stopped \
  -p "$PORT:8088" \
  -e PORT=8088 \
  -e PUID="$PUID" -e PGID="$PGID" \
  -e SOURCE_ROOT="$SOURCE_ROOT" \
  -e STRM_ROOT=/strm/CloudReel \
  -e STRM_MODE="${STRM_MODE:-file}" \
  -e SCAN_INTERVAL_MINUTES="${SCAN_INTERVAL_MINUTES:-60}" \
  -e EMBY_UPSTREAM="${EMBY_UPSTREAM:-}" \
  -e PAN123_CLIENT_ID="${PAN123_CLIENT_ID:-}" \
  -e PAN123_CLIENT_SECRET="${PAN123_CLIENT_SECRET:-}" \
  -v "$DATA_DIR:/app/data" \
  -v "$CONFIG_DIR:/app/config" \
  -v "$STRM_DIR:/strm" \
  $MOUNT_CLOUDNAS \
  "$IMAGE"

echo "CloudReel running at http://localhost:$PORT"
