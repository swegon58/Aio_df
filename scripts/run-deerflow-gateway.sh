#!/usr/bin/env bash
set -euo pipefail

USER_HOME="/home/swegon"
export PATH="$USER_HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

cd /home/swegon/AI_Agent/Aio_df/backend
exec env PYTHONPATH=. uv run uvicorn app.gateway.app:app --host 0.0.0.0 --port 8001
