#!/usr/bin/env bash
# One-time pairing: the Pi makes a random device token (kept in its private cloud.env, next to
# the Worker's address) and the same token goes straight into the rockridge-lights Worker as a
# secret. The token is never printed. Then the panel restarts, so it connects. Run again to
# rotate the token.
#   ./scripts/pair-device.sh
set -euo pipefail

HOST="${LIGHTS_HOST:-pi@192.168.0.7}"
URL="${LIGHTS_CLOUD_URL:-wss://rockridge-lights.monophonic.workers.dev/device}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ssh "$HOST" "URL='$URL' bash -s" <<'REMOTE' | (cd "$ROOT/cloud" && npx wrangler secret put LIGHTS_DEVICE_TOKEN)
set -e
f=~/.config/rockridge-lights/cloud.env
mkdir -p "$(dirname "$f")"
touch "$f" && chmod 600 "$f"
sed -i "/^LIGHTS_DEVICE_TOKEN=/d; /^LIGHTS_CLOUD_URL=/d" "$f"
echo "LIGHTS_CLOUD_URL=$URL" >> "$f"
echo "LIGHTS_DEVICE_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")" >> "$f"
grep "^LIGHTS_DEVICE_TOKEN=" "$f" | cut -d= -f2-
REMOTE

echo "paired: the Pi and the rockridge-lights Worker now share a new device token."
"$ROOT/scripts/restart-panel.sh"
