# Seedbox Serverless AWS — Documento Técnico de Desenvolvimento v1.5

**Status:** Architecture Approved — Ready for Build  
**Versão:** 1.5  
**Data:** Abril de 2026  
**Autores:** Manus AI + GPT-4o (revisão arquitetural conjunta)  
**Alterações em relação à v1.4:** Substituição do Amazon CloudFront pela Cloudflare como camada de CDN, proxy reverso e certificados SSL. Eliminação dos custos de CloudFront e ACM.

---

## Índice

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura de Alto Nível](#2-arquitetura-de-alto-nível)
3. [Estrutura de Dados no S3](#3-estrutura-de-dados-no-s3)
4. [Modelo de Estado dos Downloads](#4-modelo-de-estado-dos-downloads)
5. [Componentes do Sistema](#5-componentes-do-sistema)
   - 5.1 [Frontend (S3 + Cloudflare)](#51-frontend-s3--cloudflare)
   - 5.2 [API Gateway + Lambda](#52-api-gateway--lambda)
   - 5.3 [Worker EC2 Spot](#53-worker-ec2-spot)
   - 5.4 [Bucket S3](#54-bucket-s3)
6. [Contratos de API](#6-contratos-de-api)
7. [Protocolo de Consistência do S3](#7-protocolo-de-consistência-do-s3)
8. [Worker: Lógica de Execução](#8-worker-lógica-de-execução)
9. [Gerenciamento de Disco](#9-gerenciamento-de-disco)
10. [Retry Policy](#10-retry-policy)
11. [Idempotência](#11-idempotência)
12. [Autenticação e Segurança](#12-autenticação-e-segurança)
13. [Pre-signed URLs](#13-pre-signed-urls)
14. [Infraestrutura como Código (IaC)](#14-infraestrutura-como-código-iac)
15. [Variáveis de Ambiente e Configuração](#15-variáveis-de-ambiente-e-configuração)
16. [Testes de Falha Controlada](#16-testes-de-falha-controlada)
17. [Observabilidade e Alarmes](#17-observabilidade-e-alarmes)
18. [Estimativa de Custo](#18-estimativa-de-custo)
19. [Roadmap](#19-roadmap)

---

## 1. Visão Geral do Sistema

O Seedbox Serverless AWS é um sistema de download via torrent baseado inteiramente em serviços gerenciados da AWS, projetado para uso pessoal com custo variável e zero de operação quando ocioso. O sistema não utiliza banco de dados relacional; toda a persistência de estado é feita através de arquivos JSON no Amazon S3, eliminando um componente de custo fixo desnecessário para o volume de operações previsto.

A proposta central é simples: o usuário submete um magnet link ou arquivo `.torrent` via interface web, a infraestrutura de computação é ligada automaticamente, o download é executado, o arquivo é movido para o S3 e a instância é desligada. O custo de computação é zero quando não há downloads ativos.

A partir da v1.5, a **Cloudflare** substitui o Amazon CloudFront como camada de CDN, proxy reverso e emissão de certificados SSL/TLS. Essa mudança elimina dois componentes de custo da AWS (CloudFront e ACM) e adiciona benefícios como proteção DDoS gratuita, firewall de aplicação (WAF) no plano gratuito e gerenciamento de DNS integrado. O plano **Free** da Cloudflare é suficiente para todos os requisitos desta arquitetura.

**Tecnologias principais:**

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Frontend | React + S3 + **Cloudflare** | CDN global gratuita, SSL automático, sem custo de distribuição |
| API | AWS Lambda + API Gateway | Serverless, sem custo em idle |
| Worker | EC2 Spot (`t3.medium`) + Transmission | Até 90% mais barato que On-Demand |
| Armazenamento | Amazon S3 Intelligent-Tiering | Custo automático por frequência de acesso |
| Estado da fila | Arquivos JSON no S3 | Sem banco de dados, custo desprezível |
| Autenticação | JWT + AWS Secrets Manager | Suficiente para usuário único em v1 |
| DNS e SSL | **Cloudflare** (plano Free) | Certificados gratuitos, proxy reverso, proteção DDoS |

---

## 2. Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUÁRIO                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (TLS gerenciado pela Cloudflare)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              Cloudflare (DNS + Proxy + CDN + WAF)                │
│  - seedbox.seudominio.com → S3 Website Endpoint (frontend)       │
│  - api.seedbox.seudominio.com → API Gateway URL (backend)        │
│  - Certificado SSL/TLS Universal (gratuito)                      │
│  - Cache de assets estáticos (JS, CSS, imagens)                  │
│  - Proteção DDoS Layer 3/4/7 (gratuita)                          │
│  - WAF básico (plano Free)                                        │
└──────────┬───────────────────────────────────┬───────────────────┘
           │ HTTP (origem S3)                  │ HTTPS (origem API GW)
           ▼                                   ▼
┌──────────────────────┐         ┌─────────────────────────────────┐
│  S3 Website Bucket   │         │   API Gateway (HTTP API)        │
│  (Frontend React)    │         │   - Authorizer Lambda JWT       │
│  - Acesso público    │         │   - Rate limiting: 100 req/min  │
│    apenas via        │         │   - CORS: apenas domínio CF     │
│    Cloudflare        │         └──────────────┬──────────────────┘
│    (IP ranges)       │                        │ Invoke
└──────────────────────┘                        ▼
                                 ┌──────────────────────────────────┐
                                 │   Lambda Functions (Python 3.12) │
                                 │   - seedbox-api                  │
                                 │   - seedbox-worker-trigger       │
                                 └──────────┬───────────────────────┘
                                            │ S3 API / EC2 API
                                            ▼
                              ┌─────────────────────────────────────┐
                              │   Amazon S3 (Estado + Arquivos)     │
                              │◄────────────────────────────────────┤
                              │   EC2 Spot (t3.medium)              │
                              │   transmission-daemon               │
                              │   worker.py + rclone                │
                              └─────────────────────────────────────┘
```

### 2.1 Roteamento via Cloudflare

A Cloudflare atua como proxy reverso para dois subdomínios distintos, ambos sob o mesmo domínio do usuário:

| Subdomínio | Destino (Origem) | Tipo de Proxy |
|-----------|-----------------|---------------|
| `seedbox.seudominio.com` | S3 Website Endpoint (`http://bucket.s3-website-region.amazonaws.com`) | Cloudflare Proxy (laranja) — CDN + cache |
| `api.seedbox.seudominio.com` | API Gateway URL (`https://xxxx.execute-api.region.amazonaws.com`) | Cloudflare Proxy (laranja) — apenas proxy, sem cache |

O uso do proxy Cloudflare (ícone laranja no painel DNS) garante que o IP real da origem (S3 e API Gateway) nunca seja exposto ao usuário final, adicionando uma camada de anonimização da infraestrutura.

### 2.2 Fluxo Principal de um Download

1. Usuário acessa `https://seedbox.seudominio.com` — Cloudflare serve o frontend React cacheado.
2. Frontend faz chamadas para `https://api.seedbox.seudominio.com/api/*` — Cloudflare proxia para API Gateway.
3. Lambda valida JWT, cria JSON em `queue/pending/{id}.json` e objeto de idempotência.
4. Lambda verifica se EC2 está parada; se sim, chama `ec2.start_instances()`.
5. Worker na EC2 detecta novos itens em `queue/pending/`, adquire lock atômico via ETag e inicia download no Transmission.
6. Worker atualiza progresso a cada ciclo (throttle: apenas se delta > 2% ou > 30s).
7. Ao concluir, worker move arquivo para `downloads/completed/{id}/` via `rclone move`.
8. Worker verifica se há mais itens pendentes; após 3 ciclos ociosos (~3 min), desliga a instância.
9. Frontend consulta `queue/index.json` via API a cada 10s; fallback para LIST direto se `index.json` estiver desatualizado há mais de 2 minutos.

---

## 3. Estrutura de Dados no S3

### 3.1 Prefixos do Bucket

```
s3://seedbox-{account-id}/
├── queue/
│   ├── index.json                    # Índice consolidado de todos os itens
│   ├── pending/
│   │   └── {downloadId}.json
│   ├── processing/
│   │   └── {downloadId}.json
│   ├── completed/
│   │   └── {downloadId}.json
│   └── cancelled/
│       └── {downloadId}.json
├── torrents/
│   └── {downloadId}.torrent          # Arquivo .torrent original (quando enviado)
├── downloads/
│   └── completed/
│       └── {downloadId}/
│           └── {filename}            # Arquivo baixado, pronto para download
└── idempotency/
    └── {clientRequestId}             # Objeto de deduplicação (TTL: 24h via Lifecycle)
```

### 3.2 Schema do JSON de Download

```json
{
  "id": "uuid-v4",
  "clientRequestId": "uuid-v4-gerado-pelo-frontend",
  "name": "Nome do torrent (editável pelo usuário)",
  "status": "pending | processing | completed | cancelled",
  "type": "magnet | torrent_file",
  "magnetLink": "magnet:?xt=urn:btih:...",
  "torrentS3Key": "torrents/{id}.torrent",
  "transmissionId": 42,
  "sizeBytes": 1073741824,
  "sizeBytesDownloaded": 536870912,
  "progressPercent": 50.0,
  "downloadSpeedBps": 5242880,
  "uploadSpeedBps": 1048576,
  "eta": 120,
  "errorMessage": null,
  "retryCount": 0,
  "retryAfter": null,
  "workerId": null,
  "version": 7,
  "createdAt": "2026-04-22T10:00:00Z",
  "updatedAt": "2026-04-22T10:05:30Z",
  "startedAt": "2026-04-22T10:01:00Z",
  "completedAt": null,
  "cancelledAt": null,
  "s3Key": null,
  "s3SizeBytes": null
}
```

**Descrição dos campos críticos:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string | UUID v4 gerado pela Lambda na criação |
| `clientRequestId` | string | UUID gerado pelo frontend para idempotência |
| `status` | enum | Estado atual: `pending`, `processing`, `completed`, `cancelled` |
| `workerId` | string\|null | ID da instância EC2 que está processando. `null` = disponível para lock |
| `version` | integer | Contador de versão para controle de concorrência via ETag |
| `retryCount` | integer | Número de tentativas já realizadas (máximo: 3) |
| `retryAfter` | ISO 8601\|null | Timestamp a partir do qual o worker pode tentar novamente |
| `errorMessage` | string\|null | Mensagem de erro atual. Temporário durante pausa por disco; permanente em erro definitivo |
| `torrentS3Key` | string\|null | Chave S3 do arquivo `.torrent` original (apenas para `type: torrent_file`) |
| `transmissionId` | integer\|null | ID do torrent no Transmission daemon (usado para RPC) |
| `s3Key` | string\|null | Chave S3 do arquivo concluído (preenchido após conclusão) |

### 3.3 Schema do index.json

```json
{
  "updatedAt": "2026-04-22T10:05:30Z",
  "workerStatus": "running | stopped | starting | stopping",
  "workerInstanceId": "i-0abc123def456",
  "items": [
    {
      "id": "uuid",
      "name": "Nome do torrent",
      "status": "processing",
      "progressPercent": 50.0,
      "sizeBytes": 1073741824,
      "updatedAt": "2026-04-22T10:05:30Z"
    }
  ]
}
```

---

## 4. Modelo de Estado dos Downloads

### 4.1 Diagrama de Transições

```
                    ┌─────────┐
         POST /downloads      │
         ─────────────────►   │  PENDING
                              └────┬────┘
                                   │ Worker adquire lock
                                   │ (ETag condicional)
                                   ▼
                              ┌─────────────┐
                              │  PROCESSING │
                              └──┬──────┬───┘
                                 │      │
              Download concluído │      │ Erro definitivo ou
              + sync S3          │      │ cancelamento pelo usuário
                                 ▼      ▼
                         ┌───────────┐  ┌───────────┐
                         │ COMPLETED │  │ CANCELLED │
                         └───────────┘  └───────────┘
                                              │
                                              │ Usuário recoloca na fila
                                              ▼
                                         ┌─────────┐
                                         │ PENDING │
                                         └─────────┘
```

### 4.2 Transições Permitidas

| De | Para | Quem pode executar | Condição |
|----|------|--------------------|----------|
| `pending` | `processing` | Worker EC2 | Lock ETag bem-sucedido |
| `pending` | `cancelled` | Lambda (API) | Usuário solicita cancelamento |
| `processing` | `completed` | Worker EC2 | Download + sync S3 concluídos |
| `processing` | `cancelled` | Lambda (API) | Usuário solicita cancelamento; Lambda seta flag `cancelRequested` no JSON |
| `processing` | `pending` | Worker EC2 | Erro temporário com retries restantes; ou disco insuficiente |
| `processing` | `cancelled` | Worker EC2 | Erro definitivo ou retries esgotados |
| `cancelled` | `pending` | Lambda (API) | Usuário recoloca na fila |
| `completed` | `completed` | Lambda (API) | Edição de nome (único campo editável) |

### 4.3 Operações CRUD por Estado

| Operação | `pending` | `processing` | `completed` | `cancelled` |
|----------|:---------:|:------------:|:-----------:|:-----------:|
| Visualizar detalhes | ✓ | ✓ | ✓ | ✓ |
| Editar nome | ✓ | ✓ | ✓ | ✓ |
| Cancelar | ✓ | ✓ | — | — |
| Remover permanentemente | ✓ | ✓ | ✓ | ✓ |
| Gerar Pre-signed URL | — | — | ✓ | — |
| Recolocar na fila | — | — | — | ✓ |

---

## 5. Componentes do Sistema

### 5.1 Frontend (S3 + Cloudflare)

**Tecnologia:** React 18 + TypeScript + Vite + TailwindCSS  
**Hospedagem:** S3 bucket com website hosting estático  
**CDN e SSL:** Cloudflare (plano Free) — proxy reverso, certificado Universal SSL, cache de assets  
**Autenticação:** JWT armazenado em cookie `HttpOnly; Secure; SameSite=Strict`

#### Configuração do S3 para Website Hosting

O bucket de frontend é configurado com website hosting habilitado e acesso público restrito aos IPs da Cloudflare. Isso garante que o conteúdo só seja acessível através do proxy Cloudflare, nunca diretamente pelo endpoint S3.

```json
// Bucket Policy — permite acesso apenas dos IPs da Cloudflare
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudflareOnly",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::seedbox-frontend-{account-id}/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": [
            "173.245.48.0/20",
            "103.21.244.0/22",
            "103.22.200.0/22",
            "103.31.4.0/22",
            "141.101.64.0/18",
            "108.162.192.0/18",
            "190.93.240.0/20",
            "188.114.96.0/20",
            "197.234.240.0/22",
            "198.41.128.0/17",
            "162.158.0.0/15",
            "104.16.0.0/13",
            "104.24.0.0/14",
            "172.64.0.0/13",
            "131.0.72.0/22",
            "2400:cb00::/32",
            "2606:4700::/32",
            "2803:f800::/32",
            "2405:b500::/32",
            "2405:8100::/32",
            "2a06:98c0::/29",
            "2c0f:f248::/32"
          ]
        }
      }
    }
  ]
}
```

> **Nota:** A lista de IPs da Cloudflare é mantida em [https://www.cloudflare.com/ips/](https://www.cloudflare.com/ips/) e deve ser atualizada periodicamente. Recomenda-se automatizar essa atualização via Lambda agendada mensalmente.

#### Configuração DNS na Cloudflare

| Tipo | Nome | Conteúdo | Proxy |
|------|------|---------|-------|
| `CNAME` | `seedbox` | `seedbox-frontend-{account-id}.s3-website-us-east-1.amazonaws.com` | ✓ Proxiado (laranja) |
| `CNAME` | `api.seedbox` | `xxxx.execute-api.us-east-1.amazonaws.com` | ✓ Proxiado (laranja) |

#### Configuração de Cache na Cloudflare

As seguintes regras de cache devem ser configuradas no painel Cloudflare (Cache Rules):

| Padrão de URL | Cache | TTL | Justificativa |
|--------------|-------|-----|---------------|
| `seedbox.seudominio.com/assets/*` | Cache Everything | 1 ano | Assets com hash no nome (Vite) |
| `seedbox.seudominio.com/*.js` | Cache Everything | 1 hora | Scripts sem hash |
| `seedbox.seudominio.com/*.css` | Cache Everything | 1 hora | Estilos sem hash |
| `seedbox.seudominio.com/index.html` | Bypass Cache | — | SPA entry point sempre fresco |
| `api.seedbox.seudominio.com/*` | Bypass Cache | — | API nunca deve ser cacheada |

#### Configuração SSL/TLS na Cloudflare

No painel Cloudflare, em **SSL/TLS → Overview**, configurar o modo como **Full (strict)**:

- **Full (strict):** Cloudflare valida o certificado da origem. Como o S3 Website Endpoint usa HTTP (não HTTPS), usar o modo **Full** (sem strict) para o subdomínio do frontend, e **Full (strict)** para o subdomínio da API (API Gateway já tem certificado válido).
- O certificado Universal SSL da Cloudflare é emitido automaticamente e renovado sem custo.

#### Regras de Segurança Cloudflare (WAF — plano Free)

| Regra | Ação | Descrição |
|-------|------|-----------|
| Bloquear países não utilizados | Block | Opcional: restringir acesso geográfico |
| Rate limit por IP | Block (5 min) | > 200 req/min por IP no subdomínio `api.seedbox` |
| Bloquear bots conhecidos | Managed Challenge | Cloudflare Bot Fight Mode (gratuito) |

#### Páginas e Componentes do Frontend

| Rota | Componente | Descrição |
|------|-----------|-----------|
| `/login` | `LoginPage` | Formulário de senha única; solicita JWT |
| `/` | `Dashboard` | Visão geral com contadores por status |
| `/downloads` | `DownloadList` | Listagem completa com filtros por status |
| `/downloads/new` | `AddDownload` | Formulário: magnet link ou upload de `.torrent` |
| `/downloads/:id` | `DownloadDetail` | Detalhes, progresso, ações e Pre-signed URL |
| `/infrastructure` | `InfraStatus` | Status da EC2 (ligada/desligada), fila, custos |

**Polling de status:** O frontend realiza polling no endpoint `GET /status` a cada 10 segundos quando há itens em `processing`. Quando todos os itens estão em `completed` ou `cancelled`, o intervalo aumenta para 60 segundos.

**Upload de arquivo `.torrent`:** O frontend envia o arquivo via `POST /downloads/upload-url` para obter uma Pre-signed URL de PUT, faz o upload direto para o S3 e depois chama `POST /downloads` com o `torrentS3Key` retornado. O upload vai direto do browser para o S3, sem passar pela Lambda ou pela Cloudflare.

### 5.2 API Gateway + Lambda

**Tipo:** HTTP API (não REST API — menor latência e custo)  
**Runtime:** Python 3.12  
**Memória:** 256 MB  
**Timeout:** 30 segundos  
**Authorizer:** Lambda Authorizer que valida JWT via `PyJWT` + chave do Secrets Manager

**Funções Lambda:**

| Função | Trigger | Responsabilidade |
|--------|---------|-----------------|
| `seedbox-authorizer` | API Gateway Authorizer | Valida JWT; retorna policy IAM |
| `seedbox-api` | API Gateway HTTP | CRUD de downloads, status, Pre-signed URLs |
| `seedbox-worker-trigger` | Invocada por `seedbox-api` | Liga/desliga EC2 Spot assincronamente |

### 5.3 Worker EC2 Spot

**Tipo de instância:** `t3.medium` (2 vCPU, 4 GB RAM)  
**AMI:** Amazon Linux 2023  
**Disco:** 200 GB `gp3` (IOPS: 3000, throughput: 125 MB/s)  
**Spot interruption handling:** Script de shutdown gracioso via `instance-action` metadata endpoint  
**IAM Role:** Permissões mínimas descritas na seção 12.3

**Software instalado via User Data:**

```bash
#!/bin/bash
dnf install -y transmission-daemon python3.12 python3-pip
pip3 install boto3 requests

curl https://rclone.org/install.sh | bash

systemctl stop transmission-daemon
# ... configuração do Transmission (ver seção completa abaixo)
systemctl start transmission-daemon

python3 /opt/seedbox/worker.py &
```

**Configuração do Transmission:**

```json
{
  "download-dir": "/data/downloads",
  "incomplete-dir": "/data/incomplete",
  "incomplete-dir-enabled": true,
  "rpc-enabled": true,
  "rpc-bind-address": "127.0.0.1",
  "rpc-port": 9091,
  "rpc-whitelist-enabled": false,
  "rpc-authentication-required": true,
  "rpc-username": "seedbox",
  "rpc-password": "${TRANSMISSION_PASSWORD}",
  "speed-limit-up": 10240,
  "speed-limit-up-enabled": true,
  "seed-queue-enabled": true,
  "seed-queue-size": 5,
  "ratio-limit": 2.0,
  "ratio-limit-enabled": true,
  "peer-limit-global": 200,
  "peer-limit-per-torrent": 50,
  "max-peers-global": 200,
  "upload-slots-per-torrent": 8,
  "cache-size-mb": 256
}
```

**Parâmetros do Transmission — justificativa:**

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| `speed-limit-up` | 10240 KB/s (10 MB/s) | Limita custo de transferência de saída da EC2 |
| `ratio-limit` | 2.0 | Boa cidadania na rede BitTorrent sem custo excessivo |
| `seed-queue-size` | 5 | Máximo de torrents semeando simultaneamente |
| `cache-size-mb` | 256 | Reduz I/O em disco para torrents com muitos arquivos pequenos |
| `peer-limit-per-torrent` | 50 | Balanceia velocidade e consumo de conexões |

### 5.4 Bucket S3

**Nome:** `seedbox-{aws-account-id}` (sufixo de conta para unicidade global)  
**Região:** Mesma região da EC2 (ex: `us-east-1`) para transferência gratuita  
**Versionamento:** Desabilitado  
**Classe de armazenamento:** S3 Intelligent-Tiering para o prefixo `downloads/`

**Lifecycle Rules:**

| Prefixo | Regra | Ação |
|---------|-------|------|
| `idempotency/` | Expirar após 1 dia | Delete automático |
| `torrents/` | Expirar após 7 dias | Delete automático |
| `downloads/completed/` | Transição após 30 dias sem acesso | Intelligent-Tiering Archive |
| `queue/` | Sem regra | Mantido indefinidamente |

**Bloqueio de acesso público:** Habilitado. Nenhum objeto é público. Todo acesso é via Pre-signed URL com TTL máximo de 7 dias.

---

## 6. Contratos de API

### 6.1 Autenticação

```
POST /auth/login
Body: { "password": "string" }
Response 200: { "token": "JWT", "expiresAt": "ISO 8601" }
Response 401: { "error": "invalid_credentials" }
```

### 6.2 Downloads — CRUD

```
POST /downloads
Headers: Authorization: Bearer {JWT}
Body (magnet): {
  "clientRequestId": "uuid",
  "type": "magnet",
  "magnetLink": "magnet:?xt=...",
  "name": "Nome opcional"
}
Body (torrent file): {
  "clientRequestId": "uuid",
  "type": "torrent_file",
  "torrentS3Key": "torrents/{id}.torrent",
  "name": "Nome opcional"
}
Response 201: { "download": {DownloadObject} }
Response 200: { "download": {DownloadObject} }  ← se clientRequestId já existe (idempotente)
Response 400: { "error": "invalid_magnet_link | file_too_large | invalid_torrent" }
Response 409: { "error": "disk_space_insufficient", "availableBytes": 5368709120 }

GET /downloads
Query: ?status=pending|processing|completed|cancelled&page=1&limit=50
Response 200: { "items": [{DownloadObject}], "total": 42, "page": 1 }

GET /downloads/{id}
Response 200: { "download": {DownloadObject} }
Response 404: { "error": "not_found" }

PATCH /downloads/{id}
Body: { "name": "Novo nome" }
Response 200: { "download": {DownloadObject} }

DELETE /downloads/{id}
Response 204: (sem body)
Efeito: Remove JSON do prefixo S3 correspondente. Se completed, remove também o arquivo em downloads/completed/{id}/.

POST /downloads/{id}/cancel
Response 200: { "download": {DownloadObject} }
Nota: Se status=processing, seta flag cancelRequested=true no JSON. Worker detecta e para o torrent.

POST /downloads/{id}/requeue
Body: {}  ← apenas para status=cancelled
Response 200: { "download": {DownloadObject} }
Efeito: Move JSON de cancelled/ para pending/, reseta retryCount e errorMessage, liga EC2 se necessário.
```

### 6.3 Upload de Arquivo .torrent

```
POST /downloads/upload-url
Body: { "filename": "ubuntu.torrent", "sizeBytes": 45000 }
Response 200: {
  "uploadUrl": "https://s3.amazonaws.com/...",  ← Pre-signed PUT URL (TTL: 5min)
  "torrentS3Key": "torrents/{uuid}.torrent"
}
Validações:
  - Extensão deve ser .torrent
  - sizeBytes máximo: 1 MB
  - Content-Type esperado: application/x-bittorrent
```

### 6.4 Pre-signed URL para Download

```
POST /downloads/{id}/download-url
Body: { "expiresIn": 3600 }  ← segundos; máximo: 604800 (7 dias)
Response 200: {
  "url": "https://s3.amazonaws.com/...",
  "filename": "ubuntu-22.04.iso",
  "sizeBytes": 1073741824,
  "expiresAt": "ISO 8601",
  "estimatedTransferCostUSD": 0.096
}
Response 400: { "error": "download_not_completed" }
```

### 6.5 Status da Infraestrutura

```
GET /status
Response 200: {
  "worker": {
    "status": "running | stopped | starting | stopping",
    "instanceId": "i-0abc123",
    "instanceType": "t3.medium",
    "launchedAt": "ISO 8601 | null",
    "uptimeSeconds": 3600
  },
  "queue": {
    "pending": 2,
    "processing": 1,
    "completed": 15,
    "cancelled": 3
  },
  "index": {
    "updatedAt": "ISO 8601",
    "isStale": false
  }
}
```

---

## 7. Protocolo de Consistência do S3

### 7.1 Transição de Estado com ETag Condicional

Toda transição de estado de um item segue o protocolo **COPY → VALIDATE → DELETE** com verificação de ETag para garantir atomicidade:

```python
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

def transition_state(bucket, item_id, from_status, to_status, worker_id, updates):
    source_key = f"queue/{from_status}/{item_id}.json"
    dest_key   = f"queue/{to_status}/{item_id}.json"

    # 1. GET com ETag
    response = s3.get_object(Bucket=bucket, Key=source_key)
    etag = response['ETag']
    item = json.loads(response['Body'].read())

    # 2. VALIDATE
    if item.get('workerId') is not None and item.get('workerId') != worker_id:
        raise Exception(f"Lock conflict: item owned by {item['workerId']}")
    if item.get('status') != from_status:
        raise Exception(f"State mismatch: expected {from_status}, got {item['status']}")

    # 3. Preparar novo estado
    item.update(updates)
    item['status'] = to_status
    item['workerId'] = worker_id if to_status == 'processing' else None
    item['version'] = item.get('version', 0) + 1
    item['updatedAt'] = datetime.utcnow().isoformat() + 'Z'

    # 4. COPY condicional com CopySourceIfMatch (atomicidade garantida)
    try:
        s3.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': source_key},
            Key=dest_key,
            CopySourceIfMatch=etag,
            MetadataDirective='REPLACE',
            Metadata={'status': to_status, 'version': str(item['version'])}
        )
        # Sobrescrever com o JSON atualizado após o COPY
        s3.put_object(
            Bucket=bucket,
            Key=dest_key,
            Body=json.dumps(item),
            ContentType='application/json'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'PreconditionFailed':
            return None  # Outro processo ganhou a corrida — abortar silenciosamente
        raise

    # 5. DELETE fonte (apenas após COPY bem-sucedido)
    s3.delete_object(Bucket=bucket, Key=source_key)

    # 6. Atualizar index.json
    update_index(bucket, item)

    return item
```

### 7.2 Atualização do index.json

O `index.json` é atualizado após cada transição de estado bem-sucedida. Em caso de falha na atualização do índice, o estado do item individual permanece correto (o índice é derivado, não autoritativo). O frontend detecta staleness pelo campo `updatedAt` e faz fallback para LIST.

---

## 8. Worker: Lógica de Execução

### 8.1 Loop Principal

```python
POLL_INTERVAL_SECONDS = 60
IDLE_CYCLES_BEFORE_SHUTDOWN = 3
DISK_CRITICAL_THRESHOLD_GB = 2
DISK_RESUME_THRESHOLD_GB = 5
MAX_TORRENT_SIZE_GB = int(os.environ.get('MAX_TORRENT_SIZE_GB', 50))

def main_loop():
    idle_cycles = 0
    worker_id = get_instance_id()  # IMDSv2

    while True:
        check_disk_space_and_pause_if_critical()
        process_cancellation_requests(worker_id)
        pending_item = get_next_pending_item(bucket)

        if pending_item:
            idle_cycles = 0
            process_item(pending_item, worker_id)
        else:
            idle_cycles += 1
            if idle_cycles >= IDLE_CYCLES_BEFORE_SHUTDOWN:
                graceful_shutdown(worker_id)
                break

        time.sleep(POLL_INTERVAL_SECONDS)
```

### 8.2 Monitoramento de Progresso

```python
PROGRESS_UPDATE_MIN_DELTA_PERCENT = 2.0
PROGRESS_UPDATE_MAX_INTERVAL_SECONDS = 30

def monitor_download(item, transmission_id, worker_id):
    last_update_time = 0
    last_progress = 0

    while True:
        current = get_item(bucket, item['id'], 'processing')
        if current.get('cancelRequested'):
            transmission_rpc('torrent-stop', transmission_id)
            transmission_rpc('torrent-remove', transmission_id, delete_data=True)
            transition_state(bucket, item['id'], 'processing', 'cancelled', worker_id, {
                'cancelledAt': datetime.utcnow().isoformat() + 'Z',
                'errorMessage': 'cancelled_by_user'
            })
            return

        stats = transmission_rpc('torrent-get', transmission_id)
        progress = stats['percentDone'] * 100
        now = time.time()
        delta_progress = abs(progress - last_progress)
        elapsed = now - last_update_time

        if delta_progress >= PROGRESS_UPDATE_MIN_DELTA_PERCENT or elapsed >= PROGRESS_UPDATE_MAX_INTERVAL_SECONDS:
            update_item_fields(bucket, item['id'], 'processing', {
                'progressPercent': round(progress, 1),
                'downloadSpeedBps': stats['rateDownload'],
                'uploadSpeedBps': stats['rateUpload'],
                'eta': stats['eta'],
                'sizeBytesDownloaded': int(stats['sizeWhenDone'] * stats['percentDone'])
            })
            last_update_time = now
            last_progress = progress

        if stats['status'] == 6:  # seeding = download completo
            finalize_download(item, transmission_id, worker_id)
            return

        if stats['error'] != 0:
            handle_download_error(item, stats['errorString'], worker_id)
            return

        time.sleep(10)
```

### 8.3 Finalização e Sync para S3

```python
def finalize_download(item, transmission_id, worker_id):
    local_path = f"/data/downloads/{item['name']}"
    s3_dest = f"s3://seedbox-{account_id}/downloads/completed/{item['id']}/"

    result = subprocess.run([
        'rclone', 'move', local_path, s3_dest,
        '--s3-storage-class', 'INTELLIGENT_TIERING',
        '--transfers', '4',
        '--checksum',
        '--progress'
    ], capture_output=True, text=True)

    if result.returncode != 0:
        handle_download_error(item, f"rclone_failed: {result.stderr}", worker_id)
        return

    s3_size = get_s3_object_size(f"downloads/completed/{item['id']}/")
    transmission_rpc('torrent-remove', transmission_id, delete_data=False)

    transition_state(bucket, item['id'], 'processing', 'completed', worker_id, {
        'completedAt': datetime.utcnow().isoformat() + 'Z',
        'progressPercent': 100.0,
        'workerId': None,
        's3Key': f"downloads/completed/{item['id']}/",
        's3SizeBytes': s3_size,
        'errorMessage': None
    })
```

---

## 9. Gerenciamento de Disco

### 9.1 Verificação Antes de Iniciar

```python
def check_disk_before_start(item):
    stat = shutil.disk_usage('/data')
    free_gb = stat.free / 1e9
    estimated_size_gb = (item.get('sizeBytes') or 0) / 1e9
    required_gb = max(estimated_size_gb * 1.1, 5.0)

    if free_gb < required_gb:
        return False, f"disk_space_insufficient: {free_gb:.1f} GB free, {required_gb:.1f} GB required"
    return True, None
```

### 9.2 Monitoramento Contínuo

```python
def check_disk_space_and_pause_if_critical():
    stat = shutil.disk_usage('/data')
    free_gb = stat.free / 1e9

    if free_gb < DISK_CRITICAL_THRESHOLD_GB:
        transmission_rpc('torrent-stop', ids=[])  # Pausa todos
        mark_all_processing_as_disk_critical()
    elif free_gb >= DISK_RESUME_THRESHOLD_GB:
        if is_paused_for_disk():
            transmission_rpc('torrent-start', ids=[])
            clear_disk_critical_error_messages()
```

**Thresholds configuráveis:**

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DISK_CRITICAL_THRESHOLD_GB` | 2 | Pausa todos os torrents abaixo deste valor |
| `DISK_RESUME_THRESHOLD_GB` | 5 | Retoma torrents acima deste valor |
| `MAX_TORRENT_SIZE_GB` | 50 | Tamanho máximo por torrent |

---

## 10. Retry Policy

### 10.1 Classificação de Erros

| Categoria | Exemplos | Comportamento |
|-----------|---------|---------------|
| **Temporário** | Timeout de rede, falha de conectividade, S3 throttling | Retry com backoff exponencial |
| **Definitivo** | Torrent não encontrado, hash inválido, arquivo corrompido | Cancelamento imediato |
| **Operacional** | Disco cheio, tamanho excede limite | Volta para `pending`; não consome retry |

### 10.2 Backoff Exponencial

```python
RETRY_INTERVALS_SECONDS = [60, 300, 900]  # 1min, 5min, 15min

def handle_download_error(item, error_string, worker_id):
    is_definitive = classify_error(error_string) == 'definitive'

    if is_definitive or item.get('retryCount', 0) >= len(RETRY_INTERVALS_SECONDS):
        transition_state(bucket, item['id'], 'processing', 'cancelled', worker_id, {
            'cancelledAt': datetime.utcnow().isoformat() + 'Z',
            'errorMessage': error_string
        })
    else:
        retry_count = item.get('retryCount', 0)
        retry_after = (datetime.utcnow() + timedelta(seconds=RETRY_INTERVALS_SECONDS[retry_count])).isoformat() + 'Z'
        transition_state(bucket, item['id'], 'processing', 'pending', worker_id, {
            'retryCount': retry_count + 1,
            'retryAfter': retry_after,
            'errorMessage': error_string,
            'workerId': None
        })
```

---

## 11. Idempotência

```python
def create_download(event):
    body = json.loads(event['body'])
    client_request_id = body['clientRequestId']
    idempotency_key = f"idempotency/{client_request_id}"

    # Verificar se já existe
    try:
        existing = s3.get_object(Bucket=bucket, Key=idempotency_key)
        item_id = json.loads(existing['Body'].read())['itemId']
        if item_id:
            return get_download_by_id(item_id)
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchKey':
            raise

    # Criar item
    item = build_download_item(body)
    s3.put_object(
        Bucket=bucket,
        Key=f"queue/pending/{item['id']}.json",
        Body=json.dumps(item),
        ContentType='application/json'
    )

    # Registrar idempotência
    s3.put_object(
        Bucket=bucket,
        Key=idempotency_key,
        Body=json.dumps({'itemId': item['id'], 'createdAt': item['createdAt']}),
        ContentType='application/json'
    )

    trigger_worker_if_stopped()
    return item
```

**Lifecycle Rule para limpeza automática (TTL: 24h):**

```json
{
  "Rules": [{
    "ID": "expire-idempotency-keys",
    "Filter": { "Prefix": "idempotency/" },
    "Status": "Enabled",
    "Expiration": { "Days": 1 }
  }]
}
```

---

## 12. Autenticação e Segurança

### 12.1 JWT

```python
import jwt, bcrypt

def login(password: str) -> str:
    secret = get_secret('seedbox/auth')
    if not bcrypt.checkpw(password.encode(), secret['passwordHash'].encode()):
        raise UnauthorizedException("invalid_credentials")

    payload = {
        'sub': 'seedbox-owner',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24),
        'jti': str(uuid.uuid4())
    }
    return jwt.encode(payload, secret['jwtSecret'], algorithm='HS256')
```

### 12.2 Segredos no Secrets Manager

| Secret | Conteúdo |
|--------|---------|
| `seedbox/auth` | `{ "passwordHash": "$2b$...", "jwtSecret": "..." }` |
| `seedbox/transmission` | `{ "username": "seedbox", "password": "..." }` |

### 12.3 Políticas de Segurança

**API Gateway:**
- Rate limiting: 100 requisições/minuto por IP
- Throttling burst: 200 requisições
- CORS: `Access-Control-Allow-Origin: https://seedbox.seudominio.com` (apenas o domínio Cloudflare)

**Cloudflare (camada adicional de segurança):**
- Rate limit adicional: > 200 req/min por IP no subdomínio `api.seedbox` → Block por 5 minutos
- Bot Fight Mode: habilitado (gratuito)
- SSL Mode: Full para frontend S3, Full (strict) para API Gateway
- HSTS: habilitado via Cloudflare (max-age=31536000)

**S3 Bucket Policy (frontend):**
- Acesso público permitido apenas dos IPs da Cloudflare (lista completa na seção 5.1)
- Nenhum acesso direto ao endpoint S3 sem passar pela Cloudflare

**EC2 IAM Role (mínimo privilégio):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::seedbox-{account-id}/queue/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::seedbox-{account-id}/downloads/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::seedbox-{account-id}",
      "Condition": {
        "StringLike": { "s3:prefix": ["queue/*", "downloads/*", "torrents/*"] }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ec2:StopInstances",
      "Resource": "*",
      "Condition": {
        "StringEquals": { "ec2:ResourceTag/Name": "seedbox-worker" }
      }
    },
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:*:*:secret:seedbox/*"
    }
  ]
}
```

---

## 13. Pre-signed URLs

```python
from boto3 import client
from botocore.config import Config

s3_presign = client('s3', config=Config(signature_version='s3v4'))

def generate_download_url(item_id: str, expires_in: int = 3600) -> dict:
    item = get_download_by_id(item_id)

    if item['status'] != 'completed':
        raise BadRequestException("download_not_completed")

    if expires_in > 604800:
        expires_in = 604800

    url = s3_presign.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket,
            'Key': item['s3Key'],
            'ResponseContentDisposition': f'attachment; filename="{item["name"]}"'
        },
        ExpiresIn=expires_in
    )

    size_bytes = item.get('s3SizeBytes', 0)
    return {
        'url': url,
        'filename': item['name'],
        'sizeBytes': size_bytes,
        'expiresAt': (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + 'Z',
        'estimatedTransferCostUSD': round((size_bytes / 1e9) * 0.09, 4)
    }
```

> **Nota importante:** As Pre-signed URLs apontam diretamente para o S3 (`s3.amazonaws.com`), **não** passam pela Cloudflare. Isso é intencional: o download de arquivos grandes deve ir direto do S3 para o usuário, sem custo de transferência adicional e sem sobrecarregar o proxy Cloudflare.

---

## 14. Infraestrutura como Código (IaC)

**Ferramenta recomendada:** AWS CDK (Python) ou Terraform.

**Recursos AWS a provisionar:**

| Recurso | Tipo | Configuração Principal |
|---------|------|----------------------|
| `SeedboxBucket` | S3 Bucket | Block Public Access, Lifecycle Rules, Intelligent-Tiering |
| `SeedboxFrontendBucket` | S3 Bucket | Website hosting, Bucket Policy restrita a IPs Cloudflare |
| `SeedboxApi` | API Gateway HTTP API | Throttle 100 req/min, CORS restrito ao domínio Cloudflare |
| `SeedboxApiLambda` | Lambda Function | Python 3.12, 256 MB, 30s timeout |
| `SeedboxAuthorizerLambda` | Lambda Function | Python 3.12, 128 MB, 5s timeout |
| `SeedboxWorkerTriggerLambda` | Lambda Function | Python 3.12, 128 MB, 10s timeout |
| `SeedboxWorkerSG` | Security Group | Inbound: nenhum; Outbound: 443 (HTTPS), 6881-6889 (BitTorrent) |
| `SeedboxWorkerRole` | IAM Role | Política de mínimo privilégio (seção 12.3) |
| `SeedboxSpotTemplate` | EC2 Launch Template | t3.medium, Spot, User Data, IAM Role, SG |
| `SeedboxAuthSecret` | Secrets Manager Secret | passwordHash + jwtSecret |
| `SeedboxTransmissionSecret` | Secrets Manager Secret | username + password |
| `SeedboxAlarms` | CloudWatch Alarms | Disco > 80%, Lambda errors > 5/min |

**Recursos Cloudflare a configurar (manual ou via Terraform `cloudflare` provider):**

| Recurso | Tipo | Configuração |
|---------|------|-------------|
| DNS Record `seedbox` | CNAME Proxiado | Aponta para S3 Website Endpoint |
| DNS Record `api.seedbox` | CNAME Proxiado | Aponta para API Gateway URL |
| SSL/TLS Mode | Configuração | Full para frontend, Full (strict) para API |
| Cache Rule — assets | Page Rule | Cache Everything, TTL 1 ano para `/assets/*` |
| Cache Rule — index.html | Page Rule | Bypass Cache para `/index.html` |
| Cache Rule — API | Page Rule | Bypass Cache para `api.seedbox/*` |
| Rate Limit | Firewall Rule | > 200 req/min em `api.seedbox/*` → Block 5 min |
| Bot Fight Mode | Security | Habilitado |

**Ordem de criação:**

1. IAM Roles e Policies
2. Secrets Manager
3. S3 Buckets + Lifecycle Rules
4. Security Groups
5. EC2 Launch Template
6. Lambda Functions
7. API Gateway
8. Deploy do Frontend no S3
9. Configuração DNS e regras na Cloudflare

> **Nota:** A etapa 9 (Cloudflare) deve ser a última porque depende das URLs finais do S3 Website Endpoint e do API Gateway, que só são conhecidas após as etapas anteriores.

---

## 15. Variáveis de Ambiente e Configuração

### Lambda Functions

| Variável | Descrição |
|----------|-----------|
| `S3_BUCKET` | Nome do bucket principal |
| `EC2_INSTANCE_ID` | ID da instância EC2 worker |
| `EC2_REGION` | Região AWS |
| `AUTH_SECRET_NAME` | Nome do secret no Secrets Manager |
| `TRANSMISSION_SECRET_NAME` | Nome do secret do Transmission |
| `MAX_TORRENT_SIZE_GB` | Limite de tamanho por torrent (padrão: 50) |
| `PRESIGNED_URL_MAX_EXPIRY` | TTL máximo de Pre-signed URLs em segundos (padrão: 604800) |
| `ALLOWED_ORIGIN` | Domínio Cloudflare do frontend para CORS (ex: `https://seedbox.seudominio.com`) |

### Worker EC2

| Variável | Descrição |
|----------|-----------|
| `S3_BUCKET` | Nome do bucket principal |
| `AWS_REGION` | Região AWS |
| `TRANSMISSION_SECRET_NAME` | Nome do secret do Transmission |
| `POLL_INTERVAL_SECONDS` | Intervalo do loop principal (padrão: 60) |
| `IDLE_CYCLES_BEFORE_SHUTDOWN` | Ciclos ociosos antes do shutdown (padrão: 3) |
| `DISK_CRITICAL_THRESHOLD_GB` | Threshold de disco crítico (padrão: 2) |
| `DISK_RESUME_THRESHOLD_GB` | Threshold de retomada (padrão: 5) |
| `MAX_TORRENT_SIZE_GB` | Tamanho máximo por torrent (padrão: 50) |

---

## 16. Testes de Falha Controlada

Os seguintes cenários **devem ser testados antes de produção**:

| # | Cenário | Como simular | Comportamento esperado |
|---|---------|-------------|----------------------|
| 1 | **Disco cheio** | Criar arquivo grande em `/data` até encher | Worker pausa torrents, registra `disk_space_critical`, retoma ao liberar espaço |
| 2 | **Interrupção de EC2** | Enviar `SIGTERM` ao processo worker | Worker completa ciclo atual, move itens `processing` de volta para `pending`, para graciosamente |
| 3 | **Falha de PUT no S3** | Revogar permissão S3 temporariamente | Worker classifica como erro temporário, aplica backoff, retenta |
| 4 | **Retry forçado** | Submeter magnet link inválido | Worker classifica como erro definitivo, move para `cancelled` sem retry |
| 5 | **Race de enqueue + shutdown** | Submeter torrent enquanto EC2 está parando | Lambda detecta estado `stopping`, aguarda 30s e tenta ligar novamente |
| 6 | **Duplo clique (idempotência)** | Enviar mesma requisição 2x com mesmo `clientRequestId` | Segunda requisição retorna o item original sem criar duplicata |
| 7 | **index.json stale** | Parar EC2 abruptamente sem atualizar índice | Frontend detecta `updatedAt` > 2min, faz fallback para LIST direto |
| 8 | **Cancelamento durante sync S3** | Cancelar item enquanto rclone está rodando | Worker mata processo rclone, remove arquivo parcial do S3, move para `cancelled` |
| 9 | **Cloudflare bloqueando IPs** | Acessar S3 Website Endpoint diretamente | Acesso negado pela Bucket Policy (apenas IPs Cloudflare permitidos) |
| 10 | **Expiração de Pre-signed URL** | Aguardar TTL expirar e tentar download | S3 retorna 403; frontend exibe mensagem e oferece regenerar o link |

---

## 17. Observabilidade e Alarmes

### 17.1 Logs

| Log Group | Fonte | Retenção |
|-----------|-------|---------|
| `/aws/lambda/seedbox-api` | Lambda API | 7 dias |
| `/aws/lambda/seedbox-authorizer` | Lambda Authorizer | 7 dias |
| `/seedbox/worker` | Worker EC2 (via CloudWatch Agent) | 14 dias |

### 17.2 Alarmes CloudWatch

| Alarme | Métrica | Threshold | Ação |
|--------|---------|-----------|------|
| `SeedboxLambdaErrors` | Lambda Errors | > 5 em 5 min | SNS → Email |
| `SeedboxWorkerDisk` | Disk Used % | > 80% | SNS → Email |
| `SeedboxWorkerCPU` | CPU Utilization | > 90% por 10 min | SNS → Email |
| `SeedboxApiLatency` | API Gateway P99 | > 5000ms | SNS → Email |
| `SeedboxSpotInterruption` | EC2 Spot Interruption | Qualquer | SNS → Email |

### 17.3 Dashboard CloudWatch

Recomenda-se criar um dashboard com os seguintes widgets:
- Downloads por status (últimas 24h)
- Tempo médio de download por GB
- Custo estimado de transferência S3 (últimos 30 dias)
- Uptime da EC2 worker (últimos 7 dias)
- Erros Lambda por tipo (últimas 24h)

---

## 18. Estimativa de Custo

Estimativa mensal para uso moderado (10–20 torrents/mês, ~500 GB armazenados):

| Componente | v1.4 (CloudFront) | v1.5 (Cloudflare) | Observações |
|-----------|:-----------------:|:-----------------:|-------------|
| EC2 Spot `t3.medium` | US$ 3–8 | US$ 3–8 | ~20-50h/mês; US$ 0,015/h |
| S3 Armazenamento (500 GB) | US$ 2–6 | US$ 2–6 | Intelligent-Tiering |
| S3 Requisições | < US$ 0,10 | < US$ 0,10 | Volume baixo |
| Lambda | < US$ 0,50 | < US$ 0,50 | Dentro do free tier |
| API Gateway | < US$ 0,50 | < US$ 0,50 | US$ 1/M requisições |
| **CloudFront** | **< US$ 0,10** | **US$ 0,00** | **Eliminado** |
| **ACM (certificado)** | **US$ 0,00** | **US$ 0,00** | Gratuito em ambos |
| Secrets Manager | US$ 0,80 | US$ 0,80 | 2 secrets × US$ 0,40 |
| CloudWatch | < US$ 0,50 | < US$ 0,50 | Logs + alarmes |
| **Cloudflare** | **—** | **US$ 0,00** | **Plano Free** |
| **Total estimado** | **US$ 7–16/mês** | **US$ 6–15/mês** | Economia de ~US$ 0,10–1,00/mês |

> **Nota sobre a economia:** O impacto financeiro direto da substituição do CloudFront pela Cloudflare é pequeno para este volume de tráfego (frontend leve). O benefício real está na **eliminação de complexidade** (sem OAC, sem ACM, sem distribuição CloudFront para gerenciar) e nos **benefícios adicionais gratuitos** da Cloudflare (WAF, DDoS, analytics de tráfego, Bot Fight Mode) que no CloudFront exigiriam o AWS Shield Advanced (US$ 3.000/mês).

**Custo de transferência de dados (variável):**
- Download de arquivos do S3 para fora da AWS: US$ 0,09/GB (Pre-signed URL vai direto do S3, não passa pela Cloudflare)
- Exemplo: 100 GB baixados pelo usuário = US$ 9,00 adicionais

---

## 19. Roadmap

### v1.5 — Versão atual
- Cloudflare como CDN, proxy reverso e SSL (esta versão)
- Todos os itens do consenso v1.4 implementados

### v1.6 — Segurança Aprimorada
- Migrar autenticação de JWT manual para Amazon Cognito com refresh token e revogação real
- Implementar MFA (TOTP) para o usuário único
- Adicionar CloudTrail para auditoria de todas as operações S3 e Lambda
- Script automatizado para atualizar IPs da Cloudflare na Bucket Policy mensalmente

### v2.0 — Escalabilidade Horizontal
- Substituir fila S3 por Amazon SQS para suporte a múltiplos workers simultâneos
- Migrar worker para Amazon ECS Fargate (sem gerenciamento de instância)
- Adicionar suporte a múltiplos usuários com isolamento de dados por prefixo S3
- Implementar notificações via SNS/SES quando download concluir

### v2.5 — Experiência Avançada
- Streaming de arquivos de vídeo diretamente do S3 via Cloudflare Stream (alternativa ao CloudFront Signed Cookies)
- Agendamento de downloads (iniciar em horário específico)
- Relatório mensal de custo por download
- API pública documentada (OpenAPI) para integração com clientes torrent externos

---

*Documento elaborado com base no consenso técnico entre Manus AI e GPT-4o. Status: Architecture Approved — v1.5 Ready for Build.*
