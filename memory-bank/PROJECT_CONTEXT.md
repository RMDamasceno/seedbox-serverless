# Project Context — Seedbox Serverless AWS

## Visão Geral

- **Nome:** Seedbox Serverless AWS
- **Versão:** 1.0.0
- **Status:** Desenvolvimento Completo — Todas as Fases Concluídas
- **Data de Início:** 2026-04-22
- **Desenvolvedor:** Rafael Damasceno

## Objetivos

1. Sistema de download via torrent serverless na AWS
2. Custo zero quando ocioso (sem componentes de custo fixo)
3. Segurança e idempotência em todas as operações
4. Documentação automática e changelog detalhado

## Restrições

- Usuário único (v1.0)
- Tamanho máximo por torrent: 50 GB
- Disco worker: 200 GB gp3
- Timeout Lambda: 30 segundos
- Sem banco de dados relacional — estado via S3 JSON

## Stack

- **Frontend:** React 18 + TypeScript + Vite + TailwindCSS
- **CDN/SSL:** Cloudflare (plano Free)
- **API:** Lambda Python 3.12 + API Gateway HTTP
- **Worker:** EC2 Spot t3.medium + Transmission + rclone
- **Estado:** S3 JSON com ETag condicional
- **IaC:** Terraform

## Fases de Desenvolvimento

| Fase | Foco | Status |
|------|------|--------|
| 1 | Infraestrutura Base (IaC) | ✅ Concluída |
| 2 | Backend e Estado (Lambda + S3) | ✅ Concluída |
| 3 | Worker EC2 e Integração | ✅ Concluída |
| 4 | Frontend e Cloudflare | ✅ Concluída |
| 5 | Testes e Validação Final | ✅ Concluída |
