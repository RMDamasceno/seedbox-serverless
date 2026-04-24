# IAM Policies — Seedbox Serverless AWS

Todas as roles seguem o princípio de menor privilégio.

## seedbox-api-lambda-role

| Ação | Recurso |
|------|---------|
| s3:GetObject, PutObject, DeleteObject, CopyObject | queue/* |
| s3:GetObject, PutObject, HeadObject | idempotency/* |
| s3:PutObject, GetObject | torrents/* |
| s3:GetObject, DeleteObject | downloads/* |
| s3:ListBucket | bucket (prefixos: queue/, idempotency/, torrents/, downloads/) |
| secretsmanager:GetSecretValue | seedbox/* |
| ec2:DescribeInstances, StartInstances | tag:Project=seedbox |
| lambda:InvokeFunction | seedbox-worker-trigger |

## seedbox-authorizer-lambda-role

| Ação | Recurso |
|------|---------|
| secretsmanager:GetSecretValue | seedbox/auth* |

## seedbox-worker-trigger-lambda-role

| Ação | Recurso |
|------|---------|
| ec2:StartInstances, StopInstances, DescribeInstances | tag:Project=seedbox |

## seedbox-worker-ec2-role

| Ação | Recurso |
|------|---------|
| s3:GetObject, PutObject, DeleteObject, CopyObject | queue/* |
| s3:GetObject, PutObject | downloads/* |
| s3:GetObject | torrents/* |
| s3:ListBucket | bucket (prefixos: queue/, downloads/, torrents/) |
| ec2:StopInstances | tag:Name=seedbox-worker |
| secretsmanager:GetSecretValue | seedbox/transmission* |
