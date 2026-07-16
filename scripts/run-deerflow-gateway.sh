#!/usr/bin/env bash
set -euo pipefail

USER_HOME="/home/swegon"
export PATH="$USER_HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export DEER_FLOW_AUTH_DISABLED=1

cd /home/swegon/AI_Agent/deer-flow/backend
exec env PYTHONPATH=. uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001
