#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# Seedbox Serverless AWS — Bootstrap Script
# Provisiona toda a infraestrutura do zero em conta AWS vazia.
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TF_DIR="$PROJECT_ROOT/iac/terraform"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${CYAN}═══ $1 ═══${NC}"; }

# ─── Pré-requisitos ───

step "1/8 — Verificando pré-requisitos"

command -v aws >/dev/null 2>&1       || err "AWS CLI não encontrado. Instale: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
command -v terraform >/dev/null 2>&1  || err "Terraform não encontrado. Instale: https://developer.hashicorp.com/terraform/install"
command -v python3 >/dev/null 2>&1    || err "Python 3 não encontrado."
command -v node >/dev/null 2>&1       || err "Node.js não encontrado."
command -v npm >/dev/null 2>&1        || err "npm não encontrado."

log "AWS CLI: $(aws --version 2>&1 | head -1)"
log "Terraform: $(terraform version -json 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["terraform_version"])' 2>/dev/null || terraform version | head -1)"
log "Python: $(python3 --version)"
log "Node: $(node --version)"

# ─── Verificar credenciais AWS ───

step "2/8 — Verificando credenciais AWS"

if ! aws sts get-caller-identity >/dev/null 2>&1; then
    warn "AWS CLI não configurado. Executando 'aws configure'..."
    aws configure
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

log "Account ID: $AWS_ACCOUNT_ID"
log "Region: $AWS_REGION"

# ─── Coletar configurações ───

step "3/8 — Configuração"

read -rp "Região AWS [$AWS_REGION]: " INPUT_REGION
AWS_REGION="${INPUT_REGION:-$AWS_REGION}"

read -rp "Nome do projeto [seedbox]: " INPUT_PROJECT
PROJECT_NAME="${INPUT_PROJECT:-seedbox}"

read -rp "Domínio Cloudflare (ex: https://seedbox.dominio.com) [*]: " INPUT_ORIGIN
ALLOWED_ORIGIN="${INPUT_ORIGIN:-*}"

read -rsp "Senha para login no Seedbox: " SEEDBOX_PASSWORD
echo ""

if [ -z "$SEEDBOX_PASSWORD" ]; then
    err "Senha não pode ser vazia"
fi

log "Configuração coletada"

# ─── Gerar secrets ───

step "4/8 — Gerando secrets"

PASSWORD_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'$SEEDBOX_PASSWORD', bcrypt.gensalt()).decode())")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
TRANSMISSION_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")

log "Password hash gerado"
log "JWT secret gerado"
log "Transmission password gerado"

# ─── Criar terraform.tfvars ───

step "5/8 — Terraform init + apply"

cat > "$TF_DIR/terraform.tfvars" <<EOF
aws_region     = "$AWS_REGION"
aws_account_id = "$AWS_ACCOUNT_ID"
project_name   = "$PROJECT_NAME"
environment    = "dev"
allowed_origin = "$ALLOWED_ORIGIN"
EOF

log "terraform.tfvars criado"

# Build Lambda packages
bash "$PROJECT_ROOT/scripts/deploy/build-lambdas.sh"
log "Lambda packages built"

cd "$TF_DIR"
terraform init
log "Terraform inicializado"

terraform apply -auto-approve
log "Infraestrutura provisionada"

# Capturar outputs
API_GATEWAY_URL=$(terraform output -raw api_gateway_url)
FRONTEND_ENDPOINT=$(terraform output -raw frontend_website_endpoint)
FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
DATA_BUCKET=$(terraform output -raw data_bucket_name)
LAUNCH_TEMPLATE_ID=$(terraform output -raw worker_launch_template_id)

log "API Gateway: $API_GATEWAY_URL"
log "Frontend S3: $FRONTEND_ENDPOINT"

# ─── Preencher Secrets Manager ───

step "6/8 — Preenchendo Secrets Manager"

aws secretsmanager update-secret \
    --secret-id seedbox/auth \
    --secret-string "{\"passwordHash\":\"$PASSWORD_HASH\",\"jwtSecret\":\"$JWT_SECRET\"}" \
    --region "$AWS_REGION" >/dev/null

aws secretsmanager update-secret \
    --secret-id seedbox/transmission \
    --secret-string "{\"username\":\"seedbox\",\"password\":\"$TRANSMISSION_PASSWORD\"}" \
    --region "$AWS_REGION" >/dev/null

log "Secrets preenchidos"

# ─── Criar instância EC2 worker (parada) ───

step "7/8 — Criando instância EC2 worker"

SUBNET_ID=$(terraform output -raw public_subnet_id)

INSTANCE_ID=$(aws ec2 run-instances \
    --launch-template LaunchTemplateId="$LAUNCH_TEMPLATE_ID" \
    --subnet-id "$SUBNET_ID" \
    --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"persistent","InstanceInterruptionBehavior":"stop"}}' \
    --count 1 \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region "$AWS_REGION")

log "Instância criada: $INSTANCE_ID"

# Parar a instância (será ligada sob demanda)
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" >/dev/null 2>&1 || true
aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" 2>/dev/null || true

log "Instância parada (será ligada sob demanda)"

# Atualizar Lambda env vars com EC2_INSTANCE_ID
API_FUNCTION="${PROJECT_NAME}-api"
TRIGGER_FUNCTION="${PROJECT_NAME}-worker-trigger"

aws lambda update-function-configuration \
    --function-name "$API_FUNCTION" \
    --environment "Variables={S3_BUCKET=$DATA_BUCKET,EC2_INSTANCE_ID=$INSTANCE_ID,AUTH_SECRET_NAME=seedbox/auth,ALLOWED_ORIGIN=$ALLOWED_ORIGIN,AWS_REGION_NAME=$AWS_REGION,WORKER_TRIGGER_FUNCTION=$TRIGGER_FUNCTION}" \
    --region "$AWS_REGION" >/dev/null

aws lambda update-function-configuration \
    --function-name "$TRIGGER_FUNCTION" \
    --environment "Variables={EC2_INSTANCE_ID=$INSTANCE_ID,AWS_REGION_NAME=$AWS_REGION}" \
    --region "$AWS_REGION" >/dev/null

log "Lambdas atualizadas com EC2_INSTANCE_ID"

# ─── Build e deploy frontend ───

step "8/8 — Build e deploy do frontend"

cd "$FRONTEND_DIR"

# Criar .env.production com API URL real
cat > .env.production <<EOF
VITE_API_URL=$API_GATEWAY_URL
EOF

npm install
npm run build

# Deploy para S3
aws s3 sync dist/assets/ "s3://$FRONTEND_BUCKET/assets/" \
    --cache-control "max-age=31536000,public,immutable" \
    --delete --region "$AWS_REGION"

aws s3 cp dist/index.html "s3://$FRONTEND_BUCKET/index.html" \
    --cache-control "no-cache,no-store,must-revalidate" \
    --region "$AWS_REGION"

aws s3 sync dist/ "s3://$FRONTEND_BUCKET/" \
    --exclude "assets/*" --exclude "index.html" \
    --cache-control "max-age=3600,public" \
    --delete --region "$AWS_REGION"

log "Frontend deployed"

# ─── Resumo final ───

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Seedbox Serverless AWS — Deploy Completo!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  API Gateway:     ${CYAN}$API_GATEWAY_URL${NC}"
echo -e "  Frontend S3:     ${CYAN}http://$FRONTEND_ENDPOINT${NC}"
echo -e "  Frontend Bucket: ${CYAN}$FRONTEND_BUCKET${NC}"
echo -e "  Data Bucket:     ${CYAN}$DATA_BUCKET${NC}"
echo -e "  EC2 Instance:    ${CYAN}$INSTANCE_ID${NC}"
echo -e "  Region:          ${CYAN}$AWS_REGION${NC}"
echo ""
echo -e "${YELLOW}  Próximos passos (Cloudflare):${NC}"
echo -e "  1. CNAME  seedbox        → $FRONTEND_ENDPOINT  (Proxied)"
echo -e "  2. CNAME  api.seedbox    → ${API_GATEWAY_URL#https://}  (Proxied)"
echo -e "  3. SSL: Full (frontend), Full strict (API)"
echo -e "  4. Cache Rules conforme docs/infrastructure/cloudflare-setup.md"
echo ""
echo -e "  Testar API: ${CYAN}curl -X POST $API_GATEWAY_URL/auth/login -d '{\"password\":\"...\"}' -H 'Content-Type: application/json'${NC}"
echo ""
