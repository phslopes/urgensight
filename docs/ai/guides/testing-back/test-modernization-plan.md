# 🎯 ARQUITETURA E PLANO DE PADRONIZAÇÃO DE TESTES

## 📊 VISÃO GERAL DA ARQUITETURA DE TESTES

O projeto adota a arquitetura **Domain-First (Vertical Slice Architecture)** com **FastAPI**, **SQLAlchemy 2.0 Async** e **Unit of Work (UOW)**. A suíte de testes deve refletir rigorosamente esse isolamento, promovendo alta confiabilidade, velocidade de execução e independência de estado.

---

## 🏗️ PIRÂMIDE E CAMADAS DE TESTE

```
        / \
       /   \     10% E2E Tests (httpx.AsyncClient + Fluxos Completos)
      / E2E \
     /-------\   20% Integration Tests (Repositories + SQLite In-Memory / Routers)
    / Integra \
   /-----------\ 70% Unit Tests (Use Cases, Services, Schemas, Policies)
  /  Unitários  \
 /---------------\
```

### **1. Testes Unitários (`tests/{modulo}/unit/`) — ~70%**
- **Escopo**: Use Cases, Services de domínio, Schemas Pydantic, Policies (RBAC/ABAC).
- **Isolamento**: Total. Não efetuam conexões com banco de dados real ou serviços externos.
- **Mocks**: Repositórios e serviços de infraestrutura externa (envio de e-mails, gateways) são mockados (`unittest.mock.AsyncMock` / `MagicMock`) ou operam sobre UOW com repositórios em memória.

### **2. Testes de Integração (`tests/{modulo}/integration/`) — ~20%**
- **Escopo**: Repositórios SQLAlchemy e Roteadores FastAPI.
- **Banco de Dados**: Utilizam banco SQLite assíncrono em memória (`sqlite+aiosqlite:///:memory:`).
- **Fixtures**: As fixtures `db_session` e `uow` inicializam as tabelas (`create_all`) e executam rollback ou rebuild no teardown.
- **HTTP Client**: Roteadores utilizam `httpx.AsyncClient(transport=ASGITransport(app=app))` com injeção de dependência sobrescrita (`app.dependency_overrides[get_uow]`).

### **3. Testes End-to-End (`tests/{modulo}/e2e/`) — ~10%**
- **Escopo**: Fluxos transacionais completos de ponta a ponta envolvendo múltiplos endpoints, autenticação JWT e transações no UOW.

---

## 🚀 BLUEPRINT DE IMPLEMENTAÇÃO EM 4 FASES

### **FASE 1: ALINHAMENTO DE ESTRUTURA E FIXTURES**
**Objetivo**: Consolidar o diretório de testes no formato Domain-First.

- [x] Estruturar os testes dentro do padrão `tests/{modulo}/{unit|integration|e2e}/`.
- [x] Configurar fixtures centrais em `tests/conftest.py` (`init_db`, `db_session`, `uow`, `client`).
- [x] Configurar limpeza automática de filas/mocks no teardown.

---

### **FASE 2: SUÍTE DE TESTES UNITÁRIOS DE DOMÍNIO**
**Objetivo**: Garantir cobertura de 90%+ na camada de regras de negócio (Use Cases e Schemas).

#### **2.1 Use Cases (Exemplo Agnóstico)**
```python
# tests/{modulo}/unit/use_cases/test_exemplo_use_case.py
import pytest
from unittest.mock import AsyncMock

class TestCriarExemploUseCase:
    @pytest.mark.asyncio
    async def test_executar_com_sucesso(self):
        # Arrange
        mock_uow = AsyncMock()
        mock_uow.exemplos.add = AsyncMock()
        mock_uow.commit = AsyncMock()
        
        use_case = CriarExemploUseCase(uow=mock_uow)
        payload = ExemploCreateSchema(nome="Item Teste", valor=100.0)

        # Act
        resultado = await use_case.execute(payload)

        # Assert
        assert resultado.nome == "Item Teste"
        mock_uow.commit.assert_called_once()
```

#### **2.2 Schemas e Validações Pydantic**
```python
# tests/{modulo}/unit/schemas/test_exemplo_schemas.py
import pytest
from pydantic import ValidationError

class TestExemploSchemas:
    def test_schema_validacao_sucesso(self):
        schema = ExemploCreateSchema(nome="Teste", valor=50.0)
        assert schema.nome == "Teste"

    @pytest.mark.parametrize("payload_invalido,erro_esperado", [
        ({"nome": "", "valor": 50.0}, "String should have at least 1 character"),
        ({"nome": "Teste", "valor": -10.0}, "Input should be greater than 0"),
    ])
    def test_schema_validacao_erros(self, payload_invalido, erro_esperado):
        with pytest.raises(ValidationError) as exc:
            ExemploCreateSchema(**payload_invalido)
        assert erro_esperado in str(exc.value)
```

---

### **FASE 3: TESTES DE INTEGRAÇÃO COM REPOSITÓRIOS E ROTAS**
**Objetivo**: Validar persistência SQLAlchemy em memória e contratos HTTP da API.

#### **3.1 Testes de Repositório (SQLAlchemy Async)**
```python
# tests/{modulo}/integration/repositories/test_exemplo_repository.py
import pytest

class TestExemploRepository:
    @pytest.mark.asyncio
    async def test_salvar_e_buscar_por_id(self, db_session):
        # Arrange
        repo = ExemploRepository(db_session)
        entidade = ExemploModel(nome="Item Persistido", ativo=True)

        # Act
        await repo.add(entidade)
        await db_session.commit()
        
        buscado = await repo.get_by_id(entidade.id)

        # Assert
        assert buscado is not None
        assert buscado.nome == "Item Persistido"
```

#### **3.2 Testes de Rotas FastAPI (com Dependency Override)**
```python
# tests/{modulo}/integration/routers/test_exemplo_router.py
import pytest
from app.core.dependencies import get_uow

class TestExemploRouter:
    @pytest.mark.asyncio
    async def test_criar_item_endpoint(self, client, uow):
        # Arrange
        app.dependency_overrides[get_uow] = lambda: uow
        payload = {"nome": "Novo Item", "valor": 100.0}

        try:
            # Act
            response = await client.post("/v1/exemplos/", json=payload)

            # Assert
            assert response.status_code == 201
            assert response.json()["nome"] == "Novo Item"
        finally:
            app.dependency_overrides.clear()
```

---

### **FASE 4: FLUXOS E2E E CONTINUOUS INTEGRATION**
**Objetivo**: Validar jornadas completas e integrar verificações ao pipeline CI.

- Integrar execução no GitHub Actions / Pipeline CI via `make test-cov`.
- Aplicar marcações `@pytest.mark.e2e` e `@pytest.mark.slow`.
- Garantir tempo total de suíte reduzido e execução em paralelo via `pytest-xdist`.

---

## 📋 DIRECTIVAS E BOAS PRÁTICAS

1. **Uso de Fixtures Globais**: Sempre utilizar fixtures expostas em `tests/conftest.py` (`db_session`, `uow`, `client`).
2. **Sem Chamadas Externas**: Nenhuma requisição HTTP real para a internet ou para portas locais deve ocorrer nos testes.
3. **Limpeza Transacional**: Todo teste de integração ou E2E deve restaurar o estado do banco.
4. **Respeito ao RFC 7807**: Assertions de exceção em rotas devem validar o formato padrão de erros da API.
