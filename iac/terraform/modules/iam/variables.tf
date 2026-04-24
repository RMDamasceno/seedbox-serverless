variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "data_bucket_arn" {
  description = "ARN do bucket principal de dados"
  type        = string
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
}

variable "aws_account_id" {
  description = "ID da conta AWS"
  type        = string
}
