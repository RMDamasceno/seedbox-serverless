# Changelog

Todas as mudanças notáveis do projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-04-22

### Added
- **Testes:** Fase 5 completa — Testes e Validação Final
  - Testes unitários: state_manager (9 testes), validators (15 testes), auth (7 testes), routes (11 testes), worker (11 testes)
  - 10 cenários de falha controlada: disco cheio, SIGTERM, S3 failure, magnet inválido, race condition, idempotência, stale index, cancel durante sync, Cloudflare-only, pre-signed URL
  - CloudWatch Alarms: Lambda errors, API latency P99, EC2 CPU
  - Documentação: failure-scenarios.md, iam-policies.md
  - conftest.py com fixtures moto (mock S3) e resolução de imports

## [0.5.0] - 2026-04-22

### Added
- **Frontend:** Fase 4 completa — Frontend React e Cloudflare
  - Scaffold: Vite + React 18 + TypeScript + TailwindCSS + React Router
  - Tipos: IDownload, IStatusResponse, ILoginResponse (espelham schemas backend)
  - API Service: fetch wrapper com JWT interceptor, redirect 401, todos os endpoints
  - Auth: AuthContext, LoginPage (senha única), ProtectedRoute
  - Dashboard: contadores por status, WorkerStatus, polling adaptativo (10s/60s)
  - DownloadList: filtros por status (tabs), DownloadCard, polling, ações rápidas
  - AddDownload: magnet link + upload .torrent (drag-and-drop, Pre-signed URL direto S3)
  - DownloadDetail: progresso, velocidades, ETA, edição de nome inline, ações contextuais
  - InfraStatus: status EC2, contadores de fila, staleness do índice
  - Layout: Navbar responsiva (desktop + mobile), dark mode
  - Deploy: script deploy-frontend.sh (build + s3 sync com cache headers)
  - Cloudflare: docs/infrastructure/cloudflare-setup.md (DNS, SSL, Cache, WAF)

## [0.4.0] - 2026-04-22

### Added
- **Worker/EC2:** Fase 3 completa — Worker EC2 e Integração
  - config/transmission.json: Configuração completa do Transmission daemon
  - config/rclone.conf: Configuração do rclone para S3
  - transmission_client.py: Cliente JSON-RPC com session ID handling e retry
  - utils.py: IMDSv2, logging estruturado, load_config com defaults
  - disk_manager.py: Verificação pré-download, monitoramento contínuo (2GB crítico, 5GB retoma)
  - s3_client.py: Lock atômico via ETag, update progress throttled, move_processing_to_pending
  - error_handler.py: Classificação (temporary/definitive/operational) + backoff (60s, 300s, 900s)
  - monitor.py: Loop 10s com detecção de cancelamento, conclusão e erro
  - sync.py: rclone move com INTELLIGENT_TIERING, 4 transfers, checksum
  - main.py: Loop principal, graceful shutdown (SIGTERM), Spot interruption handler
  - spot_handler.py: Detecção de Spot interruption via IMDSv2

## [0.3.0] - 2026-04-22

### Added
- **Backend/Lambda:** Fase 2 completa — Backend e Estado
  - state_manager.py: CRUD S3 + transição de estado atômica com ETag (COPY → VALIDATE → DELETE)
  - validators.py: Models Pydantic para validação de entrada (magnet, UUID, .torrent, limites)
  - auth.py: Login com bcrypt + geração/verificação JWT (HS256, 24h TTL, cache de secret)
  - authorizer/handler.py: Lambda Authorizer com simple response (isAuthorized)
  - routes.py: Todas as rotas — create (idempotente), list, get, update, delete, cancel, requeue, upload-url, download-url, status
  - worker-trigger/handler.py: Liga/desliga EC2 com tratamento de estado stopping
  - handler.py: Router por método+path (API Gateway HTTP API format 2.0)
  - exceptions.py: BadRequest, NotFound, Conflict, Unauthorized
  - response.py: Helpers para HTTP responses com CORS

## [0.2.0] - 2026-04-22

### Added
- **IaC/Terraform:** Fase 1 completa — Infraestrutura Base
  - Módulo S3: bucket dados (lifecycle, SSE, Intelligent-Tiering) + bucket frontend (website hosting, Cloudflare IPs)
  - Módulo IAM: 4 roles least privilege + Instance Profile + 2 Secrets Manager
  - Módulo EC2: Security Group (sem inbound) + Launch Template (t3.medium Spot, gp3 200GB, IMDSv2)
  - Módulo Lambda: 3 funções placeholder (api, authorizer, worker-trigger)
  - API Gateway HTTP API: 11 rotas, CORS, Lambda Authorizer JWT, throttle
  - Documentação: docs/infrastructure/resources.md

## [0.1.0] - 2026-04-22

### Added
- **Projeto:** Inicialização do repositório com estrutura de diretórios
  - Estrutura completa conforme documento técnico v1.5
  - README.md, LICENSE (MIT), .gitignore, pyproject.toml, requirements.txt
  - Diretórios: backend/, frontend/, iac/, tests/, docs/, memory-bank/, scripts/
  - Memory Bank inicializado com PROJECT_CONTEXT.md e DECISION_LOG.md
