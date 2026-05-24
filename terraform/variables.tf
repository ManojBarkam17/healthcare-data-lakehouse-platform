# =============================================================================
# Variables — Healthcare Data Lakehouse
# =============================================================================
# All configurable parameters in one place.
# Override via terraform.tfvars or -var flags.
# =============================================================================

variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "healthcare-lakehouse"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# S3 / Data Lake
# ---------------------------------------------------------------------------
variable "enable_s3_versioning" {
  description = "Enable versioning on data lake buckets"
  type        = bool
  default     = true
}

variable "bronze_lifecycle_days" {
  description = "Days before Bronze data transitions to Glacier"
  type        = number
  default     = 365
}

variable "silver_lifecycle_days" {
  description = "Days before Silver data transitions to Glacier"
  type        = number
  default     = 730
}

# ---------------------------------------------------------------------------
# Redshift Serverless
# ---------------------------------------------------------------------------
variable "redshift_base_capacity" {
  description = "Redshift Serverless base RPU capacity (8-512)"
  type        = number
  default     = 8
}

variable "redshift_max_capacity" {
  description = "Redshift Serverless max RPU capacity"
  type        = number
  default     = 32
}

variable "redshift_admin_username" {
  description = "Redshift admin username"
  type        = string
  default     = "lakehouse_admin"
  sensitive   = true
}

variable "redshift_admin_password" {
  description = "Redshift admin password — use Secrets Manager in production"
  type        = string
  sensitive   = true
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (min 2 for Redshift)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# ---------------------------------------------------------------------------
# Glue
# ---------------------------------------------------------------------------
variable "glue_crawler_schedule" {
  description = "Cron expression for Glue crawler (default: daily 6 AM UTC)"
  type        = string
  default     = "cron(0 6 * * ? *)"
}
