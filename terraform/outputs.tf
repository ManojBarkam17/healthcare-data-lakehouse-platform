# =============================================================================
# Outputs — Healthcare Data Lakehouse
# =============================================================================
# Values exposed after terraform apply for use by pipelines and dashboards.
# =============================================================================

# ---------------------------------------------------------------------------
# S3 Buckets
# ---------------------------------------------------------------------------
output "s3_bucket_bronze" {
  description = "Bronze layer S3 bucket name"
  value       = aws_s3_bucket.data_lake["bronze"].id
}

output "s3_bucket_silver" {
  description = "Silver layer S3 bucket name"
  value       = aws_s3_bucket.data_lake["silver"].id
}

output "s3_bucket_gold" {
  description = "Gold layer S3 bucket name"
  value       = aws_s3_bucket.data_lake["gold"].id
}

output "s3_bucket_scripts" {
  description = "ETL scripts bucket name"
  value       = aws_s3_bucket.scripts.id
}

# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------
output "glue_catalog_database" {
  description = "Glue Data Catalog database name"
  value       = aws_glue_catalog_database.lakehouse.name
}

output "glue_role_arn" {
  description = "IAM role ARN for Glue jobs and crawlers"
  value       = aws_iam_role.glue.arn
}

# ---------------------------------------------------------------------------
# Redshift Serverless
# ---------------------------------------------------------------------------
output "redshift_workgroup_endpoint" {
  description = "Redshift Serverless workgroup endpoint"
  value       = aws_redshiftserverless_workgroup.lakehouse.endpoint
}

output "redshift_namespace" {
  description = "Redshift Serverless namespace name"
  value       = aws_redshiftserverless_namespace.lakehouse.namespace_name
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "security_group_id" {
  description = "Data lake security group ID"
  value       = aws_security_group.data_lake.id
}

# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------
output "kms_key_arn" {
  description = "KMS key ARN for data encryption"
  value       = aws_kms_key.data_lake.arn
}
