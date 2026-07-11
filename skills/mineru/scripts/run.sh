#!/usr/bin/env bash
# MinerU 本機 PDF→Markdown（CPU pipeline backend）
# 用法: bash run.sh <輸入.pdf 或資料夾> [輸出目錄] [額外 mineru 旗標...]
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINERU="$SKILL_DIR/.venv/Scripts/mineru.exe"
export MINERU_MODEL_SOURCE="${MINERU_MODEL_SOURCE:-huggingface}"

in="${1:?用法: run.sh <輸入.pdf|資料夾> [輸出目錄] [額外旗標]}"
out="${2:-./mineru-out}"
shift || true; shift || true || true

"$MINERU" -p "$in" -o "$out" -b pipeline "$@"
echo "---"
echo "完成。Markdown 在: $out/<檔名>/auto/<檔名>.md"
