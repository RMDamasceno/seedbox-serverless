# ═══════════════════════════════════════════════════════════════
# Seedbox Serverless AWS — Bootstrap Script (PowerShell)
# Provisiona toda a infraestrutura do zero em conta AWS vazia.
# ═══════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.."
$TfDir = "$ProjectRoot\iac\terraform"
$FrontendDir = "$ProjectRoot\frontend"

function Log($msg)  { Write-Host "[OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Err($msg)  { Write-Host "[X] $msg" -ForegroundColor Red; exit 1 }
function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

# ─── 1. Pré-requisitos ───

Step "1/8 — Verificando pré-requisitos"

if (-not (Get-Command aws -ErrorAction SilentlyContinue))       { Err "AWS CLI nao encontrado" }
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) { Err "Terraform nao encontrado" }
if (-not (Get-Command python -ErrorAction SilentlyContinue))    { Err "Python nao encontrado" }
if (-not (Get-Command node -ErrorAction SilentlyContinue))      { Err "Node.js nao encontrado" }

Log "AWS CLI: $(aws --version 2>&1 | Select-Object -First 1)"
Log "Terraform: $(terraform version | Select-Object -First 1)"
Log "Python: $(python --version)"
Log "Node: $(node --version)"

# ─── 2. Credenciais AWS ───

Step "2/8 — Verificando credenciais AWS"

try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    $AwsAccountId = $identity.Account
} catch {
    Warn "AWS CLI nao configurado. Execute 'aws configure' primeiro."
    aws configure
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    $AwsAccountId = $identity.Account
}

$AwsRegion = aws configure get region 2>$null
if (-not $AwsRegion) { $AwsRegion = "us-east-1" }

Log "Account ID: $AwsAccountId"
Log "Region: $AwsRegion"

# ─── 3. Configuração ───

Step "3/8 — Configuracao"

$InputRegion = Read-Host "Regiao AWS [$AwsRegion]"
if ($InputRegion) { $AwsRegion = $InputRegion }

$InputProject = Read-Host "Nome do projeto [seedbox]"
$ProjectName = if ($InputProject) { $InputProject } else { "seedbox" }

$InputOrigin = Read-Host "Dominio Cloudflare (ex: https://seedbox.dominio.com) [*]"
$AllowedOrigin = if ($InputOrigin) { $InputOrigin } else { "*" }

$SeedboxPassword = Read-Host "Senha para login no Seedbox" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SeedboxPassword)
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

if (-not $PlainPassword) { Err "Senha nao pode ser vazia" }

Log "Configuracao coletada"

# ─── 4. Gerar secrets ───

Step "4/8 — Gerando secrets"

$PasswordHash = python -c "import bcrypt; print(bcrypt.hashpw(b'$PlainPassword', bcrypt.gensalt()).decode())"
$JwtSecret = python -c "import secrets; print(secrets.token_hex(32))"
$TransmissionPassword = python -c "import secrets; print(secrets.token_hex(16))"

Log "Secrets gerados"

# ─── 5. Terraform ───

Step "5/8 — Terraform init + apply"

@"
aws_region     = "$AwsRegion"
aws_account_id = "$AwsAccountId"
project_name   = "$ProjectName"
environment    = "dev"
allowed_origin = "$AllowedOrigin"
"@ | Set-Content "$TfDir\terraform.tfvars" -Encoding UTF8

Log "terraform.tfvars criado"

Push-Location $TfDir
terraform init
Log "Terraform inicializado"

terraform apply -auto-approve
Log "Infraestrutura provisionada"

$ApiGatewayUrl = terraform output -raw api_gateway_url
$FrontendEndpoint = terraform output -raw frontend_website_endpoint
$FrontendBucket = terraform output -raw frontend_bucket_name
$DataBucket = terraform output -raw data_bucket_name
$LaunchTemplateId = terraform output -raw worker_launch_template_id
$SubnetId = terraform output -raw public_subnet_id

Log "API Gateway: $ApiGatewayUrl"
Log "Frontend S3: $FrontendEndpoint"

Pop-Location

# ─── 6. Secrets Manager ───

Step "6/8 — Preenchendo Secrets Manager"

$AuthSecret = "{`"passwordHash`":`"$PasswordHash`",`"jwtSecret`":`"$JwtSecret`"}"
aws secretsmanager update-secret --secret-id seedbox/auth --secret-string $AuthSecret --region $AwsRegion | Out-Null

$TransSecret = "{`"username`":`"seedbox`",`"password`":`"$TransmissionPassword`"}"
aws secretsmanager update-secret --secret-id seedbox/transmission --secret-string $TransSecret --region $AwsRegion | Out-Null

Log "Secrets preenchidos"

# ─── 7. EC2 Worker ───

Step "7/8 — Criando instancia EC2 worker"

$InstanceId = aws ec2 run-instances `
    --launch-template "LaunchTemplateId=$LaunchTemplateId" `
    --subnet-id $SubnetId `
    --count 1 `
    --query 'Instances[0].InstanceId' `
    --output text `
    --region $AwsRegion

Log "Instancia criada: $InstanceId"

aws ec2 stop-instances --instance-ids $InstanceId --region $AwsRegion 2>$null | Out-Null
Start-Sleep -Seconds 30
Log "Instancia parada (sera ligada sob demanda)"

$ApiFunction = "$ProjectName-api"
$TriggerFunction = "$ProjectName-worker-trigger"

$ApiEnv = "Variables={S3_BUCKET=$DataBucket,EC2_INSTANCE_ID=$InstanceId,AUTH_SECRET_NAME=seedbox/auth,ALLOWED_ORIGIN=$AllowedOrigin,AWS_REGION_NAME=$AwsRegion,WORKER_TRIGGER_FUNCTION=$TriggerFunction}"
aws lambda update-function-configuration --function-name $ApiFunction --environment $ApiEnv --region $AwsRegion | Out-Null

$TriggerEnv = "Variables={EC2_INSTANCE_ID=$InstanceId,AWS_REGION_NAME=$AwsRegion}"
aws lambda update-function-configuration --function-name $TriggerFunction --environment $TriggerEnv --region $AwsRegion | Out-Null

Log "Lambdas atualizadas com EC2_INSTANCE_ID"

# ─── 8. Frontend ───

Step "8/8 — Build e deploy do frontend"

Push-Location $FrontendDir

"VITE_API_URL=$ApiGatewayUrl" | Set-Content .env.production -Encoding UTF8

npm ci
npm run build

aws s3 sync dist/assets/ "s3://$FrontendBucket/assets/" --cache-control "max-age=31536000,public,immutable" --delete --region $AwsRegion
aws s3 cp dist/index.html "s3://$FrontendBucket/index.html" --cache-control "no-cache,no-store,must-revalidate" --region $AwsRegion
aws s3 sync dist/ "s3://$FrontendBucket/" --exclude "assets/*" --exclude "index.html" --cache-control "max-age=3600,public" --delete --region $AwsRegion

Pop-Location
Log "Frontend deployed"

# ─── Resumo ───

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  Seedbox Serverless AWS — Deploy Completo!" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API Gateway:     $ApiGatewayUrl" -ForegroundColor Cyan
Write-Host "  Frontend S3:     http://$FrontendEndpoint" -ForegroundColor Cyan
Write-Host "  Frontend Bucket: $FrontendBucket" -ForegroundColor Cyan
Write-Host "  Data Bucket:     $DataBucket" -ForegroundColor Cyan
Write-Host "  EC2 Instance:    $InstanceId" -ForegroundColor Cyan
Write-Host "  Region:          $AwsRegion" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Proximos passos (Cloudflare):" -ForegroundColor Yellow
Write-Host "  1. CNAME  seedbox        -> $FrontendEndpoint  (Proxied)"
Write-Host "  2. CNAME  api.seedbox    -> $($ApiGatewayUrl -replace 'https://','')  (Proxied)"
Write-Host "  3. SSL: Full (frontend), Full strict (API)"
Write-Host "  4. Cache Rules conforme docs/infrastructure/cloudflare-setup.md"
Write-Host ""
