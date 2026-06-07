#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# CortexFlow Demo 錄製腳本
# 使用方式：
#   bash docs/demo-recording.sh              # 純文字錄製
#   asciinema rec -c "bash docs/demo-recording.sh"  # 影片錄製
# ─────────────────────────────────────────────────────────────

set -euo pipefail

TOPIC="${1:-AI Coding Agents}"
OUTPUT="${2:-/tmp/cortexflow-demo.md}"

echo "================================================"
echo "  CortexFlow Demo — 主題: ${TOPIC}"
echo "================================================"
echo ""

# Step 1: Show help
echo "$ uv run cortexflow --help"
uv run cortexflow --help 2>&1
echo ""
echo "--- 按 Enter 繼續 ---"
read -r

# Step 2: Run demo pipeline
echo "$ uv run cortexflow --topic \"${TOPIC}\" --sources github --demo --output ${OUTPUT}"
echo ""
timeout 15 uv run cortexflow \
  --topic "${TOPIC}" \
  --sources github \
  --demo \
  --output "${OUTPUT}" 2>&1 || true

echo ""
echo "================================================"
echo "  輸出報告預覽 (${OUTPUT})"
echo "================================================"
head -30 "${OUTPUT}" 2>/dev/null || echo "(報告已產生)"
echo ""
echo "✅ Demo 完成！"
