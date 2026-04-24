# Roadmap de Desenvolvimento — Seedbox Serverless AWS v1.5

**Versão:** 1.0
**Data:** Abril de 2026
**Objetivo:** Guia passo-a-passo granular para desenvolvimento assistido por IA. Cada step é atômico, testável e independente.

---

## Índice de Fases

| Fase | Nome | Steps | Dependência |
|------|------|-------|-------------|
| 1 | Infraestrutura Base (IaC) | 1.1 → 1.10 | Nenhuma |
| 2 | Backend e Estado (Lambda + S3) | 2.1 → 2.12 | Fase 1 |
| 3 | Worker EC2 e Integração | 3.1 → 3.10 | Fase 2 |
| 4 | Frontend e Cloudflare | 4.1 → 4.12 | Fase 2 |
| 5 | Testes e Validação Final | 5.1 → 5.6 | Fases 3 e 4 |

## Convenções

- **Cada step** produz código funcional e commitável
- **Critério de aceite** define quando o step está completo
- **Arquivos envolvidos** lista exatamente o que será criado/modificado
- **Referência** aponta para a seção do documento técnico v1.5
- Marcar com ✅ ao concluir, 🔲 quando pendente, 🔄 quando em progresso

---

## Fase 1 — Infraestrutura Base (IaC)

> Provisionar todos os recursos AWS via Terraform. Nenhum código de aplicação nesta fase.
> **Referência:** Seções 5.4, 12.3, 14 e 15 do documento técnico v1.5

### Step 1.1 — Terraform: Estrutura base e provider ✅

**Objetivo:** Configurar o projeto Terraform com provider AWS, backend remoto (S3) e variáveis globais.

**Arquivos:**
- `iac/terraform/main.tf` — Provider AWS, versão, backend
- `iac/terraform/variables.tf` — Variáveis globais (region, account_id, project_name, environment)
- `iac/terraform/outputs.tf` — Outputs raiz
- `iac/terraform/versions.tf` — Versões de providers
- `iac/terraform/environments/dev/terraform.tfvars` — Valores para dev

**Critério de aceite:**
- `terraform init` executa sem erros
- `terraform validate` passa
- `terraform plan` mostra 0 recursos (ainda sem módulos)

---

### Step 1.2 — Módulo S3: Bucket principal (dados) ✅

**Objetivo:** Criar o bucket `seedbox-{account-id}` com Block Public Access, lifecycle rules e Intelligent-Tiering.

**Arquivos:**
- `iac/terraform/modules/s3/main.tf` — Recurso aws_s3_bucket + configurações
- `iac/terraform/modules/s3/variables.tf` — Inputs do módulo
- `iac/terraform/modules/s3/outputs.tf` — bucket_name, bucket_arn
- `iac/terraform/main.tf` — Adicionar chamada ao módulo s3

**Configurações obrigatórias:**
- Block Public Access: habilitado em todas as 4 opções
- Versionamento: desabilitado
- Lifecycle rules: `idempotency/` expira 1 dia, `torrents/` expira 7 dias
- Server-side encryption: SSE-S3
- Intelligent-Tiering para prefixo `downloads/completed/`

**Critério de aceite:**
- `terraform plan` mostra criação do bucket com todas as lifecycle rules
- Nenhum acesso público configurado

**Referência:** Seção 5.4 (Bucket S3)

---

### Step 1.3 — Módulo S3: Bucket frontend (website hosting) ✅

**Objetivo:** Criar o bucket `seedbox-frontend-{account-id}` com website hosting e bucket policy restrita a IPs Cloudflare.

**Arquivos:**
- `iac/terraform/modules/s3/frontend.tf` — Bucket frontend separado
- `iac/terraform/modules/s3/cloudflare_ips.tf` — Data source ou variável com lista de IPs CF

**Configurações obrigatórias:**
- Website hosting: index_document = `index.html`, error_document = `index.html` (SPA)
- Bucket Policy: permite `s3:GetObject` apenas dos IPs Cloudflare (lista completa da seção 5.1)
- Block Public Access: desabilitado apenas para `BlockPublicPolicy` (necessário para bucket policy pública)

**Critério de aceite:**
- `terraform plan` mostra bucket com website hosting configurado
- Bucket policy contém todos os CIDRs IPv4 e IPv6 da Cloudflare

**Referência:** Seção 5.1 (Frontend S3 + Cloudflare)

---

### Step 1.4 — Módulo IAM: Roles e Policies ✅

**Objetivo:** Criar IAM Roles com least privilege para Lambda API, Lambda Authorizer, Lambda Worker Trigger e EC2 Worker.

**Arquivos:**
- `iac/terraform/modules/iam/main.tf` — Roles e policies
- `iac/terraform/modules/iam/variables.tf` — Inputs (bucket_arn, secret_arns)
- `iac/terraform/modules/iam/outputs.tf` — Role ARNs e instance profile
- `iac/terraform/main.tf` — Adicionar chamada ao módulo iam

**Roles a criar:**
1. `seedbox-api-lambda-role` — S3 (queue/, idempotency/, torrents/), Secrets Manager, EC2 describe/start, logs
2. `seedbox-authorizer-lambda-role` — Secrets Manager (seedbox/auth), logs
3. `seedbox-worker-trigger-lambda-role` — EC2 start/describe, logs
4. `seedbox-worker-ec2-role` — S3 (queue/, downloads/, torrents/), EC2 stop (self), Secrets Manager, logs
5. Instance Profile para EC2

**Critério de aceite:**
- `terraform plan` mostra 4 roles com policies inline
- Nenhuma policy usa `*` em Resource (exceto ec2:StopInstances com condition tag)
- Cada role tem apenas as permissões listadas na seção 12.3

**Referência:** Seções 12.3 e 16 (IAM Policies)

---

### Step 1.5 — Módulo IAM: Secrets Manager ✅

**Objetivo:** Criar os secrets `seedbox/auth` e `seedbox/transmission` no Secrets Manager.

**Arquivos:**
- `iac/terraform/modules/iam/secrets.tf` — Recursos aws_secretsmanager_secret
- `iac/terraform/modules/iam/variables.tf` — Adicionar variáveis de secret

**Secrets:**
- `seedbox/auth` — Placeholder para `{ "passwordHash": "", "jwtSecret": "" }`
- `seedbox/transmission` — Placeholder para `{ "username": "seedbox", "password": "" }`

**Nota:** Os valores reais serão preenchidos manualmente ou via script de setup. O Terraform cria apenas o recurso com valor placeholder.

**Critério de aceite:**
- `terraform plan` mostra criação de 2 secrets
- Valores placeholder, sem credenciais reais no código

**Referência:** Seção 12.2 (Segredos no Secrets Manager)

---

### Step 1.6 — Módulo EC2: Security Group ✅

**Objetivo:** Criar o Security Group `seedbox-worker-sg` com regras mínimas.

**Arquivos:**
- `iac/terraform/modules/ec2/main.tf` — Security Group
- `iac/terraform/modules/ec2/variables.tf` — Inputs (vpc_id)
- `iac/terraform/modules/ec2/outputs.tf` — sg_id
- `iac/terraform/main.tf` — Adicionar chamada ao módulo ec2

**Regras:**
- Inbound: nenhuma regra (worker não recebe conexões externas)
- Outbound: 443 (HTTPS para S3/AWS APIs), 6881-6889 TCP/UDP (BitTorrent), 53 UDP (DNS)

**Critério de aceite:**
- `terraform plan` mostra SG sem regras inbound
- Outbound limitado às portas especificadas

**Referência:** Seção 14 (SeedboxWorkerSG)

---

### Step 1.7 — Módulo EC2: Launch Template ✅

**Objetivo:** Criar o Launch Template para EC2 Spot `t3.medium` com User Data, IAM Role e SG.

**Arquivos:**
- `iac/terraform/modules/ec2/launch_template.tf` — aws_launch_template
- `iac/terraform/modules/ec2/user_data.sh` — Script de inicialização (shell)
- `iac/terraform/modules/ec2/variables.tf` — Adicionar variáveis (instance_type, ami, disk_size)

**Configurações:**
- Instance type: `t3.medium`
- AMI: Amazon Linux 2023 (data source `aws_ami`)
- Disco: 200 GB gp3 (3000 IOPS, 125 MB/s)
- Spot: `instance_market_options` com `spot_options`
- IAM Instance Profile: role do worker
- Security Group: `seedbox-worker-sg`
- User Data: instalar transmission-daemon, python3.12, boto3, rclone
- Tags: `Name = seedbox-worker`
- Metadata: IMDSv2 obrigatório

**Critério de aceite:**
- `terraform plan` mostra launch template com todas as configurações
- User Data instala dependências corretas
- IMDSv2 habilitado (http_tokens = required)

**Referência:** Seções 5.3 e 14 (Worker EC2 Spot, Launch Template)

---

### Step 1.8 — Módulo Lambda: Funções base (placeholder) ✅

**Objetivo:** Criar os 3 recursos Lambda com código placeholder (handler vazio que retorna 200).

**Arquivos:**
- `iac/terraform/modules/lambda/main.tf` — 3 aws_lambda_function
- `iac/terraform/modules/lambda/variables.tf` — Inputs (role_arns, s3_bucket, env vars)
- `iac/terraform/modules/lambda/outputs.tf` — function_arns, invoke_arns
- `backend/lambda/api/handler.py` — Placeholder `def handler(event, context): return {"statusCode": 200}`
- `backend/lambda/authorizer/handler.py` — Placeholder
- `backend/lambda/worker-trigger/handler.py` — Placeholder
- `iac/terraform/main.tf` — Adicionar chamada ao módulo lambda

**Configurações por função:**
| Função | Memória | Timeout | Runtime |
|--------|---------|---------|---------|
| seedbox-api | 256 MB | 30s | python3.12 |
| seedbox-authorizer | 128 MB | 5s | python3.12 |
| seedbox-worker-trigger | 128 MB | 10s | python3.12 |

**Variáveis de ambiente:** S3_BUCKET, EC2_INSTANCE_ID, AUTH_SECRET_NAME, ALLOWED_ORIGIN

**Critério de aceite:**
- `terraform plan` mostra 3 Lambda functions
- Cada função tem role, memória, timeout e env vars corretos
- Código placeholder retorna 200

**Referência:** Seções 5.2 e 15 (Lambda Functions, Variáveis de Ambiente)

---

### Step 1.9 — Módulo Lambda: API Gateway HTTP API ✅

**Objetivo:** Criar o API Gateway HTTP API com rotas, authorizer e CORS.

**Arquivos:**
- `iac/terraform/modules/lambda/api_gateway.tf` — HTTP API, stages, routes, integrations
- `iac/terraform/modules/lambda/variables.tf` — Adicionar variáveis (allowed_origin, domain)

**Configurações:**
- Tipo: HTTP API (não REST API)
- Stage: `$default` com auto-deploy
- Authorizer: Lambda authorizer apontando para `seedbox-authorizer`
- Throttle: 100 req/s burst, 50 req/s rate
- CORS: Allow-Origin restrito ao domínio Cloudflare, Allow-Methods, Allow-Headers

**Rotas:**
| Método | Rota | Lambda | Auth |
|--------|------|--------|------|
| POST | /auth/login | seedbox-api | Nenhuma |
| GET | /downloads | seedbox-api | JWT |
| POST | /downloads | seedbox-api | JWT |
| GET | /downloads/{id} | seedbox-api | JWT |
| PATCH | /downloads/{id} | seedbox-api | JWT |
| DELETE | /downloads/{id} | seedbox-api | JWT |
| POST | /downloads/{id}/cancel | seedbox-api | JWT |
| POST | /downloads/{id}/requeue | seedbox-api | JWT |
| POST | /downloads/{id}/download-url | seedbox-api | JWT |
| POST | /downloads/upload-url | seedbox-api | JWT |
| GET | /status | seedbox-api | JWT |

**Critério de aceite:**
- `terraform plan` mostra API Gateway com todas as 11 rotas
- CORS configurado corretamente
- Authorizer vinculado a todas as rotas exceto `/auth/login`

**Referência:** Seções 6.1-6.5 e 12.3 (Contratos de API, Segurança)

---

### Step 1.10 — Validação completa da Fase 1 ✅

**Objetivo:** Validar toda a infraestrutura com `terraform plan` e documentar.

**Ações:**
1. Executar `terraform fmt -recursive` em todo o diretório `iac/`
2. Executar `terraform validate`
3. Executar `terraform plan` e revisar todos os recursos
4. Atualizar `docs/infrastructure/resources.md` com lista de recursos criados
5. Atualizar `docs/CHANGELOG.md` com entrada da Fase 1
6. Atualizar `memory-bank/PROJECT_CONTEXT.md` — Fase 1 = ✅

**Critério de aceite:**
- `terraform validate` passa sem erros
- `terraform plan` mostra todos os recursos esperados sem erros
- Documentação atualizada

---

## Fase 2 — Backend e Estado (Lambda + S3)

> Implementar toda a lógica de backend: state manager, API routes, autenticação JWT e validação.
> **Referência:** Seções 6, 7, 11, 12 e 13 do documento técnico v1.5

### Step 2.1 — State Manager: Módulo base S3 ✅

**Objetivo:** Implementar o módulo `state_manager.py` com operações CRUD básicas no S3 (get, put, delete, list).

**Arquivos:**
- `backend/lambda/api/state_manager.py` — Classe StateManager com get_item, put_item, delete_item, list_items
- `backend/lambda/api/__init__.py` — Exports

**Funções:**
- `get_item(item_id, status)` — GET objeto JSON do S3 com ETag
- `put_item(item, status)` — PUT objeto JSON no S3
- `delete_item(item_id, status)` — DELETE objeto do S3
- `list_items(status)` — LIST objetos por prefixo
- `get_index()` — GET index.json
- `update_index(item)` — Atualizar index.json

**Critério de aceite:**
- Todas as funções têm docstrings (RULE 2)
- Tratamento de erros específico para ClientError (RULE 3)
- Logging estruturado com contexto (item_id, status, operação)

**Referência:** Seção 3 (Estrutura de Dados no S3)

---

### Step 2.2 — State Manager: Transição de estado com ETag ✅

**Objetivo:** Implementar `transition_state()` com protocolo COPY → VALIDATE → DELETE e ETag condicional.

**Arquivos:**
- `backend/lambda/api/state_manager.py` — Adicionar transition_state()

**Lógica:**
1. GET item com ETag
2. VALIDATE: verificar workerId e status atual
3. Preparar novo estado (atualizar campos, incrementar version)
4. COPY condicional com CopySourceIfMatch
5. PUT com JSON atualizado
6. DELETE fonte
7. Atualizar index.json

**Critério de aceite:**
- Retorna None se ETag mismatch (PreconditionFailed)
- Raise LockConflictError se workerId não corresponde
- Raise StateMismatchError se status não corresponde
- Incrementa version a cada transição

**Referência:** Seção 7 (Protocolo de Consistência do S3)

---

### Step 2.3 — Validators: Validação de entrada ✅

**Objetivo:** Implementar validadores Pydantic para todos os requests da API.

**Arquivos:**
- `backend/lambda/api/validators.py` — Models Pydantic

**Models:**
- `CreateDownloadRequest` — clientRequestId (UUID), type (magnet|torrent_file), magnetLink, torrentS3Key, name
- `UpdateDownloadRequest` — name (max 255 chars)
- `UploadUrlRequest` — filename (.torrent), sizeBytes (max 1MB)
- `DownloadUrlRequest` — expiresIn (max 604800)
- `LoginRequest` — password (string)

**Validações específicas:**
- magnetLink deve começar com `magnet:?`
- clientRequestId deve ser UUID v4 válido
- filename deve terminar com `.torrent`
- sizeBytes máximo: 1048576 (1 MB)

**Critério de aceite:**
- Todos os models com validadores customizados
- Mensagens de erro claras e específicas
- Rejeita inputs inválidos com ValueError

**Referência:** Seção 6 (Contratos de API), RULE 17

---

### Step 2.4 — Auth: Login e JWT ✅

**Objetivo:** Implementar endpoint de login e geração de JWT.

**Arquivos:**
- `backend/lambda/api/auth.py` — Funções login() e verify_token()

**Lógica:**
- `login(password)` — Busca secret `seedbox/auth` no Secrets Manager, valida com bcrypt, gera JWT (HS256, 24h TTL)
- `verify_token(token)` — Decodifica e valida JWT (exp, sub, jti)
- Cache do secret em memória (reutilizado entre invocações Lambda)

**Critério de aceite:**
- JWT contém claims: sub, iat, exp, jti
- Retorna 401 para senha inválida
- Retorna 401 para token expirado ou inválido
- Secret buscado do Secrets Manager (nunca hardcoded)

**Referência:** Seção 12.1 (JWT)

---

### Step 2.5 — Auth: Lambda Authorizer ✅

**Objetivo:** Implementar o Lambda Authorizer que valida JWT e retorna IAM policy.

**Arquivos:**
- `backend/lambda/authorizer/handler.py` — Handler do authorizer

**Lógica:**
- Extrair token do header Authorization (Bearer)
- Validar JWT via verify_token()
- Retornar IAM policy Allow/Deny
- Cache de resultado por 300s (configurado no API Gateway)

**Critério de aceite:**
- Retorna Allow policy para token válido
- Retorna Deny policy para token inválido/expirado/ausente
- Logging de tentativas de autenticação (sem logar o token)

**Referência:** Seção 5.2 (Lambda Authorizer)

---

### Step 2.6 — API Routes: POST /downloads (criar download) ✅

**Objetivo:** Implementar criação de download com idempotência.

**Arquivos:**
- `backend/lambda/api/routes.py` — Função create_download()
- `backend/lambda/api/handler.py` — Router que despacha para routes

**Lógica:**
1. Validar request com CreateDownloadRequest
2. Verificar idempotência: checar `idempotency/{clientRequestId}`
3. Se existe, retornar item existente (200)
4. Se não existe, criar item em `queue/pending/{id}.json` (201)
5. Registrar chave de idempotência
6. Chamar trigger_worker_if_stopped()
7. Atualizar index.json

**Critério de aceite:**
- Idempotência funciona (mesma requisição 2x retorna mesmo item)
- Valida magnet link ou torrentS3Key conforme type
- Retorna 400 para input inválido
- Gera UUID v4 para id do download

**Referência:** Seções 6.2 e 11 (Downloads CRUD, Idempotência)

---

### Step 2.7 — API Routes: GET /downloads e GET /downloads/{id} ✅

**Objetivo:** Implementar listagem e detalhes de downloads.

**Arquivos:**
- `backend/lambda/api/routes.py` — Funções list_downloads() e get_download()

**Lógica:**
- `list_downloads(status, page, limit)` — Ler index.json, filtrar por status, paginar
- `get_download(id)` — Buscar item em todos os prefixos (pending, processing, completed, cancelled)

**Critério de aceite:**
- Listagem suporta filtro por status
- Paginação funciona (page, limit, total)
- GET por id retorna 404 se não encontrado
- Fallback para LIST direto se index.json não encontrado

**Referência:** Seção 6.2 (GET /downloads)

---

### Step 2.8 — API Routes: PATCH, DELETE, cancel, requeue ✅

**Objetivo:** Implementar operações de edição, remoção, cancelamento e requeue.

**Arquivos:**
- `backend/lambda/api/routes.py` — Funções update_download, delete_download, cancel_download, requeue_download

**Lógica:**
- `PATCH /downloads/{id}` — Editar nome (único campo editável em qualquer status)
- `DELETE /downloads/{id}` — Remover JSON + arquivo S3 se completed
- `POST /downloads/{id}/cancel` — Se pending: mover para cancelled. Se processing: setar cancelRequested=true
- `POST /downloads/{id}/requeue` — Apenas de cancelled: mover para pending, resetar retryCount e errorMessage

**Critério de aceite:**
- Respeita tabela de transições permitidas (seção 4.2)
- DELETE remove arquivo em `downloads/completed/{id}/` se status=completed
- Cancel em processing seta flag sem mover (worker detecta)
- Requeue reseta campos de erro e liga EC2 se necessário

**Referência:** Seções 4.2, 4.3 e 6.2 (Transições, CRUD por Estado)

---

### Step 2.9 — API Routes: Pre-signed URLs (upload e download) ✅

**Objetivo:** Implementar geração de Pre-signed URLs para upload de .torrent e download de arquivos.

**Arquivos:**
- `backend/lambda/api/routes.py` — Funções generate_upload_url() e generate_download_url()

**Lógica:**
- `POST /downloads/upload-url` — Gerar Pre-signed PUT URL para `torrents/{uuid}.torrent` (TTL: 5min, max 1MB)
- `POST /downloads/{id}/download-url` — Gerar Pre-signed GET URL para arquivo concluído (TTL configurável, max 7 dias)
- Incluir estimatedTransferCostUSD no response de download

**Critério de aceite:**
- Upload URL aceita apenas .torrent, max 1MB
- Download URL só funciona para status=completed (400 caso contrário)
- expiresIn limitado a 604800 segundos
- Custo estimado calculado: (sizeBytes / 1e9) * 0.09

**Referência:** Seções 6.3, 6.4 e 13 (Upload, Download, Pre-signed URLs)

---

### Step 2.10 — API Routes: GET /status ✅

**Objetivo:** Implementar endpoint de status da infraestrutura e fila.

**Arquivos:**
- `backend/lambda/api/routes.py` — Função get_status()

**Lógica:**
- Consultar EC2 DescribeInstances para status do worker (running/stopped/starting/stopping)
- Contar itens por status no index.json
- Calcular uptime se worker running
- Verificar staleness do index.json (updatedAt > 2min = isStale)

**Critério de aceite:**
- Retorna status do worker, contadores de fila e staleness do index
- Funciona mesmo se EC2 não existe (retorna stopped)
- Funciona mesmo se index.json não existe (retorna contadores zerados)

**Referência:** Seção 6.5 (Status da Infraestrutura)

---

### Step 2.11 — Worker Trigger Lambda ✅

**Objetivo:** Implementar a Lambda que liga/desliga a EC2 Spot.

**Arquivos:**
- `backend/lambda/worker-trigger/handler.py` — Handler com start_worker() e stop_worker()

**Lógica:**
- `start_worker()` — DescribeInstances para verificar estado. Se stopped, StartInstances. Se stopping, aguardar 30s e tentar novamente.
- `stop_worker()` — StopInstances (usado apenas para manutenção manual)
- Invocada assincronamente pela Lambda API (InvocationType=Event)

**Critério de aceite:**
- Não tenta ligar se já running ou starting
- Trata estado stopping com retry após 30s
- Logging de todas as transições de estado da EC2

**Referência:** Seção 5.2 (seedbox-worker-trigger)

---

### Step 2.12 — Handler principal e Router ✅

**Objetivo:** Implementar o handler principal da Lambda API com roteamento por método+path.

**Arquivos:**
- `backend/lambda/api/handler.py` — Handler principal com router
- `backend/lambda/api/exceptions.py` — Exceções customizadas (BadRequest, NotFound, Conflict, Unauthorized)
- `backend/lambda/api/response.py` — Helper para formatar responses HTTP

**Lógica:**
- Extrair method e path do event (API Gateway HTTP API format 2.0)
- Despachar para função correta em routes.py
- Tratar exceções e retornar HTTP response formatado
- Logging de request/response (sem body sensível)

**Critério de aceite:**
- Todas as 11 rotas mapeadas corretamente
- Exceções retornam status code correto (400, 401, 404, 409)
- Response sempre em JSON com Content-Type application/json
- POST /auth/login não passa pelo authorizer

**Referência:** Seção 6 (Contratos de API)

---

## Fase 3 — Worker EC2 e Integração

> Implementar o worker Python que roda na EC2: polling S3, controle do Transmission, sync para S3 e auto-shutdown.
> **Referência:** Seções 8, 9 e 10 do documento técnico v1.5

### Step 3.1 — Worker: Configuração do Transmission ✅

**Objetivo:** Criar o arquivo de configuração do Transmission e script de setup.

**Arquivos:**
- `backend/worker/config/transmission.json` — Configuração completa do Transmission daemon
- `backend/worker/config/rclone.conf` — Configuração do rclone para S3

**Configurações do Transmission:**
- download-dir: `/data/downloads`
- incomplete-dir: `/data/incomplete`
- RPC: 127.0.0.1:9091, autenticação habilitada
- Upload limit: 10240 KB/s, ratio limit: 2.0
- Cache: 256 MB, peer limit: 50/torrent

**Critério de aceite:**
- JSON válido com todos os parâmetros da seção 5.3
- RPC bind apenas em localhost (segurança)
- Password como placeholder `${TRANSMISSION_PASSWORD}`

**Referência:** Seção 5.3 (Configuração do Transmission)

---

### Step 3.2 — Worker: Cliente Transmission RPC ✅

**Objetivo:** Implementar cliente Python para comunicação com Transmission via JSON-RPC.

**Arquivos:**
- `backend/worker/scripts/transmission_client.py` — Classe TransmissionClient

**Métodos:**
- `add_torrent(magnet_or_file)` — Adicionar torrent (retorna transmission_id)
- `get_torrent(torrent_id)` — Obter status (percentDone, rateDownload, rateUpload, eta, error, status)
- `stop_torrent(torrent_id)` — Pausar torrent
- `start_torrent(torrent_id)` — Retomar torrent
- `remove_torrent(torrent_id, delete_data)` — Remover torrent
- `stop_all()` / `start_all()` — Pausar/retomar todos

**Critério de aceite:**
- Autenticação RPC via Secrets Manager
- Tratamento de erros de conexão (Transmission não disponível)
- Session ID handling (X-Transmission-Session-Id)

**Referência:** Seção 8.2 (Transmission RPC)

---

### Step 3.3 — Worker: IMDSv2 e utilidades ✅

**Objetivo:** Implementar funções utilitárias: obter instance ID via IMDSv2, logging estruturado, configuração.

**Arquivos:**
- `backend/worker/scripts/utils.py` — get_instance_id(), setup_logging(), load_config()

**Funções:**
- `get_instance_id()` — IMDSv2 com token (PUT + GET)
- `setup_logging()` — Logger estruturado com worker_id, timestamp
- `load_config()` — Carregar variáveis de ambiente com defaults

**Critério de aceite:**
- IMDSv2 com token (não IMDSv1)
- Logger inclui worker_id em todas as mensagens
- Config com valores default para todos os thresholds

**Referência:** Seção 8.1 (IMDSv2), Seção 15 (Variáveis Worker)

---

### Step 3.4 — Worker: Disk Manager ✅

**Objetivo:** Implementar gerenciamento de disco com verificação antes de iniciar e monitoramento contínuo.

**Arquivos:**
- `backend/worker/scripts/disk_manager.py` — Classe DiskManager

**Funções:**
- `check_before_start(item)` — Verificar espaço antes de iniciar download (sizeBytes * 1.1 ou mínimo 5 GB)
- `check_critical()` — Verificar se disco < DISK_CRITICAL_THRESHOLD_GB (2 GB)
- `check_resume()` — Verificar se disco > DISK_RESUME_THRESHOLD_GB (5 GB) para retomar
- `is_paused_for_disk()` / `set_paused_for_disk()` — Flag de estado

**Critério de aceite:**
- Pausa todos os torrents se disco < 2 GB
- Retoma se disco > 5 GB
- Rejeita download se espaço insuficiente (volta para pending sem consumir retry)

**Referência:** Seção 9 (Gerenciamento de Disco)

---

### Step 3.5 — Worker: S3 State Client ✅

**Objetivo:** Implementar cliente S3 para o worker (get pending items, transition state, update progress).

**Arquivos:**
- `backend/worker/scripts/s3_client.py` — Classe WorkerS3Client

**Funções:**
- `get_next_pending_item()` — LIST `queue/pending/`, filtrar por retryAfter, retornar primeiro disponível
- `acquire_lock(item_id)` — Transição pending → processing com ETag (mesma lógica do state_manager)
- `update_progress(item_id, fields)` — Atualizar campos de progresso no JSON (throttled)
- `complete_item(item_id, s3_key, s3_size)` — Transição processing → completed
- `fail_item(item_id, error, is_definitive)` — Transição processing → cancelled ou pending (retry)
- `check_cancel_requested(item_id)` — Verificar flag cancelRequested

**Critério de aceite:**
- Lock via ETag condicional (retorna None se outro worker ganhou)
- Respeita retryAfter (não pega item antes do tempo)
- Update progress com throttle (delta > 2% ou > 30s)

**Referência:** Seções 7 e 8 (Protocolo S3, Worker)

---

### Step 3.6 — Worker: Error Handler e Retry Policy ✅

**Objetivo:** Implementar classificação de erros e política de retry com backoff exponencial.

**Arquivos:**
- `backend/worker/scripts/error_handler.py` — Funções classify_error() e handle_error()

**Lógica:**
- `classify_error(error_string)` — Retorna 'temporary', 'definitive' ou 'operational'
- `handle_error(item, error_string, worker_id)` — Aplica retry policy
  - Definitivo ou retries esgotados (3): mover para cancelled
  - Temporário: mover para pending com retryCount+1 e retryAfter (60s, 300s, 900s)
  - Operacional (disco): mover para pending sem consumir retry

**Erros definitivos:** torrent not found, invalid hash, corrupted file
**Erros temporários:** network timeout, S3 throttling, connection refused
**Erros operacionais:** disk full, size exceeds limit

**Critério de aceite:**
- Backoff exponencial: 1min, 5min, 15min
- Máximo 3 retries para erros temporários
- Erros operacionais não consomem retry
- Logging detalhado de cada erro com classificação

**Referência:** Seção 10 (Retry Policy)

---

### Step 3.7 — Worker: Download Monitor ✅

**Objetivo:** Implementar o loop de monitoramento de progresso de um download ativo.

**Arquivos:**
- `backend/worker/scripts/monitor.py` — Função monitor_download()

**Lógica:**
1. Loop a cada 10 segundos
2. Verificar cancelRequested → se sim, parar torrent e mover para cancelled
3. Obter stats do Transmission (percentDone, speeds, eta, error)
4. Atualizar progresso no S3 (throttled: delta > 2% ou > 30s)
5. Se status=6 (seeding): chamar finalize_download()
6. Se error != 0: chamar handle_error()

**Critério de aceite:**
- Detecta cancelamento em até 10 segundos
- Atualiza progresso com throttle correto
- Detecta conclusão (seeding) e erros do Transmission
- Não faz PUT desnecessário no S3

**Referência:** Seção 8.2 (Monitoramento de Progresso)

---

### Step 3.8 — Worker: Finalize Download (rclone sync) ✅

**Objetivo:** Implementar a finalização do download: sync para S3 via rclone e transição para completed.

**Arquivos:**
- `backend/worker/scripts/sync.py` — Função finalize_download()

**Lógica:**
1. Executar `rclone move` do diretório local para `s3://bucket/downloads/completed/{id}/`
2. Flags: `--s3-storage-class INTELLIGENT_TIERING`, `--transfers 4`, `--checksum`
3. Verificar returncode do rclone
4. Obter tamanho total no S3
5. Remover torrent do Transmission (sem deletar dados locais — já movidos)
6. Transição processing → completed

**Critério de aceite:**
- rclone usa INTELLIGENT_TIERING
- Falha de rclone é tratada como erro (handle_error)
- Arquivo local removido após sync bem-sucedido (rclone move)
- s3SizeBytes preenchido corretamente

**Referência:** Seção 8.3 (Finalização e Sync)

---

### Step 3.9 — Worker: Main Loop e Graceful Shutdown ✅

**Objetivo:** Implementar o loop principal do worker e shutdown gracioso.

**Arquivos:**
- `backend/worker/scripts/main.py` — Função main_loop() e graceful_shutdown()

**Lógica do loop:**
1. check_disk_space_and_pause_if_critical()
2. process_cancellation_requests()
3. get_next_pending_item()
4. Se encontrou: idle_cycles=0, process_item()
5. Se não encontrou: idle_cycles++
6. Se idle_cycles >= 3: graceful_shutdown()
7. Sleep POLL_INTERVAL_SECONDS (60s)

**Graceful shutdown:**
1. Parar todos os torrents ativos
2. Mover itens processing de volta para pending
3. Atualizar index.json
4. Executar `sudo shutdown -h now`

**Signal handling:**
- SIGTERM: graceful_shutdown() (Spot interruption)
- Verificar Spot interruption via metadata endpoint a cada ciclo

**Critério de aceite:**
- Auto-shutdown após 3 ciclos ociosos (~3 min)
- SIGTERM tratado graciosamente
- Itens processing voltam para pending no shutdown
- Logging de início e fim do worker

**Referência:** Seção 8.1 (Loop Principal)

---

### Step 3.10 — Worker: Spot Interruption Handler ✅

**Objetivo:** Implementar detecção de Spot interruption via metadata endpoint.

**Arquivos:**
- `backend/worker/scripts/spot_handler.py` — Função check_spot_interruption()

**Lógica:**
- GET `http://169.254.169.254/latest/meta-data/spot/instance-action` (IMDSv2)
- Se retorna 200: interrupção iminente → graceful_shutdown()
- Se retorna 404: sem interrupção
- Verificar a cada ciclo do main_loop

**Critério de aceite:**
- Usa IMDSv2 (token)
- Não falha se endpoint retorna 404 (normal)
- Trigger graceful_shutdown() se interrupção detectada

**Referência:** Seção 5.3 (Spot interruption handling)

---

## Fase 4 — Frontend e Cloudflare

> Desenvolver a interface React e configurar Cloudflare como CDN/proxy.
> **Referência:** Seção 5.1 do documento técnico v1.5

### Step 4.1 — Frontend: Scaffold Vite + React + TypeScript + TailwindCSS ✅

**Objetivo:** Inicializar o projeto frontend com Vite, React 18, TypeScript e TailwindCSS.

**Arquivos:**
- `frontend/package.json` — Dependências
- `frontend/vite.config.ts` — Configuração Vite
- `frontend/tsconfig.json` — TypeScript config
- `frontend/tailwind.config.js` — TailwindCSS config
- `frontend/postcss.config.js` — PostCSS
- `frontend/index.html` — Entry point
- `frontend/src/main.tsx` — React entry
- `frontend/src/App.tsx` — App root com router
- `frontend/src/styles/globals.css` — Tailwind imports

**Critério de aceite:**
- `npm run dev` inicia sem erros
- `npm run build` gera bundle em `dist/`
- TailwindCSS funciona (classe utilitária renderiza)

---

### Step 4.2 — Frontend: Tipos e interfaces TypeScript ✅

**Objetivo:** Definir todas as interfaces TypeScript que espelham os schemas JSON do backend.

**Arquivos:**
- `frontend/src/types/download.ts` — IDownload, IDownloadListResponse, ICreateDownloadRequest
- `frontend/src/types/status.ts` — IStatusResponse, IWorkerStatus, IQueueStatus
- `frontend/src/types/auth.ts` — ILoginRequest, ILoginResponse

**Critério de aceite:**
- Interfaces espelham exatamente os schemas da seção 3.2 e contratos da seção 6
- Todos os campos com tipos corretos (string | null, number, enum)

**Referência:** Seções 3.2, 3.3 e 6 (Schemas e Contratos)

---

### Step 4.3 — Frontend: API Service (HTTP client) ✅

**Objetivo:** Implementar serviço HTTP que comunica com a API backend.

**Arquivos:**
- `frontend/src/services/api.ts` — Classe ApiService com todos os métodos

**Métodos:**
- `login(password)` — POST /auth/login
- `listDownloads(status?, page?, limit?)` — GET /downloads
- `getDownload(id)` — GET /downloads/{id}
- `createDownload(request)` — POST /downloads
- `updateDownload(id, name)` — PATCH /downloads/{id}
- `deleteDownload(id)` — DELETE /downloads/{id}
- `cancelDownload(id)` — POST /downloads/{id}/cancel
- `requeueDownload(id)` — POST /downloads/{id}/requeue
- `getDownloadUrl(id, expiresIn)` — POST /downloads/{id}/download-url
- `getUploadUrl(filename, sizeBytes)` — POST /downloads/upload-url
- `uploadTorrentFile(uploadUrl, file)` — PUT direto no S3
- `getStatus()` — GET /status

**Critério de aceite:**
- JWT armazenado em cookie HttpOnly (ou localStorage como fallback)
- Interceptor para adicionar Authorization header
- Interceptor para redirect ao /login se 401
- Base URL configurável via env var (VITE_API_URL)

**Referência:** Seção 6 (Contratos de API)

---

### Step 4.4 — Frontend: Auth Context e LoginPage ✅

**Objetivo:** Implementar contexto de autenticação e página de login.

**Arquivos:**
- `frontend/src/services/auth-context.tsx` — AuthContext com login/logout/isAuthenticated
- `frontend/src/pages/LoginPage.tsx` — Formulário de senha única
- `frontend/src/components/ProtectedRoute.tsx` — Wrapper que redireciona para /login se não autenticado

**Critério de aceite:**
- Login com senha única
- Redirect para / após login bem-sucedido
- Redirect para /login se token expirado
- Logout limpa token e redireciona

---

### Step 4.5 — Frontend: Dashboard (página principal) ✅

**Objetivo:** Implementar a página principal com contadores por status e visão geral.

**Arquivos:**
- `frontend/src/pages/Dashboard.tsx` — Página principal
- `frontend/src/components/StatusCard.tsx` — Card com contador por status
- `frontend/src/components/WorkerStatus.tsx` — Indicador de status da EC2

**Funcionalidades:**
- 4 cards: Pending, Processing, Completed, Cancelled (com contadores)
- Status do worker (running/stopped) com indicador visual
- Link rápido para adicionar novo download
- Polling: 10s se processing > 0, 60s caso contrário

**Critério de aceite:**
- Contadores atualizados via polling
- Indicador visual do worker (verde=running, cinza=stopped)
- Responsivo (mobile-friendly)

**Referência:** Seção 5.1 (Dashboard)

---

### Step 4.6 — Frontend: DownloadList (listagem com filtros) ✅

**Objetivo:** Implementar listagem de downloads com filtros por status.

**Arquivos:**
- `frontend/src/pages/DownloadList.tsx` — Página de listagem
- `frontend/src/components/DownloadCard.tsx` — Card individual de download
- `frontend/src/components/ProgressBar.tsx` — Barra de progresso
- `frontend/src/components/StatusBadge.tsx` — Badge colorido por status

**Funcionalidades:**
- Filtro por status (tabs ou dropdown)
- Card com: nome, status badge, progresso, velocidade, ETA
- Ações rápidas: cancelar, deletar (conforme status)
- Polling de progresso para itens em processing

**Critério de aceite:**
- Filtro funciona corretamente
- Progresso atualiza em tempo real (polling 10s)
- Ações respeitam tabela de operações por estado (seção 4.3)

**Referência:** Seção 5.1 (DownloadList)

---

### Step 4.7 — Frontend: AddDownload (formulário de criação) ✅

**Objetivo:** Implementar formulário para adicionar download via magnet link ou upload de .torrent.

**Arquivos:**
- `frontend/src/pages/AddDownload.tsx` — Página de criação
- `frontend/src/components/MagnetInput.tsx` — Input para magnet link
- `frontend/src/components/TorrentUpload.tsx` — Upload de arquivo .torrent

**Funcionalidades:**
- Tab: Magnet Link | Arquivo .torrent
- Magnet: input de texto com validação (começa com `magnet:?`)
- Torrent: drag-and-drop ou file picker (max 1MB, extensão .torrent)
- Campo nome (opcional, max 255 chars)
- Gera clientRequestId (UUID) para idempotência
- Upload .torrent: obtém Pre-signed URL → upload direto S3 → POST /downloads

**Critério de aceite:**
- Validação client-side antes de enviar
- Upload .torrent vai direto para S3 (não passa pela Lambda)
- Idempotência: duplo clique não cria duplicata
- Redirect para /downloads após criação

**Referência:** Seções 5.1 e 6.3 (AddDownload, Upload)

---

### Step 4.8 — Frontend: DownloadDetail (detalhes e ações) ✅

**Objetivo:** Implementar página de detalhes de um download com todas as ações disponíveis.

**Arquivos:**
- `frontend/src/pages/DownloadDetail.tsx` — Página de detalhes
- `frontend/src/components/DownloadActions.tsx` — Botões de ação contextuais

**Funcionalidades:**
- Informações completas: nome, status, progresso, velocidades, ETA, tamanho, datas
- Barra de progresso detalhada
- Ações contextuais por status:
  - Pending: editar nome, cancelar, deletar
  - Processing: editar nome, cancelar
  - Completed: editar nome, gerar link de download, deletar
  - Cancelled: editar nome, recolocar na fila, deletar
- Mensagem de erro (se houver)
- Polling de progresso se processing

**Critério de aceite:**
- Ações corretas por status (seção 4.3)
- Link de download abre Pre-signed URL em nova aba
- Exibe custo estimado de transferência
- Polling automático se processing

**Referência:** Seção 5.1 (DownloadDetail)

---

### Step 4.9 — Frontend: InfraStatus (status da infraestrutura) ✅

**Objetivo:** Implementar página de status da infraestrutura.

**Arquivos:**
- `frontend/src/pages/InfraStatus.tsx` — Página de infraestrutura

**Funcionalidades:**
- Status do worker: running/stopped/starting/stopping com uptime
- Instance type e ID
- Contadores de fila (pending, processing, completed, cancelled)
- Indicador de staleness do index.json
- Polling a cada 30s

**Critério de aceite:**
- Exibe todas as informações do GET /status
- Indicador visual de staleness (warning se > 2min)

**Referência:** Seções 5.1 e 6.5 (InfraStatus, GET /status)

---

### Step 4.10 — Frontend: Layout, navegação e responsividade ✅

**Objetivo:** Implementar layout global, sidebar/navbar e garantir responsividade.

**Arquivos:**
- `frontend/src/components/Layout.tsx` — Layout com sidebar/header
- `frontend/src/components/Navbar.tsx` — Navegação principal
- `frontend/src/components/Sidebar.tsx` — Menu lateral (desktop)

**Funcionalidades:**
- Navbar com logo, links de navegação e botão logout
- Sidebar colapsável em desktop, drawer em mobile
- Rotas: /, /downloads, /downloads/new, /downloads/:id, /infrastructure
- Tema escuro (dark mode) como padrão

**Critério de aceite:**
- Navegação funciona em todas as rotas
- Responsivo: mobile (< 768px) e desktop
- Dark mode aplicado

---

### Step 4.11 — Frontend: Build e deploy para S3 ✅

**Objetivo:** Configurar build de produção e script de deploy para o bucket S3 frontend.

**Arquivos:**
- `frontend/vite.config.ts` — Ajustar base URL para produção
- `scripts/deploy/deploy-frontend.sh` — Script de deploy (build + sync S3)
- `frontend/.env.production` — VITE_API_URL para produção

**Lógica do deploy:**
1. `npm run build` — Gera `dist/`
2. `aws s3 sync dist/ s3://seedbox-frontend-{account-id}/ --delete`
3. Configurar Cache-Control headers: `max-age=31536000` para assets, `no-cache` para index.html

**Critério de aceite:**
- Build de produção sem erros
- Assets com hash no nome (cache busting automático do Vite)
- index.html com no-cache
- Script de deploy funcional

---

### Step 4.12 — Cloudflare: Configuração DNS, SSL e Cache ✅

**Objetivo:** Documentar e/ou automatizar a configuração da Cloudflare.

**Arquivos:**
- `docs/infrastructure/cloudflare-setup.md` — Guia passo-a-passo de configuração
- `iac/terraform/modules/cloudflare/main.tf` — (Opcional) Terraform com provider cloudflare

**Configurações a documentar:**
1. DNS: CNAME `seedbox` → S3 Website Endpoint (proxiado)
2. DNS: CNAME `api.seedbox` → API Gateway URL (proxiado)
3. SSL: Full para frontend, Full (strict) para API
4. Cache Rules: assets 1 ano, index.html bypass, API bypass
5. WAF: Rate limit 200 req/min em api.seedbox, Bot Fight Mode
6. HSTS: habilitado (max-age=31536000)

**Critério de aceite:**
- Documentação completa e testável
- Frontend acessível via `https://seedbox.dominio.com`
- API acessível via `https://api.seedbox.dominio.com`
- S3 direto bloqueado (apenas via Cloudflare)

**Referência:** Seção 5.1 (Cloudflare config completa)

---

## Fase 5 — Testes e Validação Final

> Testes unitários, integração, cenários de falha controlada e documentação final.
> **Referência:** Seções 16 e 17 do documento técnico v1.5, RULES 12-14

### Step 5.1 — Testes unitários: State Manager e Validators ✅

**Objetivo:** Testes unitários para state_manager.py e validators.py com moto (mock S3).

**Arquivos:**
- `tests/unit/test_state_manager.py` — Testes de get, put, delete, list, transition_state
- `tests/unit/test_validators.py` — Testes de validação de entrada

**Cenários state_manager:**
- Transição bem-sucedida (pending → processing)
- ETag mismatch retorna None
- Lock conflict levanta exceção
- State mismatch levanta exceção
- Version incrementa corretamente
- index.json atualizado após transição

**Cenários validators:**
- Magnet link válido e inválido
- UUID v4 válido e inválido
- Nome com mais de 255 caracteres
- Arquivo .torrent > 1MB
- expiresIn > 604800

**Critério de aceite:**
- Cobertura > 90% para ambos os módulos
- Usa moto para mock S3 (sem chamadas reais)
- Estrutura AAA (Arrange-Act-Assert)

**Referência:** RULE 12 (Cobertura), RULE 14 (Nomeação)

---

### Step 5.2 — Testes unitários: Auth e Routes ✅

**Objetivo:** Testes unitários para auth.py e routes.py.

**Arquivos:**
- `tests/unit/test_auth.py` — Testes de login e verify_token
- `tests/unit/test_routes.py` — Testes de cada rota da API

**Cenários auth:**
- Login com senha correta retorna JWT válido
- Login com senha incorreta retorna 401
- Token expirado retorna 401
- Token com assinatura inválida retorna 401

**Cenários routes:**
- Criar download com magnet link
- Criar download idempotente (mesmo clientRequestId)
- Listar downloads com filtro por status
- Cancelar download em cada status
- Gerar Pre-signed URL para completed
- Gerar Pre-signed URL para não-completed retorna 400

**Critério de aceite:**
- Cobertura > 90%
- Mock de Secrets Manager e S3
- Testa todos os status codes de resposta

---

### Step 5.3 — Testes unitários: Worker ✅

**Objetivo:** Testes unitários para os módulos do worker.

**Arquivos:**
- `tests/unit/test_transmission_client.py` — Mock de RPC
- `tests/unit/test_disk_manager.py` — Mock de shutil.disk_usage
- `tests/unit/test_error_handler.py` — Classificação de erros e retry
- `tests/unit/test_monitor.py` — Loop de monitoramento

**Cenários error_handler:**
- Erro temporário com retries restantes → pending com backoff
- Erro temporário com retries esgotados → cancelled
- Erro definitivo → cancelled imediato
- Erro operacional (disco) → pending sem consumir retry

**Cenários disk_manager:**
- Disco < 2 GB → pausa todos
- Disco > 5 GB após pausa → retoma
- Espaço insuficiente para download → rejeita

**Critério de aceite:**
- Cobertura > 90% para cada módulo
- Backoff exponencial testado (60s, 300s, 900s)
- Classificação de erros correta para cada categoria

---

### Step 5.4 — Testes de falha controlada (10 cenários) ✅

**Objetivo:** Implementar os 10 cenários de falha controlada obrigatórios.

**Arquivos:**
- `tests/integration/test_failure_scenarios.py` — Todos os 10 cenários

**Cenários:**
1. Disco cheio → worker pausa, registra erro, retoma ao liberar
2. Interrupção EC2 (SIGTERM) → graceful shutdown, itens voltam para pending
3. Falha de PUT no S3 → retry com backoff
4. Magnet link inválido → erro definitivo, cancelled
5. Race enqueue + shutdown → Lambda detecta stopping, retry após 30s
6. Duplo clique (idempotência) → retorna item original
7. index.json stale → frontend faz fallback para LIST
8. Cancelamento durante rclone → mata processo, remove parcial, cancelled
9. Acesso direto ao S3 (sem Cloudflare) → 403 Forbidden
10. Pre-signed URL expirada → 403

**Critério de aceite:**
- Todos os 10 cenários implementados e passando
- Documentar resultados em `docs/testing/failure-scenarios.md`

**Referência:** Seção 16 (Testes de Falha Controlada), RULE 13

---

### Step 5.5 — Observabilidade: CloudWatch Alarms ✅

**Objetivo:** Configurar alarmes CloudWatch via Terraform.

**Arquivos:**
- `iac/terraform/modules/lambda/alarms.tf` — Alarmes Lambda
- `iac/terraform/modules/ec2/alarms.tf` — Alarmes EC2

**Alarmes:**
- Lambda Errors > 5 em 5 min → SNS
- API Gateway P99 latency > 5000ms → SNS
- EC2 Disk Used > 80% → SNS
- EC2 CPU > 90% por 10 min → SNS
- Spot Interruption → SNS

**Critério de aceite:**
- `terraform plan` mostra todos os alarmes
- SNS topic criado para notificações
- Alarmes com thresholds corretos

**Referência:** Seção 17 (Observabilidade e Alarmes)

---

### Step 5.6 — Documentação final e validação ✅

**Objetivo:** Atualizar toda a documentação, validar o projeto completo e preparar para deploy.

**Arquivos a atualizar:**
- `docs/CHANGELOG.md` — Entradas de todas as fases
- `docs/ARCHITECTURE.md` — Diagrama final
- `docs/API_REFERENCE.md` — Referência completa com exemplos
- `docs/COMPONENTS.md` — Todos os componentes documentados
- `docs/infrastructure/resources.md` — Lista final de recursos AWS
- `docs/testing/failure-scenarios.md` — Resultados dos 10 cenários
- `docs/security/iam-policies.md` — Policies documentadas
- `memory-bank/PROJECT_CONTEXT.md` — Todas as fases ✅
- `memory-bank/INTEGRATION_POINTS.md` — Todos os pontos documentados

**Critério de aceite:**
- Todos os testes passando (`pytest` green)
- `terraform validate` e `terraform plan` sem erros
- `npm run build` sem erros
- Documentação completa e atualizada
- Memory Bank sincronizado com estado atual

---

## Resumo de Progresso

| Fase | Steps | Concluídos | Status |
|------|-------|-----------|--------|
| 1 — IaC | 10 | 10 | ✅ |
| 2 — Backend | 12 | 12 | ✅ |
| 3 — Worker | 10 | 10 | ✅ |
| 4 — Frontend | 12 | 12 | ✅ |
| 5 — Testes | 6 | 6 | ✅ |
| **Total** | **50** | **50** | **100%** |
