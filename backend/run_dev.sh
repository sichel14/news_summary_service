#!/usr/bin/env bash
# 不依赖 `source .venv/bin/activate`，避免 pyenv/conda 抢走 `python` 命令。
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python main.py "$@"
