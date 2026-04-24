# Pacotes ZIP para deploy
data "archive_file" "api" {
  type        = "zip"
  source_dir  = "${path.root}/../../backend/lambda/api"
  output_path = "${path.module}/packages/api.zip"
}

data "archive_file" "authorizer" {
  type        = "zip"
  source_dir  = "${path.root}/../../backend/lambda/authorizer"
  output_path = "${path.module}/packages/authorizer.zip"
}

data "archive_file" "worker_trigger" {
  type        = "zip"
  source_dir  = "${path.root}/../../backend/lambda/worker-trigger"
  output_path = "${path.module}/packages/worker-trigger.zip"
}

# ─── Lambda: seedbox-api ───

resource "aws_lambda_function" "api" {
  function_name    = "${var.project_name}-api"
  role             = var.api_lambda_role_arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 30
  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256

  environment {
    variables = {
      S3_BUCKET        = var.s3_bucket
      EC2_INSTANCE_ID  = var.ec2_instance_id
      AUTH_SECRET_NAME = var.auth_secret_name
      ALLOWED_ORIGIN   = var.allowed_origin
      AWS_REGION_NAME  = var.aws_region
      WORKER_TRIGGER_FUNCTION = "${var.project_name}-worker-trigger"
    }
  }

  tags = {
    Name = "${var.project_name}-api"
  }
}

# ─── Lambda: seedbox-authorizer ───

resource "aws_lambda_function" "authorizer" {
  function_name    = "${var.project_name}-authorizer"
  role             = var.authorizer_lambda_role_arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 5
  filename         = data.archive_file.authorizer.output_path
  source_code_hash = data.archive_file.authorizer.output_base64sha256

  environment {
    variables = {
      AUTH_SECRET_NAME = var.auth_secret_name
    }
  }

  tags = {
    Name = "${var.project_name}-authorizer"
  }
}

# ─── Lambda: seedbox-worker-trigger ───

resource "aws_lambda_function" "worker_trigger" {
  function_name    = "${var.project_name}-worker-trigger"
  role             = var.worker_trigger_lambda_role_arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 10
  filename         = data.archive_file.worker_trigger.output_path
  source_code_hash = data.archive_file.worker_trigger.output_base64sha256

  environment {
    variables = {
      EC2_INSTANCE_ID = var.ec2_instance_id
      AWS_REGION_NAME = var.aws_region
    }
  }

  tags = {
    Name = "${var.project_name}-worker-trigger"
  }
}
