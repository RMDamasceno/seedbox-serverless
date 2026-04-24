provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.default_tags
  }
}

# ─── Módulo VPC ───

module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  aws_region   = var.aws_region
}

# ─── Módulo S3 ───

module "s3" {
  source = "./modules/s3"

  bucket_name          = local.bucket_name
  frontend_bucket_name = local.frontend_bucket_name
}

# ─── Módulo IAM ───

module "iam" {
  source = "./modules/iam"

  project_name    = var.project_name
  data_bucket_arn = module.s3.data_bucket_arn
  aws_region      = var.aws_region
  aws_account_id  = var.aws_account_id
}

# ─── Módulo EC2 ───

module "ec2" {
  source = "./modules/ec2"

  project_name          = var.project_name
  vpc_id                = module.vpc.vpc_id
  subnet_id             = module.vpc.public_subnet_id
  instance_profile_name = module.iam.worker_instance_profile_name
  s3_bucket             = module.s3.data_bucket_name
  aws_region            = var.aws_region
}

# ─── Módulo Lambda ───

module "lambda" {
  source = "./modules/lambda"

  project_name                   = var.project_name
  api_lambda_role_arn            = module.iam.api_lambda_role_arn
  authorizer_lambda_role_arn     = module.iam.authorizer_lambda_role_arn
  worker_trigger_lambda_role_arn = module.iam.worker_trigger_lambda_role_arn
  s3_bucket                      = module.s3.data_bucket_name
  ec2_instance_id                 = var.ec2_instance_id
  allowed_origin                 = var.allowed_origin
  aws_region                     = var.aws_region
}
