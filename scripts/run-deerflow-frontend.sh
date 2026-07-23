#!/usr/bin/env bash
set -euo pipefail

USER_HOME="/home/swegon"
NODE_V24_BIN="$USER_HOME/.local/share/fnm/node-versions/v24.16.0/installation/bin"

export PATH="$NODE_V24_BIN:$USER_HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export NEXT_TELEMETRY_DISABLED=1
export SKIP_ENV_VALIDATION=1

cd /home/swegon/AI_Agent/Aio_df/frontend
exec pnpm dev --hostname 0.0.0.0 --port 3002
