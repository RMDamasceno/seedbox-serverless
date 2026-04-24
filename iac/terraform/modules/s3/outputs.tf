output "data_bucket_name" {
  description = "Nome do bucket principal de dados"
  value       = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  description = "ARN do bucket principal de dados"
  value       = aws_s3_bucket.data.arn
}

output "frontend_bucket_name" {
  description = "Nome do bucket do frontend"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  description = "ARN do bucket do frontend"
  value       = aws_s3_bucket.frontend.arn
}

output "frontend_website_endpoint" {
  description = "Endpoint do website hosting do frontend"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}
