# Configuração Cloudflare — Seedbox Serverless AWS

## Pré-requisitos

- Domínio próprio com nameservers apontando para Cloudflare
- Plano Free (suficiente)
- Outputs do Terraform: `frontend_website_endpoint` e `api_gateway_url`

## 1. DNS Records

| Tipo | Nome | Conteúdo | Proxy |
|------|------|---------|-------|
| CNAME | `seedbox` | `seedbox-frontend-{account-id}.s3-website-us-east-1.amazonaws.com` | ✅ Proxiado |
| CNAME | `api.seedbox` | `xxxx.execute-api.us-east-1.amazonaws.com` | ✅ Proxiado |

## 2. SSL/TLS

Em **SSL/TLS → Overview**:
- Frontend (`seedbox.dominio.com`): **Full** (S3 Website usa HTTP)
- API (`api.seedbox.dominio.com`): **Full (strict)** (API Gateway tem certificado válido)

Em **SSL/TLS → Edge Certificates**:
- HSTS: Habilitado (max-age=31536000, includeSubDomains)

## 3. Cache Rules

Em **Caching → Cache Rules**, criar regras na ordem:

1. **API — Bypass Cache**
   - Hostname equals `api.seedbox.dominio.com`
   - Cache eligibility: Bypass cache

2. **index.html — Bypass Cache**
   - Hostname equals `seedbox.dominio.com` AND URI Path equals `/index.html`
   - Cache eligibility: Bypass cache

3. **Assets — Cache 1 ano**
   - Hostname equals `seedbox.dominio.com` AND URI Path starts with `/assets/`
   - Cache eligibility: Eligible for cache
   - Edge TTL: 1 year

## 4. Security

Em **Security → WAF**:
- Bot Fight Mode: **Habilitado**

Em **Security → WAF → Rate limiting rules**:
- Rule: `api.seedbox.dominio.com/*` → 200 requests/minute → Block 5 minutes

## 5. Validação

```bash
# Frontend deve retornar 200
curl -I https://seedbox.dominio.com

# API deve retornar 401 (sem token)
curl -I https://api.seedbox.dominio.com/status

# Acesso direto ao S3 deve retornar 403
curl -I http://seedbox-frontend-{account-id}.s3-website-us-east-1.amazonaws.com
```
