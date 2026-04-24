# Referência da API — Seedbox Serverless AWS

**Base URL:** `https://api.seedbox.seudominio.com`
**Autenticação:** Bearer JWT (header `Authorization: Bearer {token}`)

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | /auth/login | Autenticação (retorna JWT) |
| POST | /downloads | Criar download (magnet ou torrent) |
| GET | /downloads | Listar downloads (filtro por status) |
| GET | /downloads/{id} | Detalhes de um download |
| PATCH | /downloads/{id} | Editar nome |
| DELETE | /downloads/{id} | Remover permanentemente |
| POST | /downloads/{id}/cancel | Cancelar download |
| POST | /downloads/{id}/requeue | Recolocar na fila |
| POST | /downloads/{id}/download-url | Gerar Pre-signed URL |
| POST | /downloads/upload-url | Obter URL para upload de .torrent |
| GET | /status | Status da infraestrutura e fila |

## Contratos Detalhados

Consulte o [Documento Técnico v1.5](../.amazonq/rules/EscopoTecnicoArquitetura.md#6-contratos-de-api) para schemas completos de request/response.

A especificação OpenAPI será gerada em `docs/api/openapi.yaml` durante a Fase 2.
