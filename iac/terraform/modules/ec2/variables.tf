variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "vpc_id" {
  description = "ID da VPC"
  type        = string
}

variable "subnet_id" {
  description = "ID da subnet para a instância"
  type        = string
}

variable "instance_profile_name" {
  description = "Nome do Instance Profile IAM"
  type        = string
}

variable "instance_type" {
  description = "Tipo da instância EC2"
  type        = string
  default     = "t3.medium"
}

variable "disk_size_gb" {
  description = "Tamanho do disco em GB"
  type        = number
  default     = 200
}

variable "s3_bucket" {
  description = "Nome do bucket S3 principal"
  type        = string
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
}

variable "transmission_secret_name" {
  description = "Nome do secret do Transmission no Secrets Manager"
  type        = string
  default     = "seedbox/transmission"
}
