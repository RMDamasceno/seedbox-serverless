# Trust policy para Lambda
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Trust policy para EC2
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# ─── 1. seedbox-api-lambda-role ───

resource "aws_iam_role" "api_lambda" {
  name               = "${var.project_name}-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "api_lambda" {
  name = "${var.project_name}-api-lambda-policy"
  role = aws_iam_role.api_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3QueueAndIdempotency"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:CopyObject"]
        Resource = "${var.data_bucket_arn}/queue/*"
      },
      {
        Sid      = "S3Idempotency"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:HeadObject"]
        Resource = "${var.data_bucket_arn}/idempotency/*"
      },
      {
        Sid      = "S3Torrents"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${var.data_bucket_arn}/torrents/*"
      },
      {
        Sid    = "S3Downloads"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:DeleteObject"]
        Resource = "${var.data_bucket_arn}/downloads/*"
      },
      {
        Sid      = "S3List"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = var.data_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["queue/*", "idempotency/*", "torrents/*", "downloads/*"]
          }
        }
      },
      {
        Sid      = "SecretsManager"
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:seedbox/*"
      },
      {
        Sid      = "EC2Worker"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ec2:StartInstances"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Project" = var.project_name
          }
        }
      },
      {
        Sid      = "EC2Describe"
        Effect   = "Allow"
        Action   = "ec2:DescribeInstances"
        Resource = "*"
      },
      {
        Sid      = "LambdaInvoke"
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.project_name}-worker-trigger"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_lambda_logs" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ─── 2. seedbox-authorizer-lambda-role ───

resource "aws_iam_role" "authorizer_lambda" {
  name               = "${var.project_name}-authorizer-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "authorizer_lambda" {
  name = "${var.project_name}-authorizer-lambda-policy"
  role = aws_iam_role.authorizer_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SecretsManager"
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:seedbox/auth*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "authorizer_lambda_logs" {
  role       = aws_iam_role.authorizer_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ─── 3. seedbox-worker-trigger-lambda-role ───

resource "aws_iam_role" "worker_trigger_lambda" {
  name               = "${var.project_name}-worker-trigger-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "worker_trigger_lambda" {
  name = "${var.project_name}-worker-trigger-lambda-policy"
  role = aws_iam_role.worker_trigger_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EC2Control"
        Effect   = "Allow"
        Action   = ["ec2:StartInstances", "ec2:StopInstances", "ec2:DescribeInstances"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Project" = var.project_name
          }
        }
      },
      {
        Sid      = "EC2Describe"
        Effect   = "Allow"
        Action   = "ec2:DescribeInstances"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "worker_trigger_lambda_logs" {
  role       = aws_iam_role.worker_trigger_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ─── 4. seedbox-worker-ec2-role ───

resource "aws_iam_role" "worker_ec2" {
  name               = "${var.project_name}-worker-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy" "worker_ec2" {
  name = "${var.project_name}-worker-ec2-policy"
  role = aws_iam_role.worker_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "S3Queue"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:CopyObject"]
        Resource = "${var.data_bucket_arn}/queue/*"
      },
      {
        Sid      = "S3Downloads"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${var.data_bucket_arn}/downloads/*"
      },
      {
        Sid      = "S3Torrents"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${var.data_bucket_arn}/torrents/*"
      },
      {
        Sid      = "S3List"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = var.data_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["queue/*", "downloads/*", "torrents/*", "worker/*"]
          }
        }
      },
      {
        Sid      = "S3WorkerScripts"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${var.data_bucket_arn}/worker/*"
      },
      {
        Sid      = "EC2StopSelf"
        Effect   = "Allow"
        Action   = "ec2:StopInstances"
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:ResourceTag/Name" = "${var.project_name}-worker"
          }
        }
      },
      {
        Sid      = "SecretsManager"
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:seedbox/transmission*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "worker" {
  name = "${var.project_name}-worker-instance-profile"
  role = aws_iam_role.worker_ec2.name
}

resource "aws_iam_role_policy_attachment" "worker_ssm" {
  role       = aws_iam_role.worker_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
