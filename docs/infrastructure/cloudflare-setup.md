# Configuração Cloudflare — Seedbox Serverless AWS

**Domínio:** rafael.damasceno.nom.br
**Frontend:** seedbox.rafael.damasceno.nom.br
**API:** api-seedbox.rafael.damasceno.nom.br

## 1. DNS Records

No painel Cloudflare, em **DNS → Records**, criar:

| Tipo | Nome | Conteúdo | Proxy | TTL |
|------|------|---------|-------|-----|
| CNAME | `seedbox` | `seedbox-frontend-318940352257.s3-website-us-east-1.amazonaws.com` | ✅ Proxied (laranja) | Auto |
| CNAME | `api-seedbox` | `5dxinr12k0.execute-api.us-east-1.amazonaws.com` | ✅ Proxied (laranja) | Auto |

## 2. SSL/TLS

Em **SSL/TLS → Overview**:
- Modo: **Full** (não Full strict — S3 Website Endpoint usa HTTP na origem)

Em **SSL/TLS → Edge Certificates**:
- Always Use HTTPS: **Habilitado**
- HSTS: **Habilitado** (max-age=31536000, includeSubDomains)
- Minimum TLS Version: **1.2**

## 3. Cache Rules

Em **Caching → Cache Rules**, criar na ordem:

**Regra 1 — API Bypass Cache:**
- When: Hostname equals `api-seedbox.rafael.damasceno.nom.br`
- Then: Bypass cache

**Regra 2 — index.html Bypass:**
- When: Hostname equals `seedbox.rafael.damasceno.nom.br` AND URI Path equals `/index.html`
- Then: Bypass cache

**Regra 3 — Assets Cache 1 ano:**
- When: Hostname equals `seedbox.rafael.damasceno.nom.br` AND URI Path starts with `/assets/`
- Then: Eligible for cache, Edge TTL: 1 year

## 4. Security

Em **Security → WAF**:
- Bot Fight Mode: **Habilitado**

Em **Security → WAF → Rate limiting rules**:
- When: Hostname equals `api-seedbox.rafael.damasceno.nom.br`
- Rate: 200 requests per minute
- Action: Block for 5 minutes

## 5. Validação

Após configurar, testar:

```bash
# Frontend (deve retornar 200 com HTML)
curl -I https://seedbox.rafael.damasceno.nom.br

# API sem token (deve retornar 401)
curl -I https://api-seedbox.rafael.damasceno.nom.br/status

# Login
curl -s -X POST https://api-seedbox.rafael.damasceno.nom.br/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"SUA_SENHA"}'

# Status com token
TOKEN="TOKEN_RETORNADO"
curl -s https://api-seedbox.rafael.damasceno.nom.br/status \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Acesso direto ao S3 (deve retornar 403)
curl -I http://seedbox-frontend-318940352257.s3-website-us-east-1.amazonaws.com
```
