variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "api_lambda_role_arn" {
  description = "ARN da role da Lambda API"
  type        = string
}

variable "authorizer_lambda_role_arn" {
  description = "ARN da role da Lambda Authorizer"
  type        = string
}

variable "worker_trigger_lambda_role_arn" {
  description = "ARN da role da Lambda Worker Trigger"
  type        = string
}

variable "s3_bucket" {
  description = "Nome do bucket S3 principal"
  type        = string
}

variable "ec2_instance_id" {
  description = "ID da instância EC2 worker (preenchido após primeiro deploy)"
  type        = string
  default     = ""
}

variable "auth_secret_name" {
  description = "Nome do secret de autenticação"
  type        = string
  default     = "seedbox/auth"
}

variable "allowed_origin" {
  description = "Domínio Cloudflare para CORS"
  type        = string
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
}
