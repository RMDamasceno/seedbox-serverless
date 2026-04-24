# Recursos AWS — Seedbox Serverless

Lista de recursos provisionados via Terraform.

## S3

| Recurso | Nome | Configuração |
|---------|------|-------------|
| Bucket dados | `seedbox-{account-id}` | Block Public Access, SSE-S3, Lifecycle (idempotency 1d, torrents 7d, downloads IT 30d) |
| Bucket frontend | `seedbox-frontend-{account-id}` | Website hosting, Bucket Policy (Cloudflare IPs only) |

## IAM

| Recurso | Nome | Escopo |
|---------|------|--------|
| Role | `seedbox-api-lambda-role` | S3 queue/idempotency/torrents/downloads, Secrets Manager, EC2 describe/start, Lambda invoke |
| Role | `seedbox-authorizer-lambda-role` | Secrets Manager (seedbox/auth) |
| Role | `seedbox-worker-trigger-lambda-role` | EC2 start/stop/describe |
| Role | `seedbox-worker-ec2-role` | S3 queue/downloads/torrents, EC2 stop self, Secrets Manager (transmission) |
| Instance Profile | `seedbox-worker-instance-profile` | Vinculado à role EC2 |

## Secrets Manager

| Secret | Conteúdo |
|--------|---------|
| `seedbox/auth` | passwordHash, jwtSecret |
| `seedbox/transmission` | username, password |

## EC2

| Recurso | Configuração |
|---------|-------------|
| Security Group | Inbound: nenhum. Outbound: 443, 6881-6889 TCP/UDP, 53 UDP, 80 TCP |
| Launch Template | t3.medium Spot, 200GB gp3, IMDSv2, Amazon Linux 2023 |

## Lambda

| Função | Runtime | Memória | Timeout |
|--------|---------|---------|---------|
| `seedbox-api` | Python 3.12 | 256 MB | 30s |
| `seedbox-authorizer` | Python 3.12 | 128 MB | 5s |
| `seedbox-worker-trigger` | Python 3.12 | 128 MB | 10s |

## API Gateway

| Recurso | Configuração |
|---------|-------------|
| HTTP API | 11 rotas, CORS restrito, throttle 100 burst / 50 rate |
| Authorizer | Lambda REQUEST, TTL 300s |
