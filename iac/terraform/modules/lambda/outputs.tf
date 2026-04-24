output "api_function_arn" {
  description = "ARN da Lambda API"
  value       = aws_lambda_function.api.arn
}

output "api_invoke_arn" {
  description = "Invoke ARN da Lambda API"
  value       = aws_lambda_function.api.invoke_arn
}

output "authorizer_function_arn" {
  description = "ARN da Lambda Authorizer"
  value       = aws_lambda_function.authorizer.arn
}

output "authorizer_invoke_arn" {
  description = "Invoke ARN da Lambda Authorizer"
  value       = aws_lambda_function.authorizer.invoke_arn
}

output "worker_trigger_function_arn" {
  description = "ARN da Lambda Worker Trigger"
  value       = aws_lambda_function.worker_trigger.arn
}

output "api_gateway_url" {
  description = "URL do API Gateway"
  value       = aws_apigatewayv2_api.main.api_endpoint
}
