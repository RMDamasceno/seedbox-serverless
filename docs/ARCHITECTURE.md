# Arquitetura — Seedbox Serverless AWS

## Diagrama de Alto Nível

```
Usuário
  │ HTTPS (Cloudflare)
  ▼
Cloudflare (DNS + Proxy + CDN + WAF)
  ├── seedbox.dominio.com → S3 Website (Frontend React)
  └── api.seedbox.dominio.com → API Gateway HTTP
                                   │
                                   ▼
                              Lambda (Python 3.12)
                              ├── seedbox-authorizer (JWT)
                              ├── seedbox-api (CRUD)
                              └── seedbox-worker-trigger (EC2)
                                   │
                              ┌────┴────┐
                              ▼         ▼
                          Amazon S3   EC2 Spot (t3.medium)
                        (Estado JSON)  ├── transmission-daemon
                        (Arquivos)     ├── worker.py
                                       └── rclone → S3
```

## Componentes

| Componente | Tecnologia | Responsabilidade |
|-----------|-----------|-----------------|
| Frontend | React 18 + Vite + TailwindCSS | Interface web SPA |
| CDN/SSL | Cloudflare Free | Proxy reverso, cache, WAF, DDoS |
| API | API Gateway HTTP + Lambda | CRUD de downloads, autenticação |
| Worker | EC2 Spot + Transmission | Download BitTorrent + sync S3 |
| Estado | S3 JSON (queue/) | Fila e estado dos downloads |
| Armazenamento | S3 Intelligent-Tiering | Arquivos baixados |

## Fluxo Principal

1. Usuário submete magnet link via frontend
2. Lambda cria JSON em `queue/pending/{id}.json`
3. Lambda liga EC2 se parada
4. Worker detecta item pendente, adquire lock via ETag
5. Worker inicia download no Transmission
6. Worker atualiza progresso no S3 (throttle: delta > 2% ou > 30s)
7. Ao concluir, `rclone move` para `downloads/completed/{id}/`
8. Após 3 ciclos ociosos, worker desliga a instância

## Decisões Arquiteturais

Consulte [memory-bank/DECISION_LOG.md](../memory-bank/DECISION_LOG.md) para o registro completo de ADRs.
