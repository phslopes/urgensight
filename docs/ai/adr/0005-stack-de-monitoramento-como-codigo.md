# ADR-0005 — Stack de monitoramento como código

- **Status:** Aceito
- **Data:** 2026-09-01
- **Contexto da decisão:** Etapa 3 (Observabilidade)

## Contexto

A Etapa 3 exige que um avaliador consiga clonar o repositório, subir a stack
completa (API + Prometheus + Grafana) com um comando, e ver um dashboard já
populado — sem passos manuais de configuração na UI do Grafana ou conhecimento
prévio da ordem de comandos do projeto. Ao mesmo tempo, o `docker-compose.yml` da
raiz já era usado, desde a Etapa 1.3, para subir a stack do Airflow, o que gera uma
colisão de responsabilidade: um único arquivo `docker-compose.yml` na raiz não pode
descrever duas stacks logicamente separadas (treino/orquestração vs.
API+observabilidade) sem ambiguidade sobre qual delas é "a" stack padrão do
projeto.

## Decisão

O `docker-compose.yml` da **raiz** passa a definir a stack de observabilidade —
`api`, `prometheus` e `grafana` — e a stack do Airflow **migra** para
`docker-compose.airflow.yml`. O avaliador que abre o repositório e roda
`docker compose up` encontra exatamente o que a rubrica da Etapa 3 descreve.

Detalhes de configuração:

- **Portas:** API em `8000`, Prometheus em `9090`, Grafana em `3000`.
- **Volumes:** volume nomeado (`prometheus-data`) para o TSDB do Prometheus,
  preservando a série temporal entre restarts durante a gravação do vídeo de
  demonstração. O Grafana não tem volume — tudo nele é provisionado por arquivo.
- **Grafana:** acesso anônimo habilitado com papel `Viewer` (o avaliador abre
  `localhost:3000` e já vê o dashboard, sem login); `admin/admin` continua
  disponível para edição.
- **Prometheus:** `scrape_interval: 15s`, com o target `api:8000` resolvido pela
  rede interna do Compose.
- **Dashboard provisionado por arquivo**, com UID de datasource fixo
  (`urgensight-prometheus`, em `monitoring/grafana/provisioning/datasources`) — sem
  um UID fixo, um JSON exportado da UI do Grafana referencia um UID gerado
  aleatoriamente e não reimporta corretamente em outra máquina. O JSON do dashboard
  é mantido em `monitoring/dashboard.json`, servindo simultaneamente como fonte do
  provisionamento automático e como o entregável "JSON do dashboard" exigido pela
  rubrica.
- `make dev` sobe a stack de monitoramento e **garante o pré-requisito**: se
  `models/model.pkl` não existir, executa `make train` antes de subir os
  containers. O Airflow ganha um target próprio (`make dev-airflow` ou
  equivalente), removendo a fricção de o avaliador precisar saber a ordem correta
  dos comandos.

## Alternativas consideradas

**Mover o Compose de monitoramento para `monitoring/docker-compose.yml`, deixando
a raiz para o Airflow.** Rejeitada: preservaria a posição histórica do Airflow, mas
inverteria a expectativa do avaliador na Etapa 3 — a rubrica descreve `docker
compose up` na raiz subindo API+Prometheus+Grafana, não a stack de treino. Deixar o
Airflow na raiz forçaria o avaliador a descobrir um segundo arquivo em um
subdiretório para ver exatamente o que está sendo avaliado nesta etapa.

**Um único Compose com profiles** (ex.: `--profile airflow` vs. `--profile
monitoring` no mesmo `docker-compose.yml`). Rejeitada: os dois grupos de serviços
têm ciclos de vida e propósitos distintos (orquestração de treino periódico vs.
serviço de inferência observado), e um arquivo único com profiles aumentaria o
acoplamento de configuração entre as duas stacks (rede, volumes, variáveis de
ambiente) sem benefício real — o avaliador ainda precisaria saber qual profile
ativar. Dois arquivos nomeados explicitamente (`docker-compose.yml` e
`docker-compose.airflow.yml`) comunicam a separação sem exigir memorizar uma flag.

**Montar o dashboard manualmente na UI do Grafana e exportar o JSON depois.**
Rejeitada: um dashboard editado manualmente na UI recebe um UID de datasource
gerado no momento da criação, específico àquela instância do Grafana. O JSON
exportado desse processo não reimporta corretamente em uma instância diferente
(como a do avaliador) sem edição manual do UID, quebrando exatamente o cenário de
"clonar e rodar" que esta decisão pretende garantir. Provisionar por arquivo com UID
fixo desde o início elimina essa dependência de passo manual.

## Consequências

- `docker compose up` na raiz é, a partir de agora, o comando canônico para a stack
  de observabilidade da Etapa 3; qualquer documentação ou script que assumia que a
  raiz continha o Airflow precisa ser atualizado para apontar para
  `docker-compose.airflow.yml`.
- O dashboard do Grafana está sob controle de versão (`monitoring/dashboard.json`)
  como o restante da infraestrutura — mudanças nos painéis passam por revisão de
  código, não por edição direta na UI de produção.
- O acesso anônimo em modo `Viewer` do Grafana é adequado para o ambiente de
  demonstração/avaliação local deste projeto, mas **não deve ser replicado** em um
  ambiente real sem revisão de segurança — é uma conveniência de avaliação, não uma
  postura de produção.
- `make dev` acoplar o treino automático (`make train`) à subida da stack significa
  que a primeira execução em uma máquina nova é mais lenta (treina antes de subir os
  containers); execuções subsequentes reutilizam `models/model.pkl` já existente.
