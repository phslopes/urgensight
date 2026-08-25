# Contrato da API — UrgenSight

API REST de triagem automática de laudos médicos. Classifica o texto do
laudo em três níveis de urgência: `normal`, `atencao` ou `urgente`.

- **Base URL (local)**: `http://localhost:8000`
- **Execução**: `uvicorn src.app:app --host 0.0.0.0 --port 8000`
- **Documentação interativa (Swagger UI)**: `http://localhost:8000/docs`
- **Versão do contrato**: `0.2.0`

> **Nota**: o endpoint de predição executa a **inferência real** do modelo
> de ML (`models/model.pkl` — pipeline TF-IDF + classificador, serializado
> via `joblib`). O modelo é carregado em memória **uma única vez**, na
> inicialização da aplicação (lifespan do FastAPI). Se o arquivo estiver
> ausente ou inválido, a API inicia normalmente, mas os endpoints
> respondem `503 Service Unavailable` até que um modelo válido esteja
> presente e a aplicação seja reiniciada.

## Convenções gerais

- Todos os payloads são `application/json; charset=utf-8`.
- Campos não documentados no request são ignorados.
- Erros de validação seguem o formato padrão do FastAPI/Pydantic
  (objeto `detail` com a lista de erros).

---

## Endpoints

| Método | Rota      | Descrição                          |
|--------|-----------|------------------------------------|
| GET    | `/health` | Health check da API                |
| POST   | `/predict`| Classifica a urgência de um laudo  |

---

## GET /health

Verifica se a API está em execução e se o modelo de ML está carregado em
memória. Responders de infraestrutura (load balancers, Docker
`HEALTHCHECK`, probes de Kubernetes) devem tratar `503` como "não pronto
para receber tráfego".

### Request

Sem corpo, parâmetros de query ou headers obrigatórios.

```http
GET /health HTTP/1.1
Host: localhost:8000
```

### Response — `200 OK`

```json
{
  "status": "ok",
  "model_loaded": true
}
```

| Campo          | Tipo    | Descrição                                     |
|----------------|---------|-----------------------------------------------|
| `status`       | string  | Status de saúde da API (`ok`)                 |
| `model_loaded` | boolean | Indica se o modelo de ML está carregado em memória |

### Response — `503 Service Unavailable`

Retornado quando a API está em execução, mas o modelo não pôde ser
carregado no startup (arquivo ausente ou inválido).

```json
{
  "detail": "Modelo de ML indisponivel."
}
```

### Códigos de status

| Código | Quando ocorre                              |
|--------|--------------------------------------------|
| `200`  | API saudável e modelo carregado            |
| `503`  | API em execução, mas modelo indisponível   |

---

## POST /predict

Recebe o texto de um laudo médico e retorna a classe de urgência prevista.

### Request

**Headers obrigatórios**

| Header         | Valor              |
|----------------|--------------------|
| `Content-Type` | `application/json` |

**Body**

```json
{
  "text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."
}
```

| Campo  | Tipo   | Obrigatório | Restrições              | Descrição                              |
|--------|--------|-------------|-------------------------|----------------------------------------|
| `text` | string | sim         | não vazio (`min_length=1`) | Texto do laudo médico a ser classificado |

### Response — `200 OK`

```json
{
  "prediction": "urgente"
}
```

| Campo        | Tipo          | Descrição                              |
|--------------|---------------|----------------------------------------|
| `prediction` | string (Enum) | Classe de urgência prevista pelo modelo |

**Valores possíveis de `prediction`** (Enum — exatos, sem variações de caixa):

| Valor     | Significado                          |
|-----------|--------------------------------------|
| `normal`  | Sem urgência aparente                |
| `atencao` | Requer atenção / acompanhamento      |
| `urgente` | Requer atendimento imediato          |

### Response — `422 Unprocessable Entity` (erro de validação)

Retornado quando o corpo da requisição falha na validação do schema —
ex.: campo `text` ausente, vazio ou com tipo inválido.

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "text"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### Response — `503 Service Unavailable` (modelo indisponível)

Retornado quando o modelo de ML não está carregado (arquivo
`models/model.pkl` ausente, corrompido ou incompatível). A resposta é
imediatamente novamente bem-sucedida após o modelo ser disponibilizado
e a aplicação reiniciada.

```json
{
  "detail": "Modelo de ML indisponivel. Verifique se models/model.pkl existe e e compativel com as versoes de requirements.txt."
}
```

### Códigos de status

| Código | Quando ocorre                                              |
|--------|------------------------------------------------------------|
| `200`  | Predição realizada com sucesso                             |
| `422`  | Payload inválido (schema não atendido)                     |
| `503`  | Modelo de ML não carregado (ausente/inválido)              |
| `500`  | Erro interno inesperado                                    |

---

## Schemas (resumo)

### PredictRequest

```json
{
  "type": "object",
  "required": ["text"],
  "properties": {
    "text": {
      "type": "string",
      "minLength": 1,
      "description": "Texto do laudo medico a ser classificado."
    }
  }
}
```

### PredictResponse

```json
{
  "type": "object",
  "required": ["prediction"],
  "properties": {
    "prediction": {
      "type": "string",
      "enum": ["normal", "atencao", "urgente"],
      "description": "Classe de urgencia prevista: normal, atencao ou urgente."
    }
  }
}
```

---

## Exemplos de uso (curl)

### Health check

```bash
curl -s http://localhost:8000/health
```

Resposta:

```json
{"status": "ok", "model_loaded": true}
```

### Predição

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Severe chest pain with dyspnea and diaphoresis, ECG shows ST elevation, suspect acute myocardial infarction."}'
```

Resposta esperada (inferência real do modelo):

```json
{"prediction": "urgente"}
```
