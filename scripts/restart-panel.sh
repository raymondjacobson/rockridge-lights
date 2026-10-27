#!/usr/bin/env bash
# Restart the control panel on the Pi so it runs the latest code. The lights blink off for a
# moment: the shows stop with the old panel, and the new one picks up what was on the lights.
#   ./scripts/restart-panel.sh
set -euo pipefail

HOST="${LIGHTS_HOST:-pi@192.168.0.7}"

ssh -n "$HOST" 'set -e
  cd ~/rockridge-lights
  pkill -f "^python panel[.]py" || true
  for _ in $(seq 50); do pgrep -f "^python panel[.]py" > /dev/null || break; sleep 0.2; done
  setsid nohup python panel.py >> panel.log 2>&1 < /dev/null &
  sleep 3
  pgrep -f "^python panel[.]py" > /dev/null && echo "panel restarted" || { tail -20 panel.log; exit 1; }'
