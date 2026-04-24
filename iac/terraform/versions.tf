terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 5.80"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.0, < 2.7"
    }
  }

  # Backend local para deploy inicial.
  # backend "s3" {
  #   bucket         = "seedbox-terraform-state"
  #   key            = "seedbox-serverless/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "seedbox-terraform-locks"
  # }
}
