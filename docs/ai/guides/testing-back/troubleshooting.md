# 🔧 TROUBLESHOOTING E RESOLUÇÃO DE PROBLEMAS EM TESTES

## 🚨 PROBLEMAS COMUNS E SOLUÇÕES

---

### **1. Erro `MissingGreenlet` no SQLAlchemy Async**

#### **Sintoma**:
Ao acessar relacionamentos de modelos SQLAlchemy durante assertions ou serializações Pydantic, ocorre `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`.

#### **Causa**:
Tentativa de carregar dados de um relacionamento `lazy="select"` (carregamento síncrono padrão) em um contexto de execução assíncrona.

#### **Solução**:
Aplique eager loading com `selectinload` ou `joinedload` nas queries do repositório ou no Use Case antes de serializar o DTO:

```python
# No repositório:
from sqlalchemy.orm import selectinload

stmt = select(ExemploModel).options(selectinload(ExemploModel.relacionamento))
result = await db.execute(stmt)
return result.scalars().all()
```

---

### **2. Vazamento de Dependências (`dependency_overrides`)**

#### **Sintoma**:
Um teste passa isoladamente, mas falha quando executado junto com a suíte completa, utilizando mocks ou UOW de um teste anterior.

#### **Causa**:
O dicionário `app.dependency_overrides` do FastAPI não foi limpo após o teste ser concluído.

#### **Solução**:
Sempre envolva a alteração de dependências em um bloco `try/finally` ou utilize uma fixture context manager com teardown:

```python
# ✅ Solução com try/finally
app.dependency_overrides[get_uow] = override_get_uow
try:
    response = await client.post("/v1/exemplos/", json=payload)
finally:
    app.dependency_overrides.clear()
```

---

### **3. Erros de Sessão Fechada ou Conflito no SQLite In-Memory**

#### **Sintoma**:
Mensagens do tipo `sqlalchemy.exc.ResourceClosedError` ou dados inseridos em um teste aparecendo em outro teste.

#### **Causa**:
Sessões reutilizadas entre testes sem o devido rollback/re-início de schema, ou reaproveitamento de instâncias da engine.

#### **Solução**:
Garanta que cada teste utilize a fixture `db_session` com escopo de função (`scope="function"`), permitindo isolamento transacional por teste:

```python
# tests/conftest.py
@pytest.fixture(scope="function")
async def db_session(init_db):
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
```

---

### **4. Warning de Loop de Eventos Asyncio (`Event loop is closed`)**

#### **Sintoma**:
Pytest exibe avisos `RuntimeError: Event loop is closed` ao final da execução dos testes.

#### **Causa**:
Incompatibilidade no escopo do `event_loop` entre fixtures de sessão e fixtures de função.

#### **Solução**:
Mantenha o escopo do event loop alinhado com o escopo das fixtures assíncronas do Pytest (pytest-asyncio):

```python
# pytest.ini
[pytest]
asyncio_mode = auto
```

---

### **5. Importação e Resolução de Módulos (`ModuleNotFoundError`)**

#### **Sintoma**:
Pytest não encontra os pacotes da aplicação (`ModuleNotFoundError: No module named 'app'`).

#### **Causa**:
O diretório `src/` não foi incluído no `PYTHONPATH` durante a chamada do `pytest`.

#### **Solução**:
Defina a variável `PYTHONPATH=src` antes da execução ou utilize o Make / uv:

```bash
# ✅ Execução via Makefile
make test

# ✅ Execução via uv
PYTHONPATH=src uv run pytest
```

---

## ⚡ OTIMIZAÇÃO DE PERFORMANCE E DIAGNÓSTICO DE LENTIDÃO

### **Identificar Testes Lentos**
```bash
# Listar os 10 testes mais demorados
PYTHONPATH=src uv run pytest --durations=10
```

### **Paralelização de Execução**
Para agilizar a execução de suítes grandes no CI ou ambiente local:
```bash
# Requer pytest-xdist instalado
PYTHONPATH=src uv run pytest -n auto --dist worksteal
```
