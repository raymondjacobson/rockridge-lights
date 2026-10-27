#!/usr/bin/env bash
# Put this checkout's commits on the Pi (fast-forward only, so it never undoes work made on the
# Pi) and install what the panel needs. Doesn't restart the panel: run restart-panel.sh for that.
#   ./scripts/deploy-pi.sh
set -euo pipefail

HOST="${LIGHTS_HOST:-pi@192.168.0.7}"
cd "$(dirname "$0")/.."

git push --quiet "$HOST:rockridge-lights" HEAD:refs/heads/incoming
ssh -n "$HOST" 'set -e
  cd ~/rockridge-lights
  git merge --ff-only --quiet incoming
  git log --oneline -1
  python3 -c "import websocket" 2> /dev/null || pip3 install --user --quiet -r requirements.txt'
