# 📐 PADRÕES DE ESCRITA DE TESTES

## 🎯 ESTRUTURA OBRIGATÓRIA (AAA Pattern)

Todo teste deve ser organizado de forma clara e explícita utilizando o padrão **Arrange, Act, Assert**:

```python
@pytest.mark.asyncio
async def test_nome_do_metodo_cenario_resultado_esperado():
    # Arrange — Preparação de dados, mocks e estado inicial
    payload = ExemploCreateSchema(nome="Item Teste", valor=100.0)
    mock_uow = AsyncMock()
    use_case = CriarExemploUseCase(uow=mock_uow)

    # Act — Execução da ação sob teste
    resultado = await use_case.execute(payload)

    # Assert — Verificação dos resultados e chamadas de método
    assert resultado.nome == "Item Teste"
    mock_uow.commit.assert_called_once()
```

---

## 📝 CONVENÇÕES DE NOMENCLATURA

### **1. Classes de Teste**
- Deve utilizar PascalCase com o prefixo `Test`.
- Nome alinhado ao componente testado.

```python
class TestExemploUseCase:       # Testes do Use Case Criar/Atualizar Exemplo
class TestExemploRepository:    # Testes do Repositório SQLAlchemy de Exemplo
class TestExemploSchemas:       # Testes de validação dos Schemas Pydantic
class TestExemploRouter:        # Testes das rotas HTTP de Exemplo
```

### **2. Métodos de Teste**
- Deve utilizar snake_case com o prefixo `test_`.
- Formato recomendado: `test_<acao>_<cenario>_<resultado_esperado>`

```python
def test_criar_item_dados_validos_retorna_sucesso():        # Happy path
def test_criar_item_nome_duplicado_lanca_excecao():        # Erro de regra de negócio
def test_buscar_por_id_inexistente_retorna_404():          # Caso não encontrado
def test_atualizar_item_sem_permissao_retorna_403():       # Erro de autorização
```

### **3. Arquivos de Teste**
- Localizados dentro de `tests/{modulo}/{unit|integration|e2e}/`.
- Nome do arquivo deve iniciar com `test_`.

```text
tests/
└── {modulo}/
    ├── unit/
    │   ├── test_exemplo_use_case.py
    │   └── test_exemplo_schemas.py
    ├── integration/
    │   ├── test_exemplo_repository.py
    │   └── test_exemplo_router.py
    └── e2e/
        └── test_exemplo_workflow.py
```

---

## 🎭 ESTRATÉGIAS DE MOCK E INJEÇÃO

### **1. Mocks em Testes Unitários (Use Cases / Services)**
- Mockar apenas dependências externas, I/O ou o Unit of Work / Repositórios.
- Nunca mockar a própria classe ou método sob teste.

```python
# ✅ CORRETO: Mockar o Unit of Work ou dependência externa
@pytest.mark.asyncio
async def test_enviar_notificacao_sucesso():
    mock_email_service = AsyncMock()
    mock_email_service.send.return_value = True

    use_case = EnviarNotificacaoUseCase(email_service=mock_email_service)
    resultado = await use_case.execute(user_id=1)

    assert resultado is True
    mock_email_service.send.assert_called_once()
```

### **2. Injeção de Dependências em Testes de Rota (FastAPI)**
- Utilizar `app.dependency_overrides` para injetar o UOW em memória ou mocks.
- **Obrigatorio**: Limpar os overrides ao final do teste via `app.dependency_overrides.clear()` ou bloco `try/finally`.

```python
@pytest.mark.asyncio
async def test_rota_criar_item(client, uow):
    app.dependency_overrides[get_uow] = lambda: uow
    try:
        response = await client.post("/v1/exemplos/", json={"nome": "Item"})
        assert response.status_code == 201
    finally:
        app.dependency_overrides.clear()
```

---

## 🔍 ASSERTIONS ESPECÍFICAS

### **✅ DO: Assertions Precisas e Descritivas**
```python
# Verificação de atributos específicos
assert resultado.id is not None
assert resultado.nome == "Item Teste"
assert resultado.valor == Decimal("100.00")

# Verificação de status e payload HTTP
assert response.status_code == 201
assert response.json()["detalhe"] == "Item criado com sucesso"

# Verificação de chamadas de mock
mock_uow.commit.assert_called_once()
mock_repo.add.assert_called_with(entidade_esperada)
```

### **❌ DON'T: Assertions Genéricas**
```python
assert resultado                    # ❌ Muito genérico
assert resultado is not None        # ❌ Não valida conteúdo
assert response.status_code != 500  # ❌ Não garante o código correto (ex: 200 vs 201)
```

---

## 🧪 TESTES PARAMETRIZADOS (Pytest)

Utilize `pytest.mark.parametrize` para testar múltiplos cenários de validação ou borda sem duplicar lógica de teste:

```python
@pytest.mark.parametrize("valor_invalido,mensagem_erro", [
    (-10.0, "Input should be greater than 0"),
    (0.0, "Input should be greater than 0"),
    (1000000.0, "Input should be less than 100000"),
])
def test_validacao_limites_valor(valor_invalido, mensagem_erro):
    with pytest.raises(ValidationError) as exc_info:
        ExemploSchema(nome="Teste", valor=valor_invalido)
    assert mensagem_erro in str(exc_info.value)
```

---

## 🏷️ MARKERS E FIXTURES NATIVAS

### **Markers Padrão**
Sempre utilize os markers apropriados para categorização:
- `@pytest.mark.unit`: Testes unitários isolados em memória.
- `@pytest.mark.integration`: Testes de integração (repositórios/rotas).
- `@pytest.mark.e2e`: Testes de fluxos completos.
- `@pytest.mark.asyncio`: Requerido para funções de teste assíncronas (`async def`).

### **Fixtures Globais Reutilizáveis (`tests/conftest.py`)**
- `db_session`: Sessão assíncrona SQLAlchemy (`AsyncSession`) vinculada ao SQLite em memória.
- `uow`: Instância do `UnitOfWorkImpl` vinculada à `db_session`.
- `client`: Instância do `httpx.AsyncClient` com `ASGITransport(app=app)`.
- `init_db`: Fixture autouse que prepara e limpa o schema do banco em memória a cada execução.
