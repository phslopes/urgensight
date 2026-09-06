---
name: gen-api-test
description: Gera casos de teste assíncronos modernos com httpx.AsyncClient para rotas FastAPI
---

# Skill: gen-api-test

Esta skill fornece o padrão oficial para criação de testes assíncronos de API no UrgenSight.

## Padrão Oficial
```python
import pytest
from httpx import ASGITransport, AsyncClient
from src.app import app

@pytest.mark.asyncio
async def test_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/predict", json={"texto_laudo": "Paciente com cefaleia intensa"})
    assert response.status_code == 200
```
