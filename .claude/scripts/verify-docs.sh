#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Verificando documentacao..."
if git diff --cached --name-only | grep -E "^src/" >/dev/null 2>&1; then
  echo "ℹ️ Codigo-fonte alterado. Certifique-se de que a documentacao em docs/ reflete as mudancas."
fi

exit 0
