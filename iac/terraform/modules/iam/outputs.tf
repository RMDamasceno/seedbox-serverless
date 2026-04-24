output "api_lambda_role_arn" {
  description = "ARN da role da Lambda API"
  value       = aws_iam_role.api_lambda.arn
}

output "authorizer_lambda_role_arn" {
  description = "ARN da role da Lambda Authorizer"
  value       = aws_iam_role.authorizer_lambda.arn
}

output "worker_trigger_lambda_role_arn" {
  description = "ARN da role da Lambda Worker Trigger"
  value       = aws_iam_role.worker_trigger_lambda.arn
}

output "worker_ec2_role_arn" {
  description = "ARN da role do Worker EC2"
  value       = aws_iam_role.worker_ec2.arn
}

output "worker_instance_profile_name" {
  description = "Nome do Instance Profile do Worker"
  value       = aws_iam_instance_profile.worker.name
}

output "auth_secret_arn" {
  description = "ARN do secret de autenticação"
  value       = aws_secretsmanager_secret.auth.arn
}

output "transmission_secret_arn" {
  description = "ARN do secret do Transmission"
  value       = aws_secretsmanager_secret.transmission.arn
}
