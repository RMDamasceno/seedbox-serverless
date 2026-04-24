variable "aws_region" {
  description = "Região AWS para todos os recursos"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "ID da conta AWS"
  type        = string
}

variable "project_name" {
  description = "Nome do projeto (usado como prefixo em recursos)"
  type        = string
  default     = "seedbox"
}

variable "environment" {
  description = "Ambiente de deploy (dev, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment deve ser 'dev' ou 'prod'."
  }
}

variable "allowed_origin" {
  description = "Domínio Cloudflare do frontend para CORS (ex: https://seedbox.dominio.com)"
  type        = string
  default     = "*"
}

variable "tags" {
  description = "Tags padrão aplicadas a todos os recursos"
  type        = map(string)
  default     = {}
}

locals {
  default_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  bucket_name          = "${var.project_name}-${var.aws_account_id}"
  frontend_bucket_name = "${var.project_name}-frontend-${var.aws_account_id}"
}
