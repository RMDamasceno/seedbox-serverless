# Integration Points

Pontos de integração entre componentes. Será preenchido durante as Fases 2-4.

## Resumo

| De | Para | Protocolo |
|----|------|-----------|
| Frontend | API Gateway | HTTPS via Cloudflare |
| API Gateway | Lambda | Invocação síncrona |
| Lambda | S3 | boto3 (GetObject, PutObject, CopyObject, DeleteObject) |
| Lambda | Secrets Manager | boto3 (GetSecretValue) |
| Lambda | EC2 | boto3 (StartInstances, DescribeInstances) |
| Worker | S3 | boto3 + rclone |
| Worker | Transmission | JSON-RPC local (127.0.0.1:9091) |
