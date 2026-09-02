# Tech Challenge — Divisão em 4 Etapas Macro

> **Prazo:** 15/09
> **Estratégia:** as etapas possuem uma ordem de dependência, mas as pessoas podem iniciar partes independentes em paralelo.
> **Vídeo:** responsabilidade compartilhada por todo o grupo; não entra na divisão de carga técnica.
> **Última atualização:** 2026-08-30

| Etapa | Responsável | Foco                                                | Critérios diretamente atendidos   | Status        |
| ----- | ------------ | --------------------------------------------------- | --------------------------------- | ------------- |
| 1     | Integrante 1 | Dados, modelo NLP e DAG Airflow                     | Modelagem base + Airflow (15%)    | ✅ Concluída  |
| 2     | Integrante 2 | API FastAPI, Docker e arquitetura em nuvem          | API/Docker + README (15%)         | ✅ Concluída  |
| 3     | Integrante 3 | Testes, CI/CD e monitoramento                       | CI/CD (15%) + Monitoramento (20%) | ✅ Concluída  |
| 4     | Integrante 4 | Otimização de latência e benchmark                  | Modelagem/Otimização (20%)        | ⬜ Não iniciada |
| Final | Todos        | README final, validação, vídeo STAR e submissão     | README (15%) + Vídeo (15%)        | ⬜ Não iniciada |

---

# Etapa 1 — Dados, Modelo NLP e Airflow ✅

**Responsável:** Integrante 1
**Janela principal:** 10/08 a 31/08
**Status:** Concluída

## 1.1. Dataset e preparação

- [x] Selecionar dataset público de classificação de textos médicos ou triagem
- [x] Validar que o dataset possui pelo menos **2.000 amostras**
- [x] Validar que existe uma coluna de texto e uma coluna target
- [x] Documentar fonte, formato e instruções de obtenção do dataset — `docs/dataset.md`
- [x] Mapear os valores do target para as classes do projeto: `normal`, `atencao` e `urgente`
- [x] Verificar e tratar registros nulos, duplicados e textos vazios
- [x] Avaliar distribuição das classes — `docs/dataset_distribution.md`
- [x] Criar split de treino e teste com seed fixa
- [x] Criar amostras de entrada para teste e benchmark em `data/benchmark_samples.json`

## 1.2. Modelo baseline

- [x] Criar `src/train.py` executável via linha de comando
- [x] Implementar carregamento do dataset CSV
- [x] Implementar validação das colunas obrigatórias
- [x] Implementar vetorização de texto com TF-IDF
- [x] Treinar classificador NLP leve com Scikit-Learn
- [x] Priorizar modelo compatível com otimização futura (Logistic Regression)
- [x] Fixar seeds para reprodutibilidade
- [x] Avaliar o modelo com métricas básicas (accuracy, F1-score por classe)
- [x] Salvar métricas em `docs/model_metrics.md`
- [x] Serializar pipeline completo em `models/model.pkl`
- [x] Validar carregamento do modelo em um script isolado
- [x] Entregar `models/model.pkl`, instruções de carregamento e amostras de teste ao Integrante 2

## 1.3. DAG Airflow

- [x] Subir ambiente local do Airflow antes de implementar a DAG
- [x] Criar `dags/train_pipeline.py`
- [x] Criar task de carregamento/validação do dataset
- [x] Criar task de treino reutilizando a lógica de `src/train.py`
- [x] Criar task de salvamento do modelo treinado
- [x] Configurar ordem obrigatória: **carregamento de dados → treino → salvamento do modelo**
- [x] Configurar a DAG para simular um fluxo de retreino
- [x] Executar a DAG com sucesso no Airflow
- [x] Salvar print da interface e logs da execução bem-sucedida — `docs/airflow_run_evidence.png`
- [x] Documentar no README como iniciar o Airflow e disparar a DAG

## 1.4. Handoff técnico

- [x] Entregar modelo baseline ao Integrante 2 até 24/08
- [x] Entregar amostras de benchmark ao Integrante 4 até 24/08
- [x] Entregar evidências da DAG ao grupo até 31/08
- [x] Informar compatibilidade preliminar do pipeline com ONNX ao Integrante 4
- [x] Registrar plano alternativo caso ONNX não seja compatível com o modelo

### Entregáveis da Etapa 1

- [x] Dataset documentado e validado
- [x] `src/train.py`
- [x] `models/model.pkl` *(gitignored; regenerar com `make train` ou `python -m src.train`)*
- [x] `docs/model_metrics.md`
- [x] `data/benchmark_samples.json`
- [x] `dags/train_pipeline.py`
- [x] Evidência de DAG executada com sucesso (`docs/airflow_run_evidence.png`)

---

# Etapa 2 — API FastAPI, Docker e Arquitetura ✅

**Responsável:** Integrante 2
**Janela principal:** 12/08 a 31/08
**Status:** Concluída — Docker validado com modelo real, baseline de latência medido e registrado.

## 2.1. Fundação da API

- [x] Criar `src/app.py` com FastAPI
- [x] Definir contrato da API em `docs/api_contract.md`
- [x] Criar request Pydantic com campo obrigatório `text`
- [x] Criar response Pydantic com campo `prediction`
- [x] Definir conjunto permitido de classes: `normal`, `atencao`, `urgente`
- [x] Criar `GET /health`
- [x] Criar `POST /predict`
- [x] Implementar resposta mockada para destravar testes e CI/CD
- [x] Validar API localmente com Uvicorn e `curl` ou Postman
- [x] Comunicar contrato dos endpoints ao Integrante 3

## 2.2. Integração do modelo

- [x] Receber `models/model.pkl` do Integrante 1
- [x] Implementar carregamento do modelo ao iniciar a aplicação (lifespan)
- [x] Garantir que o modelo não seja carregado a cada requisição (`app.state.model`)
- [x] Substituir predição mockada pela inferência do pipeline real
- [x] Validar endpoint com textos conhecidos do dataset de teste
- [x] Tratar erro de modelo ausente ou inválido com resposta controlada (503)
- [x] Revisar contrato de resposta após integração com o modelo

## 2.3. Dockerização

- [x] Criar `Dockerfile` funcional para serviço de inferência
- [x] Incluir código, dependências e artefato do modelo na imagem
- [x] Expor a porta da API
- [x] Configurar comando de inicialização com Uvicorn
- [x] Fazer build da imagem localmente
- [x] Subir o container e validar `GET /health`
- [x] Validar `POST /predict` rodando exclusivamente dentro do container
- [x] Criar instruções de build e execução no README
- [x] Medir latência baseline da API em Docker (100 req, 4 concurrent — p50: 2.4ms, p95: 5.8ms, 1220 req/s)
- [x] Salvar baseline em `docs/baseline_latency.md`
- [x] Entregar baseline e Dockerfile ao Integrante 4

## 2.4. Decisão arquitetural em nuvem

- [x] Escrever seção de arquitetura no README
- [x] Comparar processamento batch e real-time para triagem de laudos
- [x] Escolher estratégia recomendada para o cenário hospitalar
- [x] Selecionar AWS, Azure ou GCP como referência arquitetural
- [x] Justificar a escolha com base em API de inferência, escalabilidade e contexto clínico
- [x] Deixar explícito que o escopo exigido é a análise textual, não o provisionamento real em nuvem

### Entregáveis da Etapa 2

- [x] `src/app.py`
- [x] `GET /health`
- [x] `POST /predict`
- [x] `docs/api_contract.md`
- [x] `Dockerfile`
- [x] API com modelo real rodando em Docker
- [x] `docs/baseline_latency.md` com dados reais
- [x] Decisão arquitetural documentada no README

---

# Etapa 3 — Testes, CI/CD e Observabilidade ✅

**Responsável:** Integrante 3
**Janela principal:** 12/08 a 09/09
**Status:** Concluída. CI/CD verde no GitHub Actions (lint ∥ test → smoke-train →
build), API instrumentada com Prometheus, stack Docker Compose (API +
Prometheus + Grafana) validada e dashboard Grafana provisionado com 6 painéis
populados por tráfego real.

## 3.1. Testes automatizados

- [x] Configurar `pytest` (`pyproject.toml`)
- [x] Criar teste para `GET /health`
- [x] Criar teste para `POST /predict` com entrada válida
- [x] Criar teste para payload inválido
- [x] Criar mock/fixture de modelo para os testes não dependerem do modelo final (`conftest.py` + fixtures em `tests/test_app.py`)
- [x] Configurar linter `ruff` (`pyproject.toml`)
- [x] Garantir execução local de lint e testes (`make test` / `make lint`)
- [x] Rodar testes após a integração do modelo real

## 3.2. GitHub Actions

- [x] Criar `.github/workflows/ci.yml`
- [x] Configurar execução automática em `push`
- [x] Configurar execução em `pull_request`
- [x] Criar job de lint
- [x] Criar job de testes com `pytest`
- [x] Criar job de build da imagem Docker
- [x] Garantir no mínimo duas automações obrigatórias: lint e testes
- [x] Validar workflow verde em push real
- [x] Adicionar badge do GitHub Actions ao README
- [x] Documentar comandos de teste e lint no README

## 3.3. Instrumentação com Prometheus

- [x] Criar branch própria para alterações em `src/app.py`
- [x] Adicionar contador de requisições recebidas
- [x] Adicionar métrica de latência/tempo de resposta
- [x] Adicionar contador de erros
- [x] Expor endpoint `GET /metrics`
- [x] Validar que métricas são atualizadas após requisições ao `/predict`
- [x] Confirmar que `/metrics` responde no formato Prometheus
- [x] Abrir pull request para integração das métricas

## 3.4. Stack Docker Compose

- [x] Criar `monitoring/prometheus.yml`
- [x] Configurar scrape da API pelo endpoint `/metrics`
- [x] Criar `docker-compose.yml` para monitoring *(o existente é exclusivo para Airflow)*
- [x] Adicionar serviço da API
- [x] Adicionar serviço do Prometheus
- [x] Adicionar serviço do Grafana
- [x] Configurar portas, rede e dependências entre serviços
- [x] Subir a stack com `docker compose up --build`
- [x] Confirmar API acessível
- [x] Confirmar Prometheus acessível
- [x] Confirmar que o target da API aparece como **UP** no Prometheus

## 3.5. Dashboard Grafana

- [x] Configurar Prometheus como datasource do Grafana
- [x] Criar painel de total de requisições
- [x] Criar painel de latência/tempo de resposta
- [x] Criar painel de taxa de erro
- [x] Garantir o mínimo obrigatório de três painéis
- [x] Criar `scripts/generate_load.py` para gerar tráfego no endpoint `/predict`
- [x] Popular os gráficos com dados reais
- [x] Exportar dashboard para `monitoring/dashboard.json`
- [x] Salvar prints do dashboard em `docs/`
- [x] Documentar acesso e execução da stack no README

### Entregáveis da Etapa 3

- [x] Testes com `pytest`
- [x] Lint configurado
- [x] `.github/workflows/ci.yml`
- [x] Workflow verde
- [x] API instrumentada com `prometheus_client`
- [x] `docker-compose.yml` (stack de monitoring)
- [x] `monitoring/prometheus.yml`
- [x] Dashboard Grafana com 3 painéis
- [x] `monitoring/dashboard.json`
- [x] Prints com métricas reais

### Adendo (2026-09-02) — DVC, uv e Python 3.12

- [x] Piso único de Python 3.12 ([ADR-0008](../ai/adr/0008-piso-unico-de-python.md))
- [x] uv com lock único e grupos PEP 735 ([ADR-0007](../ai/adr/0007-uv-com-lock-unico.md))
- [x] Pipeline DVC reprodutível ([ADR-0006](../ai/adr/0006-dvc-como-fonte-de-verdade-do-pipeline.md))

Fora da rubrica da Fase 3 (DVC pertence à Fase 2); adotado para eliminar a
divergência de `numpy` entre treino e inferência e centralizar os
hiperparâmetros. **A Etapa 4 (ONNX/benchmark, 20% da nota) permanece a maior
pendência.**

---

# Etapa 4 — Otimização e Benchmark de Latência ⬜

**Responsável:** Integrante 4
**Janela principal:** 17/08 a 10/09
**Status:** Não iniciada. Depende do baseline de latência da Etapa 2 (`docs/baseline_latency.md`).

## 4.1. Planejamento de otimização

- [ ] Alinhar com Integrante 1 qual modelo baseline foi escolhido
- [ ] Escolher técnica de otimização vista em aula: ONNX Runtime, quantização básica ou pruning
- [ ] Priorizar ONNX Runtime como primeira tentativa, se compatível
- [ ] Definir plano B antes de iniciar a conversão
- [ ] Criar `scripts/benchmark_latency.py`
- [ ] Padronizar uso de `data/benchmark_samples.json`
- [ ] Definir métricas do benchmark: média, mediana, p95, mínimo, máximo e número de execuções
- [ ] Criar tabela inicial em `docs/latency_results.md`

## 4.2. Otimização do modelo

- [ ] Receber modelo baseline do Integrante 1
- [ ] Converter o modelo para ONNX ou aplicar a técnica alternativa selecionada
- [ ] Salvar artefato otimizado (`models/model.onnx` ou equivalente)
- [ ] Validar carregamento do artefato otimizado
- [ ] Comparar previsões do modelo original e otimizado em amostras conhecidas
- [ ] Investigar e documentar divergências de predição, se existirem
- [ ] Entregar instruções de integração do modelo otimizado ao Integrante 2

## 4.3. Benchmark comparativo

- [ ] Executar benchmark do modelo original
- [ ] Executar benchmark do modelo otimizado
- [ ] Garantir mesma máquina, mesmo conjunto de entradas e mesmo número de iterações
- [ ] Descartar warm-up ou registrá-lo separadamente
- [ ] Calcular percentual de melhoria de latência
- [ ] Registrar resultados em `docs/latency_results.md`
- [ ] Apoiar o Integrante 2 na medição ponta a ponta da API otimizada em Docker
- [ ] Comparar latência final da API com o baseline de `docs/baseline_latency.md`
- [ ] Atualizar README com tabela de resultados e ganho obtido

### Entregáveis da Etapa 4

- [ ] `scripts/benchmark_latency.py`
- [ ] Modelo otimizado (`models/model.onnx` ou equivalente)
- [ ] Resultados comparativos reproduzíveis
- [ ] Evidência de melhoria de latência
- [ ] Tabela de benchmark no README
- [ ] Instruções para inferência otimizada

---

# Responsabilidades coletivas finais

> **Não atribuir a uma pessoa só.** Cada integrante deve preparar as evidências da própria etapa; a gravação e revisão são do grupo.

## README

- [ ] Integrante 1 documenta dataset, modelo e DAG Airflow
- [ ] Integrante 2 documenta API, Docker e decisão arquitetural
- [ ] Integrante 3 documenta testes, CI/CD, Prometheus, Grafana e Docker Compose
- [ ] Integrante 4 documenta técnica de otimização e benchmark
- [ ] Todos validam comandos de execução
- [ ] Um integrante consolida formatação final, sem ser responsável por produzir conteúdo técnico dos demais
- [ ] Grupo executa o projeto do zero seguindo exclusivamente o README

## Vídeo STAR — coletivo

- [ ] Todos revisam roteiro STAR
- [ ] Todos participam da explicação ou demonstração da própria etapa
- [ ] Demonstrar problema clínico e importância da triagem
- [ ] Demonstrar requisitos técnicos: CI/CD, Airflow, monitoramento e latência
- [ ] Demonstrar GitHub Actions verde
- [ ] Demonstrar DAG executada
- [ ] Demonstrar Grafana com métricas reais
- [ ] Demonstrar comparação original versus otimizado
- [ ] Garantir duração máxima de 5 minutos
- [ ] Publicar vídeo e adicionar link ao README

## Validação e submissão

- [ ] Conferir API funcional em Docker
- [ ] Conferir workflow GitHub Actions funcional
- [ ] Conferir DAG Airflow funcional
- [ ] Conferir Compose com API + Prometheus + Grafana
- [ ] Conferir dashboard com mínimo de 3 painéis
- [ ] Conferir modelo otimizado e ganho de latência demonstrado
- [ ] Conferir histórico de commits semântico e organizado
- [ ] Conferir README, JSON/prints do dashboard e link do vídeo
- [ ] Fazer push final
- [ ] Submeter até 15/09

---

# Cronograma de checkpoints

| Data limite     | Resultado que precisa existir                                                     | Status  |
| --------------- | --------------------------------------------------------------------------------- | ------- |
| **16/08** | Dataset validado, API mockada, testes iniciais e benchmark estruturado            | ✅ OK   |
| **24/08** | Modelo baseline salvo, API integrada ou pronta para integrar, CI verde            | 🟡 Parcial — CI não iniciado |
| **31/08** | Docker funcional, baseline de latência, DAG Airflow executada                    | ✅ OK — Docker validado, baseline medido (2026-08-30) |
| **06/09** | Métricas expostas, Prometheus coletando dados, técnica de otimização aplicada | 🟡 Parcial — Etapa 3 concluída (métricas expostas e Prometheus coletando); técnica de otimização da Etapa 4 pendente |
| **10/09** | Grafana com 3 painéis, benchmark final, README quase fechado                     | 🟡 Parcial — Grafana com 6 painéis populados (Etapa 3 concluída); benchmark final da Etapa 4 pendente |
| **12/09** | Vídeo ensaiado, solução executada do zero, evidências revisadas               | ⬜ Pendente |
| **15/09** | Entrega submetida                                                                 | ⬜ Pendente |

## Dependências críticas

- **Etapa 1 → Etapa 2:** ✅ Concluída — modelo.pkl entregue, Docker validado com modelo real.
- **Etapa 1 → Etapa 4:** ✅ modelo baseline pronto; benchmark_samples.json disponível. Aguardando início da Etapa 4.
- **Etapa 2 → Etapa 3:** ✅ Concluída — API instrumentada com `prometheus_client`, Prometheus e Grafana coletando e exibindo dados reais.
- **Etapa 2 → Etapa 4:** ✅ baseline_latency.md preenchido com dados reais (p50: 2.4ms, p95: 5.8ms, 1220 req/s).
- **Etapa 3 → vídeo:** dashboard precisa estar populado antes da gravação.
- **Etapa 4 → vídeo:** comparação de latência precisa estar fechada antes da narrativa de resultado.

---

## Resumo de pendências prioritárias (por checkpoint 06/09)

| Prioridade | Item | Responsável |
| ---------- | ---- | ----------- |
| ✅ FEITO   | Docker validado com modelo real, baseline de latência medido | Integrante 2 |
| ✅ FEITO   | Criar `.github/workflows/ci.yml` com jobs de lint e pytest | Integrante 3 |
| 🟠 ALTO    | Iniciar planejamento da otimização (ONNX ou alternativa) | Integrante 4 |
