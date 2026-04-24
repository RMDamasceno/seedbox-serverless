terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend local para deploy inicial. Migrar para S3 após primeiro apply.
  # backend "s3" {
  #   bucket         = "seedbox-terraform-state"
  #   key            = "seedbox-serverless/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "seedbox-terraform-locks"
  # }
}
