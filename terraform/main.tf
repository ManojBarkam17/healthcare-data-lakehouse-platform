# =============================================================================
# Main — Healthcare Data Lakehouse (AWS)
# =============================================================================
# Production-grade infrastructure for a HIPAA-eligible data lakehouse.
#
# Resources:
#   - S3 buckets (Bronze / Silver / Gold layers + scripts)
#   - AWS Glue Data Catalog + Crawlers
#   - Redshift Serverless (analytics warehouse)
#   - VPC + private subnets
#   - IAM roles with least-privilege policies
#   - KMS encryption key for PHI at rest
#
# NOTE: This is a reference implementation for portfolio demonstration.
#       Review security and compliance requirements before production use.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment for team collaboration:
  # backend "s3" {
  #   bucket         = "healthcare-lakehouse-tfstate"
  #   key            = "infrastructure/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = var.project
        Environment = var.environment
        ManagedBy   = "terraform"
        Compliance  = "HIPAA"
      },
      var.tags
    )
  }
}

# ---------------------------------------------------------------------------
# Local values
# ---------------------------------------------------------------------------
locals {
  name_prefix = "${var.project}-${var.environment}"

  medallion_layers = ["bronze", "silver", "gold"]
}

# =============================================================================
# KMS — Encryption key for PHI data at rest
# =============================================================================
resource "aws_kms_key" "data_lake" {
  description             = "Encryption key for ${local.name_prefix} data lake"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "data_lake" {
  name          = "alias/${local.name_prefix}-data-lake"
  target_key_id = aws_kms_key.data_lake.key_id
}

data "aws_caller_identity" "current" {}

# =============================================================================
# S3 — Data Lake Buckets (one per medallion layer)
# =============================================================================
resource "aws_s3_bucket" "data_lake" {
  for_each = toset(local.medallion_layers)

  bucket        = "${local.name_prefix}-${each.key}-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.environment != "prod"
}

resource "aws_s3_bucket_versioning" "data_lake" {
  for_each = aws_s3_bucket.data_lake

  bucket = each.value.id
  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  for_each = aws_s3_bucket.data_lake

  bucket = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  for_each = aws_s3_bucket.data_lake

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "bronze" {
  bucket = aws_s3_bucket.data_lake["bronze"].id

  rule {
    id     = "archive-old-bronze"
    status = "Enabled"

    transition {
      days          = var.bronze_lifecycle_days
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "silver" {
  bucket = aws_s3_bucket.data_lake["silver"].id

  rule {
    id     = "archive-old-silver"
    status = "Enabled"

    transition {
      days          = var.silver_lifecycle_days
      storage_class = "GLACIER"
    }
  }
}

# Scripts bucket (Glue ETL scripts, Spark JARs)
resource "aws_s3_bucket" "scripts" {
  bucket        = "${local.name_prefix}-scripts-${data.aws_caller_identity.current.account_id}"
  force_destroy = var.environment != "prod"
}

resource "aws_s3_bucket_public_access_block" "scripts" {
  bucket                  = aws_s3_bucket.scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# VPC — Private networking for Redshift + Glue
# =============================================================================
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = { Name = "${local.name_prefix}-private-${count.index + 1}" }
}

resource "aws_security_group" "data_lake" {
  name_prefix = "${local.name_prefix}-data-lake-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for data lake services"

  # Allow all traffic within the security group
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-data-lake-sg" }
}

# S3 VPC endpoint (keeps traffic off public internet)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  tags = { Name = "${local.name_prefix}-s3-endpoint" }
}

# =============================================================================
# IAM — Roles with least-privilege policies
# =============================================================================

# Glue service role
resource "aws_iam_role" "glue" {
  name = "${local.name_prefix}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "glue_data_lake" {
  name = "${local.name_prefix}-glue-data-lake"
  role = aws_iam_role.glue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3DataLakeAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = flatten([
          for bucket in aws_s3_bucket.data_lake : [
            bucket.arn,
            "${bucket.arn}/*",
          ]
        ])
      },
      {
        Sid    = "S3ScriptsRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.scripts.arn,
          "${aws_s3_bucket.scripts.arn}/*",
        ]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
        ]
        Resource = [aws_kms_key.data_lake.arn]
      },
      {
        Sid    = "GlueCatalog"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase*",
          "glue:GetTable*",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:CreatePartition",
          "glue:BatchCreatePartition",
        ]
        Resource = ["*"]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# =============================================================================
# Glue — Data Catalog + Crawlers
# =============================================================================
resource "aws_glue_catalog_database" "lakehouse" {
  name        = replace(local.name_prefix, "-", "_")
  description = "Healthcare data lakehouse catalog (${var.environment})"
}

resource "aws_glue_crawler" "bronze" {
  name          = "${local.name_prefix}-bronze-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.lakehouse.name
  schedule      = var.glue_crawler_schedule

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake["bronze"].id}/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })
}

resource "aws_glue_crawler" "gold" {
  name          = "${local.name_prefix}-gold-crawler"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.lakehouse.name
  schedule      = var.glue_crawler_schedule

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake["gold"].id}/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
}

# =============================================================================
# Redshift Serverless — Analytics Warehouse
# =============================================================================
resource "aws_redshiftserverless_namespace" "lakehouse" {
  namespace_name      = replace(local.name_prefix, "-", "_")
  admin_username      = var.redshift_admin_username
  admin_user_password = var.redshift_admin_password
  db_name             = "healthcare_warehouse"
  kms_key_id          = aws_kms_key.data_lake.arn

  iam_roles = [aws_iam_role.redshift.arn]
}

resource "aws_redshiftserverless_workgroup" "lakehouse" {
  namespace_name = aws_redshiftserverless_namespace.lakehouse.namespace_name
  workgroup_name = "${local.name_prefix}-workgroup"
  base_capacity  = var.redshift_base_capacity
  max_capacity   = var.redshift_max_capacity

  security_group_ids = [aws_security_group.data_lake.id]
  subnet_ids         = aws_subnet.private[*].id

  publicly_accessible = false
}

# Redshift IAM role for Spectrum / S3 access
resource "aws_iam_role" "redshift" {
  name = "${local.name_prefix}-redshift-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "redshift.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "redshift_s3" {
  name = "${local.name_prefix}-redshift-s3-read"
  role = aws_iam_role.redshift.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3GoldRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_lake["gold"].arn,
          "${aws_s3_bucket.data_lake["gold"].arn}/*",
        ]
      },
      {
        Sid    = "GlueCatalogRead"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase*",
          "glue:GetTable*",
          "glue:GetPartitions",
        ]
        Resource = ["*"]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = [aws_kms_key.data_lake.arn]
      },
    ]
  })
}
