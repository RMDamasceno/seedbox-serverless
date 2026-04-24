# Seedbox Serverless AWS

Sistema de download via torrent baseado em serviços gerenciados da AWS, projetado para uso pessoal com custo variável e zero de operação quando ocioso.

## Visão Geral

O usuário submete um magnet link ou arquivo `.torrent` via interface web. A infraestrutura de computação é ligada automaticamente, o download é executado, o arquivo é movido para o S3 e a instância é desligada. Custo de computação zero quando não há downloads ativos.

## Stack Tecnológico

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS |
| CDN/SSL | Cloudflare (plano Free) |
| API | AWS Lambda (Python 3.12) + API Gateway HTTP |
| Worker | EC2 Spot (t3.medium) + Transmission |
| Armazenamento | Amazon S3 Intelligent-Tiering |
| Estado | Arquivos JSON no S3 (sem banco de dados) |
| Autenticação | JWT + AWS Secrets Manager |
| IaC | Terraform |

## Arquitetura

```
Usuário → Cloudflare (CDN/SSL/WAF) → S3 (Frontend React)
                                    → API Gateway → Lambda → S3 (Estado JSON)
                                                           → EC2 Spot (Worker)
                                                              → Transmission (BitTorrent)
                                                              → rclone → S3 (Arquivos)
```

## Estrutura do Projeto

```
seedbox-serverless/
├── backend/
│   ├── lambda/
│   │   ├── api/            # Lambda principal (CRUD, status, pre-signed URLs)
│   │   ├── authorizer/     # Lambda Authorizer (JWT)
│   │   └── worker-trigger/ # Lambda trigger EC2
│   └── worker/
│       ├── scripts/        # Worker Python (polling, monitor, disk)
│       └── config/         # Configuração do Transmission
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── styles/
│   └── public/
├── iac/
│   └── terraform/
│       ├── modules/        # lambda, ec2, s3, iam
│       └── environments/   # dev, prod
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── api/
│   ├── components/
│   ├── infrastructure/
│   ├── security/
│   ├── testing/
│   └── templates/
├── memory-bank/
│   └── CHAT_HISTORY_SUMMARIES/
└── scripts/
    ├── deploy/
    ├── setup/
    └── monitoring/
```

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- Terraform 1.5+
- AWS CLI v2 configurado
- Conta Cloudflare (plano Free)
- Domínio próprio configurado na Cloudflare

## Setup Local

```bash
# Backend (Python)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Frontend (Node)
cd frontend
npm install
npm run dev
```

## Fases de Desenvolvimento

| Fase | Foco | Status |
|------|------|--------|
| 1 | Infraestrutura Base (IaC) | ✅ Concluída |
| 2 | Backend e Estado (Lambda + S3) | ✅ Concluída |
| 3 | Worker EC2 e Integração | ✅ Concluída |
| 4 | Frontend e Cloudflare | ✅ Concluída |

## Documentação

- [Documento Técnico v1.5](.amazonq/rules/EscopoTecnicoArquitetura.md)
- [Changelog](docs/CHANGELOG.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Referência da API](docs/API_REFERENCE.md)

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
