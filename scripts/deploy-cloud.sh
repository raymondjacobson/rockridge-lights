#!/usr/bin/env bash
# Typecheck, test and deploy the panel's Worker (cloud/) to Cloudflare with the logged-in wrangler.
# Secrets are set separately (pair-device.sh, `npx wrangler secret put LIGHTS_PASSWORD`) and
# survive deploys.
#   ./scripts/deploy-cloud.sh
set -euo pipefail

cd "$(dirname "$0")/../cloud"
npm ci --no-fund --no-audit --silent
npm run typecheck --silent
npx vitest run --silent
npx wrangler deploy
