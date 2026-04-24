# Amazon Q Developer Rules - Seedbox Serverless AWS

**Versão:** 1.0  
**Data:** Abril de 2026  
**Projeto:** Seedbox Serverless AWS v1.5  
**Objetivo:** Automação profissional, autônoma e eficiente com documentação automática e changelog detalhado

---

## Índice

1. [Princípios Fundamentais](#princípios-fundamentais)
2. [Regras de Padrões de Código](#regras-de-padrões-de-código)
3. [Regras de Documentação Automática](#regras-de-documentação-automática)
4. [Regras de Changelog e Versionamento](#regras-de-changelog-e-versionamento)
5. [Regras de Testes e Qualidade](#regras-de-testes-e-qualidade)
6. [Regras de Segurança e Conformidade](#regras-de-segurança-e-conformidade)
7. [Regras de IaC e Infraestrutura](#regras-de-iac-e-infraestrutura)
8. [Memory Bank - Preservação de Histórico](#memory-bank---preservação-de-histórico)
9. [Estrutura de Documentação](#estrutura-de-documentação)
10. [Checklist de Implementação](#checklist-de-implementação)

---

## Princípios Fundamentais

Estas regras são baseadas em três pilares:

1. **Profissionalismo:** Código consistente, bem documentado e seguro
2. **Autonomia:** Amazon Q Developer trabalha sem intervenção manual
3. **Eficiência:** Documentação e changelog gerados automaticamente

Todas as regras devem ser aplicadas de forma consistente em todo o projeto.

---

## Regras de Padrões de Código

### RULE 1: Nomeação Consistente

**Escopo:** Todos os arquivos Python, TypeScript, Terraform e JSON

**Padrões Obrigatórios:**

- **Python Functions:** `snake_case` (ex: `transition_state()`, `get_next_pending_item()`)
- **Python Classes:** `PascalCase` (ex: `StateManager`, `DownloadProcessor`)
- **Python Constants:** `UPPER_SNAKE_CASE` (ex: `MAX_TORRENT_SIZE_GB`, `POLL_INTERVAL_SECONDS`)
- **TypeScript Components:** `PascalCase` (ex: `DownloadList.tsx`, `ProgressBar.tsx`)
- **TypeScript Functions:** `camelCase` (ex: `fetchDownloads()`, `updateProgress()`)
- **TypeScript Interfaces:** `IPascalCase` (ex: `IDownload`, `IWorkerStatus`)
- **Terraform Resources:** `snake_case` (ex: `aws_lambda_function`, `aws_s3_bucket`)
- **AWS Resource Names:** `kebab-case` (ex: `seedbox-api-lambda`, `seedbox-worker-sg`)
- **S3 Keys:** `lowercase-with-hyphens` (ex: `queue/pending`, `downloads/completed/{id}`)

**Ações do Amazon Q Developer:**

- ✓ Validar nomes ao criar novos arquivos
- ✓ Sugerir renomeação se violação detectada
- ✓ Alertar se padrão não é seguido
- ✓ Documentar padrão em `docs/STYLE_GUIDE.md`
- ✓ Bloquear commit se violação crítica

---

### RULE 2: Docstrings e Comentários Obrigatórios

**Escopo:** Todas as funções públicas em Python e TypeScript

**Requisitos:**

- Toda função pública deve ter docstring completa
- Docstring deve incluir: descrição, parâmetros, retorno, exceções
- Comentários explicam "por quê", não "o quê"
- Usar Google style para Python
- Usar JSDoc para TypeScript

**Exemplo Python (Google Style):**

```python
def transition_state(bucket, item_id, from_status, to_status, worker_id, updates):
    """
    Transiciona um item de download entre estados com atomicidade garantida via ETag.
    
    Implementa o protocolo COPY → VALIDATE → DELETE para evitar race conditions
    em operações concorrentes no S3.
    
    Args:
        bucket (str): Nome do bucket S3
        item_id (str): UUID do download
        from_status (str): Estado atual (pending, processing, completed, cancelled)
        to_status (str): Estado destino
        worker_id (str): ID da instância EC2 processando
        updates (dict): Campos adicionais a atualizar
        
    Returns:
        dict: Item atualizado com novo estado e versão
        
    Raises:
        LockConflictError: Se item está bloqueado por outro worker
        StateMismatchError: Se estado atual não corresponde ao esperado
        S3Error: Se operação de cópia condicional falhar
    """
```

**Exemplo TypeScript (JSDoc):**

```typescript
/**
 * Cria um novo download a partir de um magnet link.
 * 
 * @param clientRequestId - UUID único da requisição (para idempotência)
 * @param magnetLink - Magnet link do torrent
 * @param name - Nome opcional do download
 * @returns Promise<IDownload> - Objeto do download criado
 * @throws BadRequestError - Se magnet link for inválido
 * @throws ConflictError - Se disco não tiver espaço suficiente
 */
async function createDownload(
  clientRequestId: string,
  magnetLink: string,
  name?: string
): Promise<IDownload>
```

**Ações do Amazon Q Developer:**

- ✓ Validar docstrings ao salvar arquivo
- ✓ Sugerir adição de docstring faltante
- ✓ Gerar documentação de API automaticamente
- ✓ Alertar se docstring incompleta
- ✓ Bloquear commit se função pública sem docstring

---

### RULE 3: Tratamento de Erros Explícito

**Escopo:** Todas as funções em Python e TypeScript

**Requisitos:**

- Nunca use `try/except Exception` genérico
- Sempre especifique exceções esperadas
- Log deve incluir: timestamp, contexto, stack trace, ação corretiva
- Diferenciar entre erros temporários (retry) e definitivos (falha)

**Exemplo Python:**

```python
try:
    response = s3.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': source_key},
        Key=dest_key,
        CopySourceIfMatch=etag
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'PreconditionFailed':
        logger.warning(f"ETag mismatch for {item_id}: {e}")
        return None  # Outro processo ganhou a corrida
    elif e.response['Error']['Code'] == 'NoSuchKey':
        logger.error(f"Source key not found: {source_key}")
        raise
    else:
        logger.error(f"Unexpected S3 error: {e}", exc_info=True)
        raise
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

**Ações do Amazon Q Developer:**

- ✓ Alertar se `except Exception` detectado
- ✓ Validar que logs incluem contexto
- ✓ Sugerir tratamento específico de exceção
- ✓ Bloquear commit se genérico encontrado

---

### RULE 4: Idempotência em Operações Críticas

**Escopo:** Lambda functions e Worker scripts (operações de estado)

**Requisitos:**

- Toda operação que modifica estado deve ser idempotente
- Utilizar Client Request ID para deduplicação
- Verificar existência antes de criar
- Implementar protocolo COPY → VALIDATE → DELETE com ETag

**Exemplo Implementação:**

```python
def create_download(client_request_id, magnet_link, name):
    """Cria download com idempotência garantida."""
    
    # 1. Verificar se já existe
    idempotency_key = f"idempotency/{client_request_id}"
    try:
        response = s3.head_object(Bucket=bucket, Key=idempotency_key)
        # Já existe, retornar item existente
        existing_id = json.loads(s3.get_object(Bucket=bucket, Key=idempotency_key)['Body'].read())['id']
        return get_download_by_id(existing_id)
    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
    
    # 2. Criar novo item
    download_id = str(uuid.uuid4())
    item = {
        'id': download_id,
        'clientRequestId': client_request_id,
        'magnetLink': magnet_link,
        'name': name,
        'status': 'pending',
        'createdAt': datetime.utcnow().isoformat() + 'Z'
    }
    
    # 3. Persistir
    s3.put_object(Bucket=bucket, Key=f"queue/pending/{download_id}.json", Body=json.dumps(item))
    s3.put_object(Bucket=bucket, Key=idempotency_key, Body=json.dumps({"id": download_id}))
    
    return item
```

**Ações do Amazon Q Developer:**

- ✓ Validar que operações de estado usam Client Request ID
- ✓ Sugerir implementação de idempotência
- ✓ Documentar em `docs/idempotency-strategy.md`
- ✓ Alertar se operação crítica sem idempotência
- ✓ Bloquear commit se idempotência faltando

---

### RULE 5: Estrutura de Diretórios Consistente

**Escopo:** Projeto inteiro

**Estrutura Obrigatória:**

```
seedbox-serverless-aws/
├── iac/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── lambda/
│   │   │   ├── ec2/
│   │   │   ├── s3/
│   │   │   └── iam/
│   │   └── environments/
│   │       ├── dev/
│   │       └── prod/
│   └── cdk/ (alternativa)
│
├── backend/
│   ├── lambda/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── handler.py
│   │   │   ├── routes.py
│   │   │   ├── validators.py
│   │   │   └── state_manager.py
│   │   ├── authorizer/
│   │   │   └── handler.py
│   │   └── worker-trigger/
│   │       └── handler.py
│   └── worker/
│       ├── scripts/
│       │   ├── main.py
│       │   ├── monitor.py
│       │   └── disk_manager.py
│       └── config/
│           └── transmission.conf
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── styles/
│   ├── public/
│   └── package.json
│
├── docs/
│   ├── CHANGELOG.md
│   ├── ARCHITECTURE.md
│   ├── COMPONENTS.md
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   ├── TESTING.md
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── endpoints.md
│   ├── components/
│   │   ├── seedbox-api-lambda.md
│   │   └── ...
│   ├── infrastructure/
│   │   ├── resources.md
│   │   └── architecture-diagram.png
│   ├── security/
│   │   ├── iam-policies.md
│   │   └── secrets-management.md
│   ├── testing/
│   │   ├── test-coverage.md
│   │   └── failure-scenarios.md
│   └── templates/
│       ├── component-doc-template.md
│       ├── changelog-entry-template.md
│       └── ...
│
├── tests/
│   ├── unit/
│   │   ├── test_state_manager.py
│   │   ├── test_validators.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_api_create_download.py
│   │   └── ...
│   └── e2e/
│       └── test_full_download_flow.py
│
├── scripts/
│   ├── deploy/
│   ├── setup/
│   └── monitoring/
│
├── .amazon-q-rules.md (ESTE ARQUIVO)
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

**Ações do Amazon Q Developer:**

- ✓ Alertar se arquivo criado fora da estrutura
- ✓ Sugerir local apropriado
- ✓ Atualizar `docs/project-structure.md` automaticamente
- ✓ Bloquear commit se estrutura violada

---

## Regras de Documentação Automática

### RULE 6: Documentação de Componentes Automática

**Trigger:** Quando arquivo em `/backend`, `/frontend`, `/iac` é criado ou modificado

**Ações Automáticas:**

1. Extrair docstring/comentários do código
2. Gerar seção em `docs/components/{component-name}.md`
3. Incluir: descrição, dependências, variáveis de ambiente, exemplos, logs
4. Atualizar `docs/COMPONENTS.md` com índice
5. Atualizar `docs/ARCHITECTURE.md` se mudança arquitetural

**Exemplo de Saída Gerada:**

```markdown
# Component: seedbox-api-lambda

## Descrição
Lambda function que expõe a API REST para gerenciamento de downloads. 
Valida JWT, gerencia transições de estado e gera Pre-signed URLs.

## Localização
- **Caminho:** backend/lambda/api/
- **Linguagem:** Python 3.12
- **Versão:** 1.2.0

## Dependências
### Componentes Internos
- state_manager: Gerenciamento de transições de estado
- validators: Validação de entrada

### Serviços AWS
- S3: Leitura/escrita de queue/
- Secrets Manager: JWT secret
- EC2: start_instances

### Bibliotecas Externas
- boto3: 1.28.0 - AWS SDK
- pydantic: 2.0.0 - Validação de dados

## Variáveis de Ambiente
| Variável | Descrição | Padrão | Obrigatória |
|----------|-----------|--------|------------|
| S3_BUCKET | Nome do bucket principal | seedbox-{account-id} | Sim |
| AUTH_SECRET_NAME | Nome do secret JWT | seedbox/auth | Sim |
| EC2_INSTANCE_ID | ID da instância worker | - | Sim |

## Exemplos de Uso
### POST /downloads
```

**Ações do Amazon Q Developer:**

- ✓ Validar ao salvar arquivo
- ✓ Gerar documentação automaticamente
- ✓ Atualizar índices
- ✓ Alertar se documentação desatualizada

---

### RULE 7: Documentação de API em OpenAPI

**Trigger:** Quando arquivo em `/backend/lambda/api` é modificado

**Ações Automáticas:**

1. Extrair rotas e contratos do código
2. Gerar/atualizar `docs/api/openapi.yaml`
3. Gerar `docs/api/endpoints.md` com método, autenticação, parâmetros, respostas, exemplos
4. Gerar HTML interativo em `docs/api/index.html` (Swagger UI)
5. Atualizar `docs/API_REFERENCE.md`

**Formato OpenAPI Esperado:**

```yaml
openapi: 3.0.0
info:
  title: Seedbox Serverless AWS API
  version: 1.2.0
  description: API para gerenciamento de downloads via torrent

paths:
  /downloads:
    post:
      summary: Criar novo download
      operationId: createDownload
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateDownloadRequest'
      responses:
        '201':
          description: Download criado com sucesso
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Download'
        '400':
          description: Requisição inválida
        '409':
          description: Espaço em disco insuficiente
```

**Ações do Amazon Q Developer:**

- ✓ Validar ao salvar arquivo
- ✓ Gerar OpenAPI automaticamente
- ✓ Gerar Swagger UI
- ✓ Alertar se contrato mudou (breaking change)

---

### RULE 8: Documentação de Infraestrutura Automática

**Trigger:** Quando arquivo em `/iac` é modificado

**Ações Automáticas:**

1. Extrair recursos Terraform/CDK
2. Gerar `docs/infrastructure/resources.md` com: nome, tipo, configuração, dependências, custo
3. Gerar diagrama de arquitetura (Mermaid/D2)
4. Atualizar `docs/DEPLOYMENT.md` com instruções
5. Recalcular `docs/COST_ESTIMATION.md`

**Exemplo de Saída:**

```markdown
## Recursos AWS

### S3 Bucket: seedbox-{account-id}
- **Tipo:** S3 Bucket
- **Configuração:**
  - Block Public Access: Habilitado
  - Versioning: Habilitado
  - Lifecycle Rules: Intelligent-Tiering
  - Encryption: SSE-S3
- **Dependências:** Nenhuma
- **Custo Estimado:** US$ 2-6/mês (500 GB)

### Lambda: seedbox-api
- **Tipo:** AWS Lambda
- **Runtime:** Python 3.12
- **Memória:** 256 MB
- **Timeout:** 30s
- **Dependências:** S3, Secrets Manager, EC2
- **Custo Estimado:** < US$ 0,50/mês
```

**Ações do Amazon Q Developer:**

- ✓ Validar ao salvar arquivo
- ✓ Gerar documentação automaticamente
- ✓ Atualizar diagramas
- ✓ Recalcular custos

---

### RULE 9: Documentação de Testes Automática

**Trigger:** Quando arquivo em `/tests` é criado ou modificado

**Ações Automáticas:**

1. Extrair testes e gerar `docs/testing/test-coverage.md`
2. Incluir: tipos de testes, cobertura por componente, cenários de falha, como executar
3. Gerar relatório de cobertura em `docs/testing/coverage-report.html`
4. Atualizar `docs/TESTING.md`

**Exemplo de Saída:**

```markdown
## Testes Unitários

### test_transition_state.py
- ✓ test_successful_transition
- ✓ test_etag_mismatch_returns_none
- ✓ test_state_mismatch_raises_error
- ✓ test_lock_conflict_raises_error

**Cobertura:** 95% (19/20 linhas)

## Testes de Integração

### test_api_create_download.py
- ✓ test_create_download_with_magnet_link
- ✓ test_idempotency_on_duplicate_request
- ✓ test_disk_space_insufficient_returns_409

**Cobertura:** 88% (22/25 linhas)

## Testes de Falha Controlada
- ✓ test_disk_full_pauses_downloads
- ✓ test_ec2_interruption_moves_to_pending
- ✓ test_idempotency_on_duplicate_click
... (10/10 cenários)

**Cobertura:** 100%
```

**Ações do Amazon Q Developer:**

- ✓ Validar ao salvar arquivo
- ✓ Gerar documentação automaticamente
- ✓ Atualizar cobertura
- ✓ Alertar se cobertura < 80%

---

## Regras de Changelog e Versionamento

### RULE 10: Changelog Automático

**Trigger:** Quando qualquer arquivo em `/backend`, `/frontend`, `/iac` é modificado

**Tipos de Mudança Detectados:**

- **Feature:** Nova funcionalidade
- **Fix:** Correção de bug
- **Refactor:** Refatoração sem mudança de comportamento
- **Docs:** Atualização de documentação
- **Test:** Adição/modificação de testes
- **Chore:** Tarefas de manutenção
- **Security:** Correção de segurança
- **Perf:** Melhoria de performance

**Ações Automáticas:**

1. Detectar tipo de mudança (do commit message ou diff)
2. Registrar em `CHANGELOG.md` com: data, tipo, componente, descrição, impacto, breaking change
3. Atualizar versão (semver)
4. Gerar sumário em `CHANGELOG_SUMMARY.md`
5. Criar git tag se versão mudou

**Formato CHANGELOG.md:**

```markdown
# Changelog

## [1.2.0] - 2026-04-23

### Added
- **Backend/Lambda:** Implementação do protocolo de consistência S3 com ETag condicional
  - Arquivo: backend/lambda/api/state_manager.py
  - Função: transition_state()
  - Impacto: Garante atomicidade em operações concorrentes
  - Teste: tests/unit/test_transition_state.py

### Fixed
- **Worker/EC2:** Correção de race condition no monitoramento de progresso
  - Arquivo: backend/worker/scripts/monitor.py
  - Problema: Múltiplas atualizações simultâneas causavam inconsistência
  - Solução: Implementar lock via ETag antes de atualizar
  - Impacto: Reduz erros de transição de estado em 99%

### Changed
- **IaC/Terraform:** Atualização de versão do provider AWS para 5.0.0
  - Arquivo: iac/terraform/main.tf
  - Razão: Suporte a novas features de Lambda
  - Breaking Change: ⚠️ Requer re-apply da infraestrutura

### Deprecated
- **API:** Endpoint GET /downloads/{id}/status será descontinuado em v2.0
  - Use GET /downloads/{id} em seu lugar
  - Prazo: 90 dias

### Security
- **Lambda/API:** Implementação de validação de entrada para magnet links
  - Arquivo: backend/lambda/api/validators.py
  - Proteção: Evita injeção de código via magnet link malformado
  - CVE: N/A

### Performance
- **Worker/EC2:** Otimização de polling interval de 60s para 30s
  - Arquivo: backend/worker/scripts/main.py
  - Impacto: Reduz latência de detecção em 50%
  - Trade-off: Aumento de 5% no uso de CPU

## [1.1.0] - 2026-04-20
...
```

**Ações do Amazon Q Developer:**

- ✓ Detectar tipo de mudança automaticamente
- ✓ Registrar em CHANGELOG.md
- ✓ Atualizar versão
- ✓ Gerar sumário
- ✓ Criar git tag

---

### RULE 11: Versionamento Semântico

**Escopo:** Todos os componentes

**Formato:** `MAJOR.MINOR.PATCH[-prerelease][+build]`

**Regras:**

- **MAJOR:** Breaking changes (ex: mudança de schema JSON, API incompatível)
- **MINOR:** Novas features compatíveis com versão anterior
- **PATCH:** Bug fixes
- **Prerelease:** `-alpha`, `-beta`, `-rc` (ex: `1.2.0-rc1`)
- **Build:** `+timestamp`, `+git-hash` (ex: `1.2.0+20260423.a1b2c3d`)

**Componentes a Versionarem:**

- Backend API: `docs/api/version.txt`
- Frontend: `frontend/package.json`
- Worker: `backend/worker/VERSION`
- Infrastructure: `iac/terraform/version.tf`
- Overall Project: `docs/PROJECT_VERSION.txt`

**Ações do Amazon Q Developer:**

- ✓ Validar semver ao criar release
- ✓ Sugerir incremento apropriado baseado em mudanças
- ✓ Atualizar todos os arquivos de versão
- ✓ Criar git tag (ex: `v1.2.0`)
- ✓ Gerar release notes automaticamente

---

## Regras de Testes e Qualidade

### RULE 12: Cobertura de Testes Obrigatória

**Escopo:** `*.py`, `*.ts` (backend e frontend)

**Requisitos:**

- Mínimo **80%** de cobertura de código geral
- **100%** de cobertura para funções críticas:
  - Transição de estado (S3)
  - Autenticação (JWT)
  - Validação de entrada
  - Tratamento de erros

**Ações do Amazon Q Developer:**

- ✓ Validar cobertura ao salvar arquivo
- ✓ Alertar se cobertura < 80%
- ✓ Sugerir testes faltantes
- ✓ Gerar relatório de cobertura em `docs/testing/coverage-report.html`
- ✓ Bloquear merge se cobertura < 80%

---

### RULE 13: Testes de Falha Controlada Obrigatórios

**Escopo:** Componentes críticos (Lambda, Worker, S3 state)

**10 Cenários Obrigatórios:**

1. **Disco Cheio:** Worker pausa torrents, registra erro, retoma ao liberar espaço
2. **Interrupção de EC2:** Worker completa ciclo, move itens para pending, para graciosamente
3. **Falha de PUT no S3:** Worker classifica como erro temporário, aplica backoff, retenta
4. **Retry Forçado:** Submeter magnet link inválido → erro definitivo, move para cancelled
5. **Race Enqueue + Shutdown:** Lambda detecta estado stopping, aguarda 30s, tenta ligar novamente
6. **Duplo Clique (Idempotência):** Mesma requisição 2x → retorna item original sem duplicata
7. **index.json Stale:** Frontend detecta updatedAt > 2min, faz fallback para LIST direto
8. **Cancelamento Durante Sync S3:** Worker mata rclone, remove arquivo parcial, move para cancelled
9. **Cloudflare Bloqueando IPs:** Acesso negado pela Bucket Policy (apenas IPs CF permitidos)
10. **Expiração de Pre-signed URL:** TTL expirado → S3 retorna 403, frontend oferece regenerar

**Ações do Amazon Q Developer:**

- ✓ Validar que todos os 10 cenários têm testes
- ✓ Executar testes de falha antes de merge
- ✓ Documentar resultados em `docs/testing/failure-scenarios.md`
- ✓ Alertar se cenário não tem teste
- ✓ Bloquear commit se cenário crítico sem teste

---

### RULE 14: Nomeação de Testes

**Escopo:** Todos os arquivos de teste

**Padrão:** `test_{function_name}_{scenario}.py`

**Exemplos:**

- `test_transition_state_etag_mismatch.py`
- `test_create_download_with_magnet_link.py`
- `test_disk_full_pauses_downloads.py`

**Estrutura AAA (Arrange-Act-Assert):**

```python
def test_transition_state_successful():
    # Arrange
    bucket = "seedbox-123"
    item_id = "uuid-1234"
    from_status = "pending"
    to_status = "processing"
    worker_id = "i-0abc123"
    updates = {"transmissionId": 42}
    
    # Act
    result = transition_state(bucket, item_id, from_status, to_status, worker_id, updates)
    
    # Assert
    assert result['status'] == 'processing'
    assert result['workerId'] == worker_id
    assert result['version'] == 1
```

**Ações do Amazon Q Developer:**

- ✓ Validar nomeação de testes
- ✓ Sugerir renomeação se não segue padrão
- ✓ Validar estrutura AAA
- ✓ Alertar se teste sem assertions

---

## Regras de Segurança e Conformidade

### RULE 15: Validação de Segredos

**Escopo:** Todos os arquivos

**Padrões Detectados:**

- `api_key`, `apiKey`, `API_KEY`
- `password`, `passwd`, `pwd`
- `token`, `TOKEN`
- `secret`, `SECRET`
- `credential`, `CREDENTIAL`
- `private_key`, `privateKey`
- `access_key`, `accessKey`
- `bearer`, `BEARER`

**Ações do Amazon Q Developer:**

- ✓ Escanear ao salvar arquivo
- ✓ Alertar se possível secret detectado
- ✓ Sugerir uso de AWS Secrets Manager
- ✓ Bloquear commit se secret encontrado
- ✓ Documentar em `docs/security/secrets-management.md`

**Implementação Correta:**

```python
import boto3
import json

def get_secret(secret_name):
    """Recuperar secret do AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usar secret
auth_secret = get_secret('seedbox/auth')
jwt_secret = auth_secret['jwtSecret']
```

---

### RULE 16: Validação de IAM (Least Privilege)

**Escopo:** `/iac` (Terraform/CDK)

**Permissões Permitidas por Função:**

**Lambda API:**
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` (apenas `queue/`, `idempotency/`)
- `secretsmanager:GetSecretValue` (apenas `seedbox/*`)
- `ec2:StartInstances`, `ec2:DescribeInstances`

**Lambda Authorizer:**
- `secretsmanager:GetSecretValue` (apenas `seedbox/auth`)

**Lambda Trigger:**
- `ec2:StartInstances`, `ec2:DescribeInstances`

**Worker EC2:**
- `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` (apenas `queue/`, `downloads/completed/`)
- `secretsmanager:GetSecretValue` (apenas `seedbox/transmission`)

**Ações do Amazon Q Developer:**

- ✓ Validar permissões ao salvar arquivo IAM
- ✓ Alertar se permissão muito ampla (ex: `s3:*`, `*:*`)
- ✓ Sugerir permissões específicas
- ✓ Documentar em `docs/security/iam-policies.md`
- ✓ Bloquear commit se violação crítica

---

### RULE 17: Validação de Entrada

**Escopo:** `/backend/lambda/api` (endpoints)

**Validações Obrigatórias:**

| Campo | Tipo | Validação | Exemplo |
|-------|------|-----------|---------|
| `clientRequestId` | string | UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| `magnetLink` | string | Começa com `magnet:?` | `magnet:?xt=urn:btih:...` |
| `name` | string | Max 255 caracteres | `Ubuntu 22.04 LTS` |
| `expiresIn` | number | Max 604800 (7 dias) | `3600` |
| `torrentFile` | file | Max 1 MB, `.torrent` | `ubuntu.torrent` |

**Implementação Exemplo:**

```python
from pydantic import BaseModel, Field, validator
import re

class CreateDownloadRequest(BaseModel):
    clientRequestId: str = Field(..., description="UUID v4")
    type: str = Field(..., regex="^(magnet|torrent_file)$")
    magnetLink: str = Field(None, description="Magnet link")
    name: str = Field(None, max_length=255)
    
    @validator('clientRequestId')
    def validate_uuid(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID v4')
    
    @validator('magnetLink')
    def validate_magnet(cls, v):
        if v and not v.startswith('magnet:?'):
            raise ValueError('Invalid magnet link')
        return v
```

**Ações do Amazon Q Developer:**

- ✓ Validar ao salvar arquivo de API
- ✓ Sugerir validação faltante
- ✓ Gerar testes de validação automaticamente
- ✓ Documentar em `docs/api/validation-rules.md`
- ✓ Alertar se entrada sem validação

---

## Memory Bank - Preservação de Histórico

### O que é Memory Bank?

Memory Bank é um sistema de documentação persistente que preserva o histórico completo do projeto, decisões arquiteturais, contexto de desenvolvimento e conhecimento acumulado. Evita perda de informações quando há mudanças de chat, alteração de escopo de conversa ou transição entre diferentes agentes/desenvolvedores.

### RULE 20: Criação e Manutenção do Memory Bank

**Escopo:** Projeto inteiro

**Objetivo:** Manter um repositório centralizado de conhecimento que seja:
- Persistente (nunca é perdido)
- Acessível (fácil de encontrar e consultar)
- Atualizado (sincronizado com o projeto)
- Estruturado (organizado por tópicos)
- Rastreável (com histórico de mudanças)

### Estrutura do Memory Bank

```
memory-bank/
├── README.md                           # Índice e guia de uso
├── PROJECT_CONTEXT.md                  # Contexto geral do projeto
├── DECISION_LOG.md                     # Decisões arquiteturais
├── LESSONS_LEARNED.md                  # Lições aprendidas
├── KNOWN_ISSUES.md                     # Problemas conhecidos e soluções
├── INTEGRATION_POINTS.md               # Pontos de integração entre componentes
├── PERFORMANCE_NOTES.md                # Notas de performance e otimizações
├── SECURITY_DECISIONS.md               # Decisões de segurança
├── COST_OPTIMIZATION.md                # Estratégias de otimização de custo
├── DEPLOYMENT_PROCEDURES.md            # Procedimentos de deploy
├── TROUBLESHOOTING.md                  # Guia de troubleshooting
├── TEAM_KNOWLEDGE.md                   # Conhecimento da equipe
├── EXTERNAL_DEPENDENCIES.md            # Dependências externas
├── API_CONTRACTS.md                    # Contratos de API
├── DATABASE_SCHEMA.md                  # Schema de dados (S3 JSON)
├── ENVIRONMENT_SETUP.md                # Setup de ambiente
├── THIRD_PARTY_INTEGRATIONS.md         # Integrações com terceiros
├── ROADMAP_DECISIONS.md                # Decisões sobre roadmap
└── CHAT_HISTORY_SUMMARIES/
    ├── chat_001_initial_setup.md
    ├── chat_002_lambda_implementation.md
    ├── chat_003_worker_ec2.md
    └── chat_NNN_{date}_{topic}.md
```

### RULE 20.1: PROJECT_CONTEXT.md

**Propósito:** Documentar o contexto geral do projeto

**Conteúdo Obrigatório:**

```markdown
# Project Context - Seedbox Serverless AWS

## Visão Geral
- **Nome do Projeto:** Seedbox Serverless AWS
- **Versão:** 1.5
- **Status:** Em Desenvolvimento
- **Data de Início:** 2026-04-01
- **Data Prevista de Conclusão:** 2026-06-30
- **Desenvolvedor Principal:** [Nome]
- **Contato:** [Email]

## Objetivos Principais
1. Criar sistema de download via torrent serverless
2. Minimizar custos operacionais (zero quando ocioso)
3. Garantir segurança e idempotência
4. Manter documentação automática

## Restrições e Limitações
- Usuário único (v1.0)
- Tamanho máximo de torrent: 50 GB
- Armazenamento máximo: 1 TB
- Timeout de Lambda: 30 segundos

## Stack Tecnológico
- **Frontend:** React + S3 + Cloudflare
- **Backend:** AWS Lambda + API Gateway
- **Worker:** EC2 Spot + Transmission
- **Armazenamento:** S3 + JSON
- **Infraestrutura:** Terraform/CDK

## Arquitetura de Alto Nível
[Incluir diagrama ou referência]

## Stakeholders
- Desenvolvedor: [Nome]
- Revisor: [Nome]
- Usuário Final: [Nome]

## Links Importantes
- Repositório: [URL]
- Documentação: [URL]
- Dashboard: [URL]
- Logs: [URL]
```

**Ações do Amazon Q Developer:**
- ✓ Atualizar quando contexto muda (novo objetivo, restrição, stakeholder)
- ✓ Manter sincronizado com realidade do projeto
- ✓ Alertar se informação desatualizada

---

### RULE 20.2: DECISION_LOG.md

**Propósito:** Documentar todas as decisões arquiteturais e técnicas

**Formato ADR (Architecture Decision Record):**

```markdown
# Decision Log

## ADR-001: Usar S3 JSON em vez de Banco de Dados Relacional

**Data:** 2026-04-01  
**Status:** Aceito  
**Contexto:**
O projeto precisa armazenar estado de downloads e fila de processamento.
Opções consideradas:
1. DynamoDB (banco NoSQL gerenciado)
2. RDS PostgreSQL (banco relacional gerenciado)
3. S3 JSON (armazenamento de objetos)

**Decisão:**
Utilizar S3 JSON para armazenar estado.

**Justificativa:**
- Custo: S3 é mais barato para volume baixo
- Simplicidade: Sem necessidade de gerenciar conexões
- Idempotência: Fácil implementar com ETag
- Escalabilidade: Suporta crescimento futuro

**Consequências:**
- Positivas:
  - Reduz custo fixo mensal
  - Simplifica arquitetura
  - Facilita testes e debugging
- Negativas:
  - Sem queries complexas
  - Consistência eventual
  - Requer implementar locking manualmente

**Alternativas Rejeitadas:**
- DynamoDB: Custo fixo de 1 unidade de leitura/escrita
- RDS: Custo fixo de instância mínima

**Referências:**
- [S3 Consistency Model](https://docs.aws.amazon.com/AmazonS3/latest/userguide/consistency.html)
- [ETag Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html)

---

## ADR-002: Usar Cloudflare em vez de CloudFront

**Data:** 2026-04-15  
**Status:** Aceito  
**Contexto:**
Precisa de CDN, proxy reverso e SSL para frontend e API.

**Decisão:**
Utilizar Cloudflare (plano Free) em vez de AWS CloudFront.

**Justificativa:**
- Custo: Plano Free vs CloudFront pago
- Funcionalidades: WAF, DDoS, Bot Fight Mode inclusos
- Simplicidade: Gerenciamento mais simples

**Consequências:**
- Reduz custo em ~US$ 0,10-1,00/mês
- Adiciona proteção DDoS gratuita
- Simplifica gerenciamento de SSL

---

## ADR-003: Implementar Idempotência com Client Request ID

**Data:** 2026-04-20  
**Status:** Aceito  
**Contexto:**
Requisições de criação de download podem ser retentadas.
Necessário evitar duplicação.

**Decisão:**
Implementar idempotência usando Client Request ID gerado pelo frontend.

**Justificativa:**
- Simples de implementar
- Funciona com S3 JSON
- Compatível com retry automático

**Implementação:**
- Frontend gera UUID para cada requisição
- Backend verifica `idempotency/{clientRequestId}`
- Se existe, retorna item existente
- Se não existe, cria novo item
```

**Ações do Amazon Q Developer:**
- ✓ Registrar decisão ao fazer escolha arquitetural
- ✓ Manter ADRs atualizados
- ✓ Alertar se decisão anterior é violada
- ✓ Documentar consequências de mudanças

---

### RULE 20.3: LESSONS_LEARNED.md

**Propósito:** Documentar lições aprendidas para evitar repetir erros

**Conteúdo:**

```markdown
# Lessons Learned

## Lição 1: Importância de Idempotência em Sistemas Distribuídos

**Data:** 2026-04-25  
**Severidade:** Alta  
**Contexto:**
Durante testes, descobrimos que requisições retentadas criavam duplicatas de downloads.

**Problema:**
Sem verificação de `clientRequestId`, múltiplas requisições idênticas criavam múltiplos itens.

**Solução Implementada:**
Implementar verificação de idempotência antes de criar novo item.

**Impacto:**
- Reduz bugs de duplicação em 100%
- Melhora confiabilidade do sistema
- Adiciona ~10ms de latência (aceitável)

**Aplicável a:**
- Todas as operações de criação
- Qualquer sistema com retries

---

## Lição 2: Monitoramento de ETag é Crítico

**Data:** 2026-04-28  
**Severidade:** Crítica  
**Contexto:**
Race condition entre worker e Lambda causava inconsistência de estado.

**Problema:**
Sem validação de ETag, dois processos podiam atualizar o mesmo item simultaneamente.

**Solução Implementada:**
Utilizar `CopySourceIfMatch` com ETag para garantir atomicidade.

**Impacto:**
- Elimina race conditions
- Garante consistência de estado
- Requer retry logic em caso de falha

---

## Lição 3: Logging Detalhado Economiza Horas de Debugging

**Data:** 2026-05-02  
**Severidade:** Alta  
**Contexto:**
Erro intermitente em produção levou 4 horas para identificar.

**Problema:**
Logs não incluíam contexto suficiente (item_id, worker_id, timestamp).

**Solução Implementada:**
Adicionar contexto estruturado a todos os logs.

**Impacto:**
- Reduz tempo de debugging
- Facilita rastreamento de issues
- Melhora observabilidade

**Padrão de Log:**
```python
logger.info("Download started", extra={
    'item_id': item_id,
    'worker_id': worker_id,
    'size_gb': size_bytes / 1e9,
    'timestamp': datetime.utcnow().isoformat()
})
```
```

**Ações do Amazon Q Developer:**
- ✓ Registrar lição ao descobrir padrão
- ✓ Manter atualizado com novos aprendizados
- ✓ Alertar se padrão de erro anterior é repetido

---

### RULE 20.4: KNOWN_ISSUES.md

**Propósito:** Documentar problemas conhecidos e workarounds

**Conteúdo:**

```markdown
# Known Issues

## Issue #001: EC2 Spot Interruption sem Aviso

**Severidade:** Alta  
**Status:** Aberto  
**Data Descoberta:** 2026-05-05  
**Componente:** Worker EC2  

**Descrição:**
Instância EC2 Spot é interrompida ocasionalmente sem aviso prévio.

**Sintomas:**
- Download em andamento é interrompido
- Item fica em estado "processing" indefinidamente
- Nenhuma mensagem de erro nos logs

**Causa Raiz:**
EC2 Spot não fornece aviso de interrupção em 100% dos casos.

**Workaround:**
- Implementar health check a cada 5 minutos
- Mover itens "processing" para "pending" se worker não responde
- Configurar alarme CloudWatch para Spot Interruption

**Solução Permanente:**
Migrar para ECS Fargate em v2.0 (sem Spot interruptions).

**Impacto:**
- Baixo (afeta <1% dos downloads)
- Mitigado por retry automático

---

## Issue #002: Cloudflare Cache Stale

**Severidade:** Média  
**Status:** Mitigado  
**Data Descoberta:** 2026-05-08  

**Descrição:**
Frontend cacheado pela Cloudflare fica desatualizado.

**Sintomas:**
- Usuário vê versão antiga do frontend
- Mudanças não aparecem imediatamente

**Causa Raiz:**
Cloudflare cache TTL muito alto (1 ano para assets).

**Workaround:**
- Usar cache busting (adicionar hash ao filename)
- Configurar `Cache-Control: no-cache` para `index.html`
- Purgar cache manualmente quando necessário

**Solução Permanente:**
Implementar versionamento de assets com hash.
```

**Ações do Amazon Q Developer:**
- ✓ Registrar issue ao descobrir
- ✓ Manter status atualizado (Aberto/Mitigado/Resolvido)
- ✓ Alertar se issue similar é encontrada

---

### RULE 20.5: INTEGRATION_POINTS.md

**Propósito:** Documentar pontos de integração entre componentes

**Conteúdo:**

```markdown
# Integration Points

## Frontend → API Gateway

**Protocolo:** HTTPS (via Cloudflare)  
**Autenticação:** Bearer JWT  
**Rate Limit:** 100 req/min  
**Timeout:** 30s  

**Endpoints:**
- POST /downloads - Criar download
- GET /downloads - Listar downloads
- GET /downloads/{id} - Obter detalhes
- PATCH /downloads/{id} - Atualizar nome
- DELETE /downloads/{id} - Deletar
- POST /downloads/{id}/cancel - Cancelar
- POST /downloads/{id}/download-url - Gerar Pre-signed URL

**Exemplo de Requisição:**
```json
{
  "clientRequestId": "uuid",
  "type": "magnet",
  "magnetLink": "magnet:?xt=..."
}
```

**Exemplo de Resposta:**
```json
{
  "download": {
    "id": "uuid",
    "status": "pending",
    "progressPercent": 0
  }
}
```

---

## API Gateway → Lambda

**Protocolo:** Invocação síncrona  
**Timeout:** 30s  
**Memória:** 256 MB  

**Fluxo:**
1. API Gateway recebe requisição
2. Valida JWT com Lambda Authorizer
3. Invoca Lambda API
4. Lambda processa e retorna resposta
5. API Gateway retorna ao cliente

---

## Lambda → S3

**Protocolo:** AWS SDK (boto3)  
**Operações:** GetObject, PutObject, DeleteObject, ListBucket, CopyObject  
**Consistência:** Read-after-write para PUT, eventual para DELETE  

**Padrão de Transição de Estado:**
1. GET item com ETag
2. VALIDATE estado
3. COPY com CopySourceIfMatch (atomicidade)
4. PUT com novo estado
5. DELETE origem
6. UPDATE index.json

---

## Lambda → Secrets Manager

**Protocolo:** AWS SDK (boto3)  
**Secrets:** seedbox/auth, seedbox/transmission  
**Cache:** 1 hora (recomendado)  

---

## Lambda → EC2

**Protocolo:** AWS SDK (boto3)  
**Ações:** StartInstances, DescribeInstances, StopInstances  
**Timeout:** 5 minutos para start  

---

## Worker EC2 → S3

**Protocolo:** AWS SDK (boto3) + rclone  
**Operações:** GetObject, PutObject, ListBucket  
**Transferências:** 4 threads paralelos (rclone)  

---

## Worker EC2 → Transmission

**Protocolo:** JSON-RPC via socket local  
**Port:** 6969 (padrão)  
**Operações:** torrent-add, torrent-get, torrent-stop, torrent-remove  
```

**Ações do Amazon Q Developer:**
- ✓ Manter atualizado quando novo ponto de integração é adicionado
- ✓ Documentar mudanças de protocolo
- ✓ Alertar se integração quebrada

---

### RULE 20.6: Chat History Summaries

**Propósito:** Preservar contexto de chats anteriores

**Formato:** `chat_NNN_{date}_{topic}.md`

**Conteúdo Obrigatório:**

```markdown
# Chat #001 - Initial Setup and Architecture

**Data:** 2026-04-01  
**Duração:** 2 horas  
**Participantes:** Desenvolvedor, Amazon Q Developer  
**Tópico Principal:** Setup inicial e definição de arquitetura  

## Objetivos Alcançados
1. ✓ Definir arquitetura geral
2. ✓ Escolher tecnologias (AWS, React, Terraform)
3. ✓ Criar documento técnico v1.0
4. ✓ Planejar fases de desenvolvimento

## Decisões Tomadas
- Usar S3 JSON em vez de banco de dados
- Usar Cloudflare em vez de CloudFront
- Implementar idempotência com Client Request ID

## Problemas Identificados
- Necessário definir protocolo de consistência S3
- Necessário implementar retry logic

## Próximas Etapas
1. Implementar IaC (Terraform)
2. Desenvolver Lambda API
3. Desenvolver Worker EC2

## Referências Criadas
- docs/ARCHITECTURE.md
- docs/Documento_Técnico_v1.0.md
- Guia_Desenvolvedor_Seedbox_AWS.md

## Contexto para Próximos Chats
- Arquitetura aprovada e documentada
- Stack tecnológico definido
- Fases de desenvolvimento planejadas
- Pronto para começar implementação
```

**Ações do Amazon Q Developer:**
- ✓ Criar sumário ao final de cada chat
- ✓ Manter histórico completo
- ✓ Consultar histórico anterior ao iniciar novo chat
- ✓ Alertar se contexto anterior é ignorado

---

### RULE 20.7: Atualização e Sincronização do Memory Bank

**Frequência:** Contínua (a cada mudança significativa)

**Triggers para Atualização:**

| Evento | Arquivo a Atualizar | Ação |
|--------|---------------------|------|
| Nova decisão arquitetural | DECISION_LOG.md | Adicionar ADR |
| Problema descoberto | KNOWN_ISSUES.md | Registrar issue |
| Lição aprendida | LESSONS_LEARNED.md | Documentar |
| Novo ponto de integração | INTEGRATION_POINTS.md | Adicionar |
| Fim de chat | Chat History | Criar sumário |
| Mudança de contexto | PROJECT_CONTEXT.md | Atualizar |
| Performance insight | PERFORMANCE_NOTES.md | Documentar |
| Problema de segurança | SECURITY_DECISIONS.md | Registrar |
| Otimização de custo | COST_OPTIMIZATION.md | Documentar |
| Novo procedimento | DEPLOYMENT_PROCEDURES.md | Adicionar |

**Ações do Amazon Q Developer:**
- ✓ Atualizar Memory Bank automaticamente
- ✓ Manter sincronizado com projeto
- ✓ Alertar se informação desatualizada
- ✓ Validar consistência entre arquivos

---

### RULE 20.8: Consulta do Memory Bank

**Quando Consultar:**

1. **Ao iniciar novo chat:** Ler `PROJECT_CONTEXT.md` e `chat_history_summaries/`
2. **Ao tomar decisão:** Consultar `DECISION_LOG.md` para evitar repetir decisões
3. **Ao encontrar problema:** Consultar `KNOWN_ISSUES.md` e `LESSONS_LEARNED.md`
4. **Ao integrar componentes:** Consultar `INTEGRATION_POINTS.md`
5. **Ao otimizar:** Consultar `PERFORMANCE_NOTES.md` e `COST_OPTIMIZATION.md`
6. **Ao fazer deploy:** Consultar `DEPLOYMENT_PROCEDURES.md`

**Ações do Amazon Q Developer:**
- ✓ Consultar Memory Bank ao iniciar
- ✓ Alertar se contexto anterior é relevante
- ✓ Sugerir referências do Memory Bank
- ✓ Validar decisões contra histórico

---

### RULE 20.9: Estrutura de Arquivo de Chat History

**Localização:** `memory-bank/CHAT_HISTORY_SUMMARIES/`

**Nomenclatura:** `chat_{NNN}_{YYYYMMDD}_{topic}.md`

**Exemplos:**
- `chat_001_20260401_initial_setup.md`
- `chat_002_20260405_lambda_implementation.md`
- `chat_003_20260410_worker_ec2.md`
- `chat_004_20260415_frontend_react.md`
- `chat_005_20260420_testing_and_qa.md`

**Conteúdo Mínimo:**

```markdown
# Chat #NNN - {Título}

**Data:** YYYY-MM-DD  
**Duração:** X horas  
**Escopo:** {Descrição do escopo}

## Objetivos
- [ ] Objetivo 1
- [ ] Objetivo 2
- [ ] Objetivo 3

## Decisões Tomadas
- Decisão 1: Justificativa
- Decisão 2: Justificativa

## Problemas Identificados
- Problema 1: Impacto
- Problema 2: Impacto

## Próximas Etapas
1. Ação 1
2. Ação 2
3. Ação 3

## Referências Criadas/Modificadas
- docs/arquivo1.md
- docs/arquivo2.md

## Contexto para Próximos Chats
- Informação crítica 1
- Informação crítica 2
- Informação crítica 3
```

---

### RULE 20.10: Backup e Versionamento do Memory Bank

**Frequência de Backup:** Diária (automática via git)

**Versionamento:**
- Usar git para versionamento
- Commitar mudanças com mensagem descritiva
- Exemplo: `docs: update memory bank - add ADR-004 on caching strategy`

**Retenção:**
- Manter histórico completo indefinidamente
- Não deletar arquivos (apenas arquivar se necessário)
- Usar branches para experimentos

**Ações do Amazon Q Developer:**
- ✓ Commitar mudanças do Memory Bank
- ✓ Manter histórico completo
- ✓ Alertar se mudança crítica não foi commitada

---

## Regras de IaC e Infraestrutura

### RULE 18: Validação de Infraestrutura

**Escopo:** `/iac` (Terraform/CDK)

**Checks Obrigatórios:**

- `terraform validate` - Validar sintaxe
- `terraform fmt` - Verificar formatação
- `terraform plan` - Verificar mudanças
- `tflint` - Linting
- `checkov` - Segurança

**Ações do Amazon Q Developer:**

- ✓ Executar validação ao salvar arquivo
- ✓ Alertar se validação falhar
- ✓ Sugerir correções
- ✓ Bloquear merge se validação falhar

---

### RULE 19: Documentação de Recursos AWS

**Trigger:** Quando arquivo em `/iac` é modificado

**Ações Automáticas:**

1. Extrair recursos Terraform/CDK
2. Para cada recurso, gerar documentação:
   - Nome e tipo
   - Configuração principal
   - Dependências
   - Custo estimado
   - Logs e métricas associadas
3. Atualizar `docs/infrastructure/resources.md`
4. Atualizar diagrama de arquitetura

---

## Estrutura de Documentação

### Arquivos Obrigatórios

```
docs/
├── CHANGELOG.md                    # Changelog completo
├── CHANGELOG_SUMMARY.md            # Sumário das últimas mudanças
├── PROJECT_VERSION.txt             # Versão atual do projeto
├── PROJECT_STRUCTURE.md            # Estrutura de diretórios
├── ARCHITECTURE.md                 # Arquitetura geral
├── COMPONENTS.md                   # Índice de componentes
├── API_REFERENCE.md                # Referência de API
├── DEPLOYMENT.md                   # Instruções de deploy
├── TESTING.md                      # Guia de testes
├── COST_ESTIMATION.md              # Estimativa de custos
├── STYLE_GUIDE.md                  # Guia de estilo
├── DEVELOPMENT.md                  # Guia de desenvolvimento
├── RELEASE_NOTES.md                # Release notes
│
├── api/
│   ├── openapi.yaml                # Especificação OpenAPI
│   ├── endpoints.md                # Documentação de endpoints
│   ├── index.html                  # Swagger UI
│   ├── validation-rules.md         # Regras de validação
│   └── version.txt                 # Versão da API
│
├── components/
│   ├── seedbox-api-lambda.md       # Documentação do componente
│   ├── seedbox-worker-ec2.md
│   ├── seedbox-frontend-react.md
│   └── ...
│
├── infrastructure/
│   ├── resources.md                # Lista de recursos AWS
│   ├── architecture-diagram.png    # Diagrama de arquitetura
│   └── cost-breakdown.md           # Detalhamento de custos
│
├── security/
│   ├── iam-policies.md             # Políticas IAM
│   ├── secrets-management.md       # Gerenciamento de segredos
│   └── security-checklist.md       # Checklist de segurança
│
├── testing/
│   ├── test-coverage.md            # Cobertura de testes
│   ├── coverage-report.html        # Relatório HTML
│   ├── failure-scenarios.md        # Cenários de falha
│   └── testing-guide.md            # Guia de testes
│
└── templates/
    ├── component-doc-template.md
    ├── changelog-entry-template.md
    ├── changelog-summary-template.md
    ├── release-notes-template.md
    └── style-guide-template.md
```

---

## Checklist de Implementação

- [ ] Copiar este arquivo (`.amazon-q-rules.md`) para a raiz do repositório
- [ ] Criar diretório `docs/templates/` com todos os templates
- [ ] Configurar Amazon Q Developer para usar este arquivo como rules
- [ ] Testar com um commit de exemplo
- [ ] Validar que documentação é gerada corretamente
- [ ] Validar que changelog é atualizado
- [ ] Validar que versão é incrementada
- [ ] Ajustar regras conforme necessário
- [ ] Documentar processo em `docs/DEVELOPMENT.md`
- [ ] Treinar equipe (se aplicável) com exemplos
- [ ] Criar backup deste arquivo
- [ ] Revisar e atualizar regras mensalmente

---

## Resumo das Regras

| # | Regra | Categoria | Prioridade | Escopo |
|---|-------|-----------|-----------|--------|
| 1 | Nomeação Consistente | Código | Alta | Todos os arquivos |
| 2 | Docstrings Obrigatórias | Código | Alta | Python/TypeScript |
| 3 | Tratamento de Erros | Código | Alta | Python/TypeScript |
| 4 | Idempotência | Código | Crítica | Lambda/Worker |
| 5 | Estrutura de Diretórios | Código | Alta | Projeto inteiro |
| 6 | Documentação de Componentes | Documentação | Alta | Backend/Frontend/IaC |
| 7 | Documentação de API | Documentação | Alta | Lambda API |
| 8 | Documentação de Infraestrutura | Documentação | Alta | IaC |
| 9 | Documentação de Testes | Documentação | Média | Testes |
| 10 | Changelog Automático | Versionamento | Crítica | Backend/Frontend/IaC |
| 11 | Versionamento Semântico | Versionamento | Alta | Todos os componentes |
| 12 | Cobertura de Testes | Qualidade | Alta | Python/TypeScript |
| 13 | Testes de Falha | Qualidade | Crítica | Lambda/Worker |
| 14 | Nomeação de Testes | Qualidade | Média | Testes |
| 15 | Validação de Segredos | Segurança | Crítica | Todos os arquivos |
| 16 | Validação de IAM | Segurança | Crítica | IaC |
| 17 | Validação de Entrada | Segurança | Alta | Lambda API |
| 18 | Validação de Infraestrutura | IaC | Alta | IaC |
| 19 | Documentação de Recursos | Documentação | Média | IaC |
| 20 | Memory Bank | Preservação | Crítica | Projeto inteiro |

---

## Benefícios das Regras

| Benefício | Descrição |
|-----------|-----------|
| **Profissionalismo** | Código consistente, bem documentado e seguro |
| **Autonomia** | Amazon Q Developer trabalha sem intervenção manual |
| **Eficiência** | Documentação e changelog gerados automaticamente |
| **Rastreabilidade** | Todas as mudanças registradas com contexto |
| **Qualidade** | Testes e validações garantem confiabilidade |
| **Segurança** | Validação de secrets, IAM e entrada |
| **Manutenibilidade** | Código limpo, modular e bem documentado |
| **Escalabilidade** | Estrutura preparada para crescimento |

---

## Próximas Etapas

1. Salvar este arquivo como `.amazon-q-rules.md` na raiz do repositório
2. Criar diretório `docs/templates/` com templates
3. Configurar Amazon Q Developer para usar este arquivo
4. Testar com um commit de exemplo
5. Ajustar regras conforme necessário
6. Documentar processo em `docs/DEVELOPMENT.md`
7. Revisar regras mensalmente

---

**Documento criado em:** Abril de 2026  
**Versão:** 1.0  
**Status:** Pronto para Implementação  
**Próxima Revisão:** Julho de 2026
