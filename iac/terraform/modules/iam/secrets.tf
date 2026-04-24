resource "aws_secretsmanager_secret" "auth" {
  name        = "seedbox/auth"
  description = "JWT secret e password hash para autenticação"
}

resource "aws_secretsmanager_secret_version" "auth" {
  secret_id = aws_secretsmanager_secret.auth.id
  secret_string = jsonencode({
    passwordHash = "PLACEHOLDER_FILL_MANUALLY"
    jwtSecret    = "PLACEHOLDER_FILL_MANUALLY"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "transmission" {
  name        = "seedbox/transmission"
  description = "Credenciais do Transmission daemon"
}

resource "aws_secretsmanager_secret_version" "transmission" {
  secret_id = aws_secretsmanager_secret.transmission.id
  secret_string = jsonencode({
    username = "seedbox"
    password = "PLACEHOLDER_FILL_MANUALLY"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
