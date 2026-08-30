
# Tech Challenge — Divisão em 4 Etapas Macro

> **Prazo:** 15/09
> **Estratégia:** as etapas possuem uma ordem de dependência, mas as pessoas podem iniciar partes independentes em paralelo.
> **Vídeo:** responsabilidade compartilhada por todo o grupo; não entra na divisão de carga técnica.

| Etapa | Responsável | Foco                                                | Critérios diretamente atendidos  |
| ----- | ------------ | --------------------------------------------------- | --------------------------------- |
| 1     | Integrante 1 | Dados, modelo NLP e DAG Airflow                     | Modelagem base + Airflow (15%)    |
| 2     | Integrante 2 | API FastAPI, Docker e arquitetura em nuvem          | API/Docker + README (15%)         |
| 3     | Integrante 3 | Testes, CI/CD e monitoramento                       | CI/CD (15%) + Monitoramento (20%) |
| 4     | Integrante 4 | Otimização de latência e benchmark               | Modelagem/Otimização (20%)      |
| Final | Todos        | README final, validação, vídeo STAR e submissão | README (15%) + Vídeo (15%)       |

---

# Etapa 1 — Dados, Modelo NLP e Airflow

**Responsável:** Integrante 1
**Janela principal:** 10/08 a 31/08
**Objetivo:** disponibilizar um pipeline de treino reproduzível, um modelo baseline funcional e uma DAG Airflow que simule o retreino.

## 1.1. Dataset e preparação

- [ ] Selecionar dataset público de classificação de textos médicos ou triagem
- [ ] Validar que o dataset possui pelo menos **2.000 amostras**
- [ ] Validar que existe uma coluna de texto e uma coluna target
- [ ] Documentar fonte, formato e instruções de obtenção do dataset
- [ ] Mapear os valores do target para as classes do projeto: `normal`, `atencao` e `urgente`, se necessário
- [ ] Verificar e tratar registros nulos, duplicados e textos vazios
- [ ] Avaliar distribuição das classes
- [ ] Criar split de treino e teste com seed fixa
- [ ] Criar amostras de entrada para teste e benchmark em `data/benchmark_samples.json`

## 1.2. Modelo baseline

- [ ] Criar `src/train.py` executável via linha de comando
- [ ] Implementar carregamento do dataset CSV
- [ ] Implementar validação das colunas obrigatórias
- [ ] Implementar vetorização de texto com TF-IDF
- [ ] Treinar classificador NLP leve com Scikit-Learn ou framework permitido
- [ ] Priorizar modelo compatível com otimização futura, como Logistic Regression, Linear SVC ou outro modelo leve
- [ ] Fixar seeds para reprodutibilidade
- [ ] Avaliar o modelo com métricas básicas, incluindo accuracy e F1-score por classe
- [ ] Salvar métricas em `docs/model_metrics.md`
- [ ] Serializar pipeline completo em `models/model.pkl`
- [ ] Validar carregamento do modelo em um script isolado
- [ ] Entregar `models/model.pkl`, instruções de carregamento e amostras de teste ao Integrante 2

## 1.3. DAG Airflow

- [ ] Subir ambiente local do Airflow antes de implementar a DAG
- [ ] Criar `dags/train_pipeline.py`
- [ ] Criar task de carregamento/validação do dataset
- [ ] Criar task de treino reutilizando a lógica de `src/train.py`
- [ ] Criar task de salvamento do modelo treinado
- [ ] Configurar ordem obrigatória: **carregamento de dados → treino → salvamento do modelo**
- [ ] Configurar a DAG para simular um fluxo de retreino
- [ ] Executar a DAG com sucesso no Airflow
- [ ] Salvar print da interface e logs da execução bem-sucedida
- [ ] Documentar no README como iniciar o Airflow e disparar a DAG

## 1.4. Handoff técnico

- [ ] Entregar modelo baseline ao Integrante 2 até 24/08
- [ ] Entregar amostras de benchmark ao Integrante 4 até 24/08
- [ ] Entregar evidências da DAG ao grupo até 31/08
- [ ] Informar compatibilidade preliminar do pipeline com ONNX ao Integrante 4
- [ ] Registrar plano alternativo caso ONNX não seja compatível com o modelo

### Entregáveis da Etapa 1

- [ ] Dataset documentado e validado
- [ ] `src/train.py`
- [ ] `models/model.pkl`
- [ ] `docs/model_metrics.md`
- [ ] `data/benchmark_samples.json`
- [ ] `dags/train_pipeline.py`
- [ ] Evidência de DAG executada com sucesso

---

# Etapa 2 — API FastAPI, Docker e Arquitetura

**Responsável:** Integrante 2**Janela principal:** 12/08 a 31/08**Objetivo:** transformar o modelo entregue pela Etapa 1 em um serviço REST containerizado e documentar a decisão arquitetural exigida.

> Esta pessoa pode começar a API antes de receber o modelo final, usando uma implementação mockada. A integração real acontece assim que `models/model.pkl` for entregue.

## 2.1. Fundação da API

- [ ] Criar `src/app.py` com FastAPI
- [ ] Definir contrato da API em `docs/api_contract.md`
- [ ] Criar request Pydantic com campo obrigatório `text`
- [ ] Criar response Pydantic com campo `prediction`
- [ ] Definir conjunto permitido de classes: `normal`, `atencao`, `urgente`
- [ ] Criar `GET /health`
- [ ] Criar `POST /predict`
- [ ] Implementar resposta mockada para destravar testes e CI/CD
- [ ] Validar API localmente com Uvicorn e `curl` ou Postman
- [ ] Comunicar contrato dos endpoints ao Integrante 3

## 2.2. Integração do modelo

- [ ] Receber `models/model.pkl` do Integrante 1
- [ ] Implementar carregamento do modelo ao iniciar a aplicação
- [ ] Garantir que o modelo não seja carregado a cada requisição
- [ ] Substituir predição mockada pela inferência do pipeline real
- [ ] Validar endpoint com textos conhecidos do dataset de teste
- [ ] Tratar erro de modelo ausente ou inválido com resposta controlada
- [ ] Revisar contrato de resposta após integração com o modelo

## 2.3. Dockerização

- [ ] Criar `Dockerfile` funcional para serviço de inferência
- [ ] Incluir código, dependências e artefato do modelo na imagem
- [ ] Expor a porta da API
- [ ] Configurar comando de inicialização com Uvicorn
- [ ] Fazer build da imagem localmente
- [ ] Subir o container e validar `GET /health`
- [ ] Validar `POST /predict` rodando exclusivamente dentro do container
- [ ] Criar instruções de build e execução no README
- [ ] Medir latência baseline da API em Docker
- [ ] Salvar baseline em `docs/baseline_latency.md`
- [ ] Entregar baseline e Dockerfile ao Integrante 4

## 2.4. Decisão arquitetural em nuvem

- [ ] Escrever seção de arquitetura no README
- [ ] Comparar processamento batch e real-time para triagem de laudos
- [ ] Escolher estratégia recomendada para o cenário hospitalar
- [ ] Selecionar AWS, Azure ou GCP como referência arquitetural
- [ ] Justificar a escolha com base em API de inferência, escalabilidade e contexto clínico
- [ ] Deixar explícito que o escopo exigido é a análise textual, não o provisionamento real em nuvem

### Entregáveis da Etapa 2

- [ ] `src/app.py`
- [ ] `GET /health`
- [ ] `POST /predict`
- [ ] `docs/api_contract.md`
- [ ] `Dockerfile`
- [ ] API com modelo real rodando em Docker
- [ ] `docs/baseline_latency.md`
- [ ] Decisão arquitetural documentada no README

---

# Etapa 3 — Testes, CI/CD e Observabilidade

**Responsável:** Integrante 3
**Janela principal:** 12/08 a 09/09
**Objetivo:** garantir qualidade automatizada e entregar a stack obrigatória com API, Prometheus e Grafana.

## 3.1. Testes automatizados

- [ ] Configurar `pytest`
- [ ] Criar teste para `GET /health`
- [ ] Criar teste para `POST /predict` com entrada válida
- [ ] Criar teste para payload inválido
- [ ] Criar mock ou fixture de modelo para os testes não dependerem do modelo final
- [ ] Configurar linter, como `ruff`
- [ ] Garantir execução local de lint e testes
- [ ] Rodar testes após a integração do modelo real

## 3.2. GitHub Actions

- [ ] Criar `.github/workflows/ci.yml`
- [ ] Configurar execução automática em `push`
- [ ] Configurar execução em `pull_request`, se o grupo trabalhar com PRs
- [ ] Criar job de lint
- [ ] Criar job de testes com `pytest`
- [ ] Criar job de build da imagem Docker
- [ ] Garantir no mínimo duas automações obrigatórias: lint e testes
- [ ] Validar workflow verde em push real
- [ ] Adicionar badge do GitHub Actions ao README
- [ ] Documentar comandos de teste e lint no README

## 3.3. Instrumentação com Prometheus

- [ ] Criar branch própria para alterações em `src/app.py`
- [ ] Adicionar contador de requisições recebidas
- [ ] Adicionar métrica de latência/tempo de resposta
- [ ] Adicionar contador de erros
- [ ] Expor endpoint `GET /metrics`
- [ ] Validar que métricas são atualizadas após requisições ao `/predict`
- [ ] Confirmar que `/metrics` responde no formato Prometheus
- [ ] Abrir pull request para integração das métricas

## 3.4. Stack Docker Compose

- [ ] Criar `monitoring/prometheus.yml`
- [ ] Configurar scrape da API pelo endpoint `/metrics`
- [ ] Criar `docker-compose.yml`
- [ ] Adicionar serviço da API
- [ ] Adicionar serviço do Prometheus
- [ ] Adicionar serviço do Grafana
- [ ] Configurar portas, rede e dependências entre serviços
- [ ] Subir a stack com `docker compose up --build`
- [ ] Confirmar API acessível
- [ ] Confirmar Prometheus acessível
- [ ] Confirmar que o target da API aparece como **UP** no Prometheus

## 3.5. Dashboard Grafana

- [ ] Configurar Prometheus como datasource do Grafana
- [ ] Criar painel de total de requisições
- [ ] Criar painel de latência/tempo de resposta
- [ ] Criar painel de taxa de erro
- [ ] Garantir o mínimo obrigatório de três painéis
- [ ] Criar `scripts/generate_load.py` para gerar tráfego no endpoint `/predict`
- [ ] Popular os gráficos com dados reais
- [ ] Exportar dashboard para `monitoring/dashboard.json`
- [ ] Salvar prints do dashboard em `docs/`
- [ ] Documentar acesso e execução da stack no README

### Entregáveis da Etapa 3

- [ ] Testes com `pytest`
- [ ] Lint configurado
- [ ] `.github/workflows/ci.yml`
- [ ] Workflow verde
- [ ] API instrumentada com `prometheus_client`
- [ ] `docker-compose.yml`
- [ ] `monitoring/prometheus.yml`
- [ ] Dashboard Grafana com 3 painéis
- [ ] `monitoring/dashboard.json`
- [ ] Prints com métricas reais

---

# Etapa 4 — Otimização e Benchmark de Latência

**Responsável:** Integrante 4
**Janela principal:** 17/08 a 10/09
**Objetivo:** aplicar uma técnica obrigatória de otimização, provar ganho de desempenho e deixar resultados reproduzíveis.

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
- [ ] Salvar artefato otimizado, como `models/model.onnx`
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
- [ ] Modelo otimizado
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

# Cronograma de checkpoints

| Data limite     | Resultado que precisa existir                                                     |
| --------------- | --------------------------------------------------------------------------------- |
| **16/08** | Dataset validado, API mockada, testes iniciais e benchmark estruturado            |
| **24/08** | Modelo baseline salvo, API integrada ou pronta para integrar, CI verde            |
| **31/08** | Docker funcional, baseline de latência, DAG Airflow executada                    |
| **06/09** | Métricas expostas, Prometheus coletando dados, técnica de otimização aplicada |
| **10/09** | Grafana com 3 painéis, benchmark final, README quase fechado                     |
| **12/09** | Vídeo ensaiado, solução executada do zero, evidências revisadas               |
| **15/09** | Entrega submetida                                                                 |

## Dependências críticas

- **Etapa 1 → Etapa 2:** o Integrante 2 pode criar a API com mock, mas precisa do `models/model.pkl` para fechar a inferência real.
- **Etapa 1 → Etapa 4:** a otimização depende do modelo baseline e das amostras de benchmark.
- **Etapa 2 → Etapa 3:** Prometheus e Grafana dependem da API e do container; testes e CI podem começar antes usando mock.
- **Etapa 3 → vídeo:** o dashboard precisa estar populado antes da gravação.
- **Etapa 4 → vídeo:** a comparação de latência precisa estar fechada antes da narrativa de resultado.
