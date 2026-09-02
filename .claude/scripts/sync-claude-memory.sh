#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-pull}"
PROJECT_MEMORY_DIR="$HOME/.claude/projects/-Users-eduardobatista-Code-urgensight/memory/team"
LOCAL_MEMORY_DIR=".claude/memory/team"

mkdir -p "$LOCAL_MEMORY_DIR"
if [ -d "$PROJECT_MEMORY_DIR" ]; then
  if [ "$ACTION" == "pull" ]; then
    rsync -av --update "$PROJECT_MEMORY_DIR/" "$LOCAL_MEMORY_DIR/" 2>/dev/null || cp -R "$PROJECT_MEMORY_DIR/"* "$LOCAL_MEMORY_DIR/" 2>/dev/null || true
    echo "✅ Memorias de equipe sincronizadas (pull)."
  elif [ "$ACTION" == "push" ]; then
    rsync -av --update "$LOCAL_MEMORY_DIR/" "$PROJECT_MEMORY_DIR/" 2>/dev/null || cp -R "$LOCAL_MEMORY_DIR/"* "$PROJECT_MEMORY_DIR/" 2>/dev/null || true
    echo "✅ Memorias de equipe sincronizadas (push)."
  fi
fi
