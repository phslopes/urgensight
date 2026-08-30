#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Verificando integridade de versao..."
if git diff --cached --name-only | grep -E "src/app.py|src/schemas.py" >/dev/null 2>&1; then
  if ! git diff --cached --name-only | grep -E "pyproject.toml|docs/api_contract.md" >/dev/null 2>&1; then
    echo "⚠️ AVISO: Endpoints ou Schemas alterados sem atualizacao correspondente de versao/contrato."
  fi
fi

exit 0
