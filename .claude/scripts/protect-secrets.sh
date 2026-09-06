#!/usr/bin/env bash
set -euo pipefail

PATTERNS=("AIza[0-9A-Za-z-_]{35}" "sk-[a-zA-Z0-9]{20,}" "ghp_[a-zA-Z0-9]{36}" "PRIVATE KEY")

echo "🔍 Verificando segredos em arquivos alterados..."

CACHED_FILES=$(git diff --cached --name-only || true)

if [ -n "$CACHED_FILES" ]; then
  for pattern in "${PATTERNS[@]}"; do
    if git diff --cached -z --name-only | xargs -0 grep -E "$pattern" 2>/dev/null; then
      echo "❌ BLOQUEIO: Possivel segredo detectado com padrao: $pattern"
      exit 1
    fi
  done
fi

echo "✅ Nenhum segredo detectado."
exit 0
