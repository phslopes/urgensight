# 🎯 ÍNDICE COMPLETO: GUIA E PADRÕES DE TESTES

## 📋 DOCUMENTAÇÃO INTERCONECTADA

Este é o **índice principal** que norteia a arquitetura, execução, escrita e manutenção de testes para este repositório backend. A estrutura segue o padrão **Domain-First (Vertical Slice)** com **FastAPI**, **Google Firestore Multi-tenant**, **Pydantic v2** e **Pytest (AnyIO)**.

---

### **🚀 ESTRUTURA DOS GUIAS DE TESTE**

#### **1. PLANO E ARQUITETURA DE TESTES** 
📄 **[test-modernization-plan.md](./test-modernization-plan.md)**
- **Propósito**: Diretrizes arquiteturais para estruturação da pirâmide de testes em projetos Vertical Slice.
- **Conteúdo**: Pirâmide de testes (Unit, Integration, E2E), isolamento com SQLite in-memory, mocking e UOW.
- **Uso**: Consulte para entender como organizar e evoluir a suíte de testes do projeto.

#### **2. PADRÕES DE ESCRITA**
📄 **[test-writing-standards.md](./test-writing-standards.md)**
- **Propósito**: Convenções e regras obrigatórias para escrita de testes de alta qualidade.
- **Conteúdo**: AAA Pattern (*Arrange, Act, Assert*), nomenclatura, fixtures nativas (`uow`, `db_session`, `client`), parametrização, `dependency_overrides` e assertions específicas.
- **Uso**: Consulte DURANTE a criação ou refatoração de qualquer teste.

#### **3. GUIA DE EXECUÇÃO**
📄 **[test-execution-guide.md](./test-execution-guide.md)**
- **Propósito**: Comandos para execução de testes nos ambientes local (via `uv`/`make`) e Docker.
- **Conteúdo**: Comandos por camada (`unit`, `integration`, `e2e`), por módulo, paralelização com `pytest-xdist` e medição de cobertura com pytest-cov.
- **Uso**: Consulte no dia a dia do desenvolvimento e integração contínua (CI).

#### **4. TROUBLESHOOTING E RESOLUÇÃO DE PROBLEMAS**
📄 **[troubleshooting.md](./troubleshooting.md)**
- **Propósito**: Guia prático de diagnóstico para falhas comuns em ambientes de testes assíncronos.
- **Conteúdo**: Resolução de `MissingGreenlet`, vazamento de estado entre testes, limpeza de `dependency_overrides`, testes instáveis (flaky) e otimização de performance.
- **Uso**: Consulte quando encontrar falhas de execução ou comportamentos inesperados.

---

## 🎯 WORKFLOW DE DESENVOLVIMENTO DE TESTES

### **FASE 1: PLANEJAMENTO DO TESTE**
1. Identifique o módulo de domínio (`tests/{modulo}/`).
2. Determine a camada correta:
   - `unit/`: Regras de negócio puras (Use Cases, Services, Schemas, Policies).
   - `integration/`: Persistência real (Repositories via `sqlite+aiosqlite:///:memory:`) ou Roteadores FastAPI.
   - `e2e/`: Fluxos de API completos de ponta a ponta.

### **FASE 2: ESCRITA E MOCKING**
1. Siga as convenções de **test-writing-standards.md**.
2. Utilize fixtures globais (`tests/conftest.py`) sem redefinir instâncias de banco ou clientes HTTP.
3. Garanta isolamento de transação e limpeza do injetor de dependências (`app.dependency_overrides.clear()`).

### **FASE 3: EXECUÇÃO E COBERTURA**
1. Execute os testes com **test-execution-guide.md**.
2. Valide a cobertura de código (meta geral ≥ 80%).
3. Caso ocorram erros assíncronos ou de escopo, consulte **troubleshooting.md**.

---

## 📊 MÉTRICAS DE QUALIDADE EXIGIDAS

- ✅ **Cobertura Geral ≥ 80%** (com foco em Use Cases e Repositórios).
- ✅ **Distribuição da Pirâmide**: ~70% Unitários, ~20% Integração, ~10% E2E.
- ✅ **Isolamento Total**: Nenhum teste deve depender de conexões de rede ou banco externo.
- ✅ **Determinismo**: Execuções consecutivas devem gerar resultados idênticos em paralelo.

---

## 🚀 COMANDOS ESSENCIAIS

### **Execução via Make (Recomendado)**
```bash
# Executar todos os testes
make test

# Executar com relatório de cobertura
make test-cov
```

### **Execução Direta via uv/pytest**
```bash
# Executar suíte de um módulo específico
PYTHONPATH=src uv run pytest tests/{modulo}/ -v

# Executar arquivo específico
PYTHONPATH=src uv run pytest tests/{modulo}/unit/test_exemplo_use_case.py -v
```
