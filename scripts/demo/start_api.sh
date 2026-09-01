#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
mkdir -p logs
PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" \
  python -m data2mcp_v2.server.api --port "${PORT:-2733}"
