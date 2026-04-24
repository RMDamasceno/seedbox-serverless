# VPC
output "vpc_id" {
  description = "ID da VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_id" {
  description = "ID da subnet pública"
  value       = module.vpc.public_subnet_id
}

# S3
output "data_bucket_name" {
  description = "Nome do bucket principal"
  value       = module.s3.data_bucket_name
}

output "frontend_bucket_name" {
  description = "Nome do bucket frontend"
  value       = module.s3.frontend_bucket_name
}

output "frontend_website_endpoint" {
  description = "Endpoint do website hosting"
  value       = module.s3.frontend_website_endpoint
}

# EC2
output "worker_security_group_id" {
  description = "ID do Security Group do worker"
  value       = module.ec2.security_group_id
}

output "worker_launch_template_id" {
  description = "ID do Launch Template"
  value       = module.ec2.launch_template_id
}

# Lambda
output "api_gateway_url" {
  description = "URL do API Gateway"
  value       = module.lambda.api_gateway_url
}

output "api_function_arn" {
  description = "ARN da Lambda API"
  value       = module.lambda.api_function_arn
}
