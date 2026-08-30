# 📋 GUIA DE EXECUÇÃO DE TESTES

## 🚀 COMANDOS ESSENCIAIS (LOCAL COM UV / MAKE)

### **1. Execução via Makefile (Recomendado)**
```bash
# Executar suíte completa de testes
make test

# Executar testes gerando relatório de cobertura
make test-cov
```

### **2. Execução Direta via uv / pytest**

#### **Executar Todos os Testes**
```bash
# Suíte completa com saída detalhada
PYTHONPATH=src uv run pytest -v

# Suíte completa com cobertura no terminal e HTML
PYTHONPATH=src uv run pytest --cov=app --cov=core --cov-report=term-missing --cov-report=html

# Executar com paralelização (utilizando pytest-xdist)
PYTHONPATH=src uv run pytest -n auto --dist worksteal
```

#### **Executar por Camada de Teste (Domain-First)**
```bash
# Testes Unitários (Use Cases, Services, Schemas, Policies)
PYTHONPATH=src uv run pytest tests/{modulo}/unit/ -v

# Testes de Integração (Repositórios SQLAlchemy, Routers com SQLite In-Memory)
PYTHONPATH=src uv run pytest tests/{modulo}/integration/ -v

# Testes End-to-End (Fluxos de API completos)
PYTHONPATH=src uv run pytest tests/{modulo}/e2e/ -v
```

#### **Executar por Módulo ou Arquivo Específico**
```bash
# Todo o módulo de domínio
PYTHONPATH=src uv run pytest tests/{modulo}/ -v

# Arquivo de teste específico
PYTHONPATH=src uv run pytest tests/{modulo}/unit/test_exemplo_use_case.py -v

# Teste individual (função ou método específico)
PYTHONPATH=src uv run pytest tests/{modulo}/unit/test_exemplo_use_case.py::test_executar_com_sucesso -v
```

---

## 🐳 EXECUTANDO NO DOCKER

Caso deseje executar os testes em um ambiente de containerizado idêntico ao de produção:

```bash
# Subir ambiente dev em container
make dev

# Executar suíte completa no container
make test

# Ou diretamente via docker compose / docker-compose
docker compose exec api PYTHONPATH=src pytest tests/{modulo}/ -v
```

---

## 🎯 MÉTRICAS DE QUALIDADE E COBERTURA

### **Targets de Cobertura (Coverage)**
- **Use Cases & Domain Logic**: ≥ 90%
- **Repositories & Infra Structure**: ≥ 80%
- **Overall Project**: ≥ 80%

### **Comandos de Verificação de Cobertura**
```bash
# Cobertura de um módulo específico
PYTHONPATH=src uv run pytest --cov=app/modules/{modulo} --cov-report=term-missing

# Falhar se a cobertura total for menor que 80%
PYTHONPATH=src uv run pytest --cov=app --cov-fail-under=80

# Gerar e abrir o relatório HTML detalhado
PYTHONPATH=src uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## ⚡ PERFORMANCE E DISTRIBUIÇÃO DA PIRÂMIDE

### **Distribuição de Tipos de Teste**
- **70% Unit Tests**: Execução ultrarrápida em memória com mocks ou instâncias puras.
- **20% Integration Tests**: Validação de queries SQLAlchemy contra SQLite in-memory (`sqlite+aiosqlite:///:memory:`) e `httpx.AsyncClient`.
- **10% E2E Tests**: Validação de fluxos complexos de rotas com autenticação e políticas.

### **Identificação de Gargalos**
```bash
# Listar os 10 testes mais lentos
PYTHONPATH=src uv run pytest --durations=10

# Parar na primeira falha (fail-fast)
PYTHONPATH=src uv run pytest -x
```
