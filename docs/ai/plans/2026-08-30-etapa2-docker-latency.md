# Etapa 2: Validação Docker e Baseline de Latência — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validar que a API FastAPI funciona dentro do container Docker com o modelo real e medir o baseline de latência para benchmark futuro.

**Architecture:** Gerar `models/model.pkl` → build da imagem Docker com modelo → validar `/health` e `/predict` dentro do container → medir latência ponta a ponta com `hey` → preencher `docs/baseline_latency.md`.

**Tech Stack:** FastAPI, Docker, Uvicorn, `hey` (benchmark tool), JSON

---

## File Structure

| Arquivo | Responsabilidade | Status |
|---------|------------------|--------|
| `models/model.pkl` | Modelo serializado treinado | ✅ Existe (entregue por Etapa 1) |
| `src/app.py` | API FastAPI com lifespan | ✅ Pronto |
| `Dockerfile` | Build de imagem com modelo | ✅ Pronto |
| `docs/baseline_latency.md` | Relatório de medições | 🔴 Template vazio |
| `README.md` | Instruções de Docker e medição | 🟡 Parcial |

---

## Task 1: Gerar `models/model.pkl` localmente

**Files:**
- Use: `Makefile` (target `train`)
- Output: `models/model.pkl`

- [ ] **Step 1: Verificar se `models/model.pkl` existe**

```bash
ls -lh models/model.pkl 2>/dev/null || echo "Arquivo não existe"
```

Expected: Se retornar "Arquivo não existe", prosseguir para Step 2.

- [ ] **Step 2: Gerar modelo**

```bash
uv run python -m src.prepare_dataset && uv run python -m src.train
```

Expected: Sucesso com saída finalizando em algo como "Model saved to models/model.pkl". Nota: `make train` não existe no Makefile deste projeto.

- [ ] **Step 3: Validar tamanho e integridade**

```bash
ls -lh models/model.pkl && file models/model.pkl
```

Expected: Arquivo com tamanho > 100KB, tipo "data"

---

## Task 2: Build da imagem Docker

**Files:**
- Use: `Dockerfile`
- Build context: raiz do projeto

- [ ] **Step 1: Limpar build cache anterior (opcional)**

```bash
docker rmi urgensight:latest 2>/dev/null || echo "Nenhuma imagem anterior"
```

- [ ] **Step 2: Build da imagem**

```bash
docker build -t urgensight:latest .
```

Expected: Build completo sem erros. Saída final: `Successfully tagged urgensight:latest`

- [ ] **Step 3: Listar imagem**

```bash
docker images | grep urgensight
```

Expected: Uma linha com `urgensight`, `latest`, tamanho ~500MB–1GB

---

## Task 3: Testar `/health` dentro do container

**Files:**
- Use: Container em execução

- [ ] **Step 1: Iniciar container em background**

```bash
docker run -d --name api-test -p 8000:8000 urgensight:latest
```

Expected: Retorna container ID (ex: `a1b2c3d4e5f6`)

- [ ] **Step 2: Aguardar inicialização**

```bash
sleep 5
```

- [ ] **Step 3: Testar `/health` via HTTP**

```bash
curl -s http://localhost:8000/health | jq .
```

Expected: Resposta JSON `{"status": "ok"}` (ou conforme `docs/api_contract.md`)

- [ ] **Step 4: Verificar logs do container**

```bash
docker logs api-test | tail -10
```

Expected: Logs do Uvicorn com "Application startup complete"

- [ ] **Step 5: Parar container**

```bash
docker stop api-test && docker rm api-test
```

---

## Task 4: Testar `/predict` com entrada válida

**Files:**
- Use: Container em execução
- Test data: `data/benchmark_samples.json`

- [ ] **Step 1: Iniciar container**

```bash
docker run -d --name api-predict -p 8000:8000 urgensight:latest
sleep 5
```

- [ ] **Step 2: Chamar `/predict` com payload válido**

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Paciente apresenta febre alta e tosse persistente. Requer avaliacao urgente."}' | jq .
```

Expected: JSON com campo `prediction` contendo `"normal"`, `"atencao"` ou `"urgente"`

- [ ] **Step 3: Testar payload inválido (texto vazio)**

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": ""}' | jq .
```

Expected: HTTP 422 Unprocessable Entity com mensagem de validação

- [ ] **Step 4: Parar container**

```bash
docker stop api-predict && docker rm api-predict
```

---

## Task 5: Instalar ferramenta de benchmark `hey`

- [ ] **Step 1: Verificar se `hey` está instalado**

```bash
which hey || echo "hey não instalado"
```

- [ ] **Step 2: Instalar `hey` (macOS)**

```bash
brew install hey
```

Expected: Instalação concluída com sucesso

- [ ] **Step 3: Verificar instalação**

```bash
hey -h | head -5
```

Expected: Exibe ajuda do comando `hey`

---

## Task 6: Medir latência baseline com container rodando

- [ ] **Step 1: Iniciar container**

```bash
docker run -d --name api-latency -p 8000:8000 urgensight:latest
sleep 5
```

- [ ] **Step 2: Executar benchmark com 100 requisições**

```bash
hey -n 100 -c 4 -m POST -H "Content-Type: application/json" \
  -d '{"text": "Paciente apresenta tosse e febre. Necessita triagem urgente."}' \
  http://localhost:8000/predict
```

Expected: Relatório com:
- `Total:`
- `Slowest:` / `Fastest:` / `Average:`
- `Requests/sec:`
- Histograma de tempo de resposta

- [ ] **Step 3: Salvar saída do benchmark**

```bash
hey -n 100 -c 4 -m POST -H "Content-Type: application/json" \
  -d '{"text": "Paciente apresenta tosse e febre. Necessita triagem urgente."}' \
  http://localhost:8000/predict > /tmp/latency_results.txt

grep -E "Slowest:|Fastest:|Average:|Requests/sec:" /tmp/latency_results.txt
```

- [ ] **Step 4: Parar container**

```bash
docker stop api-latency && docker rm api-latency
```

---

## Task 7: Preencher `docs/baseline_latency.md` com dados reais

**Files:**
- Modify: `docs/baseline_latency.md`

- [ ] **Step 1: Ler template existente**

```bash
cat docs/baseline_latency.md
```

- [ ] **Step 2: Atualizar com dados do benchmark (substituir placeholders)**

Preencher a tabela de resultados com os valores capturados em Task 6:

```markdown
# Baseline de Latência — API FastAPI em Docker

> **Data:** 2026-08-30  
> **Ferramenta:** `hey` (100 requisições, 4 conexões concorrentes)  
> **Endpoint:** `POST /predict`  
> **Payload:** `{"text": "Paciente apresenta tosse e febre. Necessita triagem urgente."}`

## Resultados — Modelo Baseline (Logistic Regression + TF-IDF)

| Métrica | Valor |
|---------|-------|
| **Média (ms)** | [preencher com Average do hey × 1000] |
| **Mediana (ms)** | [preencher com 50th percentile × 1000] |
| **Mínimo (ms)** | [preencher com Fastest × 1000] |
| **Máximo (ms)** | [preencher com Slowest × 1000] |
| **P95 (ms)** | [preencher com 95th percentile × 1000] |
| **Throughput (req/s)** | [preencher com Requests/sec] |

## Ambiente

- **Container:** `urgensight:latest`
- **Base:** Python 3.11 + FastAPI + Uvicorn
- **Modelo:** `models/model.pkl` (Logistic Regression, TF-IDF)
- **Máquina:** [especificar CPU/RAM]

## Notas

- Concorrência: 4 conexões simultâneas
- Iterações: 100 requisições sucessivas

---

**Benchmark Otimizado** (será preenchido por Etapa 4)
```

- [ ] **Step 3: Commit**

```bash
git add docs/baseline_latency.md
git commit -m "docs(baseline): preencher latência baseline com dados reais do Docker"
```

---

## Task 8: Atualizar README e `phase-tracking.md`

- [ ] **Step 1: Adicionar/atualizar seção Docker no README**

Verificar se existe seção Docker e adicionar instruções de medição:

```bash
grep -n "Docker" README.md | head -5
```

Se não houver seção de medição de latência, adicionar:

```markdown
## 🐳 Docker

### Build e execução

```bash
make train                          # gerar modelo (se ausente)
docker build -t urgensight:latest . # build
docker run -p 8000:8000 urgensight:latest # executar

# Validar
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Exemplo de texto clínico"}'
```

### Medição de latência baseline

```bash
brew install hey  # macOS
hey -n 100 -c 4 -m POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Paciente apresenta tosse e febre."}' \
  http://localhost:8000/predict
```

Resultados: ver `docs/baseline_latency.md`
```

- [ ] **Step 2: Marcar Etapa 2 como completa em `docs/specs/phase-tracking.md`**

Em `docs/specs/phase-tracking.md`, atualizar:
- Tabela de etapas: `🟡 Quase pronta` → `✅ Concluída`
- Checkboxes pendentes:
  - `- [ ] Subir o container e validar GET /health` → `- [x]`
  - `- [ ] Validar POST /predict rodando exclusivamente dentro do container` → `- [x]`
  - `- [ ] Medir latência baseline da API em Docker` → `- [x]`
  - `- [ ] Salvar baseline em docs/baseline_latency.md` → `- [x]`
  - `- [ ] Entregar baseline e Dockerfile ao Integrante 4` → `- [x]`
  - `- [ ] API com modelo real rodando em Docker` → `- [x]`

- [ ] **Step 3: Commit final**

```bash
git add README.md docs/specs/phase-tracking.md
git commit -m "chore(etapa2): marcar Etapa 2 como concluída — Docker validado, baseline medido"
```

---

## Self-Review vs Spec

| Requisito do phase-tracking.md | Coberto |
|---|---|
| Build da imagem Docker | ✅ Task 2 |
| Subir container e validar `/health` | ✅ Task 3 |
| Validar `/predict` dentro do container | ✅ Task 4 |
| Medir latência com `hey` | ✅ Tasks 5, 6 |
| Preencher `docs/baseline_latency.md` | ✅ Task 7 |
| Entregar baseline ao Integrante 4 | ✅ Task 7 (via commit) |
| Atualizar phase-tracking | ✅ Task 8 |
