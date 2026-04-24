# Bucket principal de dados (estado + arquivos)
resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "expire-idempotency-keys"
    status = "Enabled"

    filter {
      prefix = "idempotency/"
    }

    expiration {
      days = 1
    }
  }

  rule {
    id     = "expire-torrent-files"
    status = "Enabled"

    filter {
      prefix = "torrents/"
    }

    expiration {
      days = 7
    }
  }

  rule {
    id     = "intelligent-tiering-downloads"
    status = "Enabled"

    filter {
      prefix = "downloads/completed/"
    }

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
  }
}
