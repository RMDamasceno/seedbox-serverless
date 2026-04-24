# Decision Log

## ADR-001: Usar S3 JSON em vez de Banco de Dados Relacional

**Data:** 2026-04-22
**Status:** Aceito

**Decisão:** Utilizar S3 JSON para armazenar estado de downloads.

**Justificativa:**
- Custo desprezível para volume baixo de operações
- Sem componente de custo fixo (DynamoDB/RDS)
- Idempotência via ETag condicional
- Simplicidade operacional

**Consequências:**
- (+) Zero custo quando ocioso
- (+) Sem gerenciamento de conexões
- (-) Sem queries complexas
- (-) Requer locking manual via ETag

---

## ADR-002: Usar Cloudflare em vez de CloudFront

**Data:** 2026-04-22
**Status:** Aceito

**Decisão:** Cloudflare (plano Free) como CDN, proxy reverso e SSL.

**Justificativa:**
- Plano Free suficiente para todos os requisitos
- WAF, DDoS e Bot Fight Mode inclusos gratuitamente
- Elimina custos de CloudFront e ACM

---

## ADR-003: Terraform como ferramenta de IaC

**Data:** 2026-04-22
**Status:** Aceito

**Decisão:** Usar Terraform para provisionar toda a infraestrutura AWS.

**Justificativa:**
- Reprodutibilidade total do ambiente
- Módulos reutilizáveis por componente (lambda, ec2, s3, iam)
- Separação de ambientes (dev/prod)

---

## ADR-004: EC2 Spot para Worker

**Data:** 2026-04-22
**Status:** Aceito

**Decisão:** Usar instância EC2 Spot t3.medium para o worker de download.

**Justificativa:**
- Até 90% mais barato que On-Demand
- Aceitável para workload tolerante a interrupções
- Graceful shutdown via metadata endpoint
