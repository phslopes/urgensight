# ADR-0002 — Estratégia de nuvem e modo de serviço

- **Status:** Aceito
- **Data:** 2026-09-01
- **Contexto da decisão:** Etapa 2 (Deploy/API) — registrado retroativamente

## Contexto

A rubrica do Tech Challenge pede uma fundamentação teórica de implantação da API
UrgenSight em produção na nuvem, para o contexto de triagem de laudos hospitalares.
Duas decisões de arquitetura precisam ser tomadas antes de desenhar a infraestrutura:
(1) o **padrão de processamento** — laudos são classificados em lote (batch) ou à
medida que chegam (real-time síncrono)? — e (2) o **provedor de nuvem** de
referência para o desenho lógico.

A natureza clínica do problema é o critério dominante: um laudo classificado como
`urgente` demanda ação humana em minutos, não em horas. Qualquer atraso estrutural
entre a geração do laudo e a sinalização ao médico plantonista é um risco direto ao
paciente, não apenas uma questão de UX.

## Decisão

**Modo de serviço: real-time (síncrono via HTTP).** Para triagem hospitalar, o
requisito não-funcional dominante é o tempo de detecção do caso urgente. A latência
alvo de < 200 ms (p99) é facilmente atingida pelo pipeline TF-IDF + regressão
logística (CPU-bound, sem I/O intensivo), tornando o modelo real-time tecnicamente
viável e clinicamente necessário. Batch é aceito apenas como camada secundária —
por exemplo, um job noturno de reconciliação que processa laudos do dia para fins
de BI e auditoria de qualidade do modelo, sem impacto no fluxo clínico primário.

**Provedor de referência: AWS.** Selecionada pela maturidade do ecossistema de
contêineres, presença de regiões no Brasil (`sa-east-1`, reduzindo latência com
hospitais brasileiros) e alinhamento com padrões de conformidade em saúde (HIPAA,
ISO 27001, e equivalentes brasileiros como a LGPD).

**Desenho lógico:** Hospital (HTTPS) → ALB/NLB (terminação TLS) → ECS Fargate
(`urgensight-api`, 2–10 tasks, auto scaling por CPU/memória) → imagens versionadas
no ECR. Observabilidade via CloudWatch, segredos via Secrets Manager, rede em VPC
privada com subnets em duas AZs e NAT Gateway. Multi-AZ e o healthcheck já exposto
em `/health` do Dockerfile sustentam a alta disponibilidade; TLS 1.3 obrigatório no
ALB e desativação do log do corpo da requisição no CloudWatch endereçam a
governança de dados clínicos sob a LGPD. O CI/CD sugerido é: push para `main` →
GitHub Actions → testes + análise de segurança → `docker build` → push para ECR com
tag do commit → `ecs update-service` com rolling deployment, com rollback
automático via alarme de erros 5xx > 1% em 5 minutos.

**Disclaimer de escopo (preservado do README):** o escopo deste projeto (Tech
Challenge — FIAP MLET) foi focado na engenharia da análise textual e na construção
da API local containerizada. A infraestrutura em nuvem descrita é uma fundamentação
teórica de arquitetura e **não contempla o provisionamento real**, configuração de
redes, custos ou conformidade com órgãos reguladores (ANVISA, CFM). Qualquer
implantação em ambiente hospitalar real exigiria avaliação jurídica, testes de
penetração e validação clínica do modelo.

## Alternativas consideradas

**Processamento batch.** Rejeitada como modo primário: um pipeline batch
introduziria um intervalo de espera inaceitável entre a geração do laudo e a
sinalização ao médico plantonista — um caso `urgente` esperaria o próximo ciclo do
lote em vez de gerar alerta imediato. É inadequada ao contexto clínico apesar de
ter menor complexidade operacional e menor custo computacional (recursos sob
demanda em vez de instâncias sempre provisionadas). Mantida apenas como camada
secundária para BI e auditoria, fora do caminho crítico de decisão clínica.

**Azure como provedor de referência.** Rejeitada: a AWS foi preferida pela
combinação específica de presença de região `sa-east-1` (relevante para latência
com hospitais brasileiros), maturidade do ecossistema de contêineres (ECS/Fargate,
ECR) já mapeada no desenho lógico, e alinhamento direto com os padrões de
conformidade em saúde citados (HIPAA, ISO 27001, LGPD). Azure é um provedor viável
e com oferta equivalente de contêineres gerenciados e regiões compatíveis, mas não
foi o escolhido como referência teórica deste projeto.

**GCP como provedor de referência.** Rejeitada pelo mesmo critério: sem uma região
nativa na América do Sul equivalente à `sa-east-1` da AWS no momento da decisão, e
sem motivar uma vantagem específica sobre o desenho ECS Fargate + ALB já adotado
como referência. Permanece como alternativa tecnicamente válida, não descartada por
limitação técnica, apenas não escolhida como o desenho de referência documentado.

## Consequências

- O desenho lógico documentado (ECS Fargate + ALB + ECR + CloudWatch + Secrets
  Manager, em `sa-east-1`) é uma referência teórica, não uma infraestrutura
  provisionada; nenhum destes serviços existe de fato para este projeto.
- Decisões futuras de infraestrutura real (Terraform/CDK, contas AWS, custos) devem
  partir deste ADR como ponto de referência, mas exigem validação própria antes de
  qualquer provisionamento.
- A escolha por real-time síncrono reforça, do lado da aplicação, o requisito de
  latência baixa (p99 < 50 ms dentro da task, segundo o desenho) que já orienta as
  decisões de instrumentação da Etapa 3 (ver ADR-0004).
- Qualquer decisão futura de mover parte do fluxo para batch (ex.: reprocessamento
  noturno) deve ser tratada como complementar, nunca substituta, ao caminho
  síncrono de detecção de urgência.
