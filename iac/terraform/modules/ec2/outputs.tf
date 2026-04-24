output "security_group_id" {
  description = "ID do Security Group do worker"
  value       = aws_security_group.worker.id
}

output "launch_template_id" {
  description = "ID do Launch Template"
  value       = aws_launch_template.worker.id
}

output "launch_template_latest_version" {
  description = "Última versão do Launch Template"
  value       = aws_launch_template.worker.latest_version
}
