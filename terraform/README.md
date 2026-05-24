# Terraform — Healthcare Data Lakehouse (AWS)

Infrastructure-as-Code for a HIPAA-eligible healthcare data lakehouse on AWS.

## Resources Provisioned

| Resource | Purpose |
|----------|---------|
| **S3 Buckets** (x4) | Bronze, Silver, Gold data layers + ETL scripts |
| **KMS Key** | Encryption at rest for all PHI data |
| **AWS Glue Catalog** | Centralized metadata / schema registry |
| **Glue Crawlers** (x2) | Auto-discover Bronze and Gold schemas |
| **Redshift Serverless** | Analytics warehouse with Spectrum for S3 queries |
| **VPC + Subnets** | Private networking (no public endpoints) |
| **IAM Roles** (x2) | Least-privilege for Glue and Redshift |
| **S3 VPC Endpoint** | Keeps S3 traffic off public internet |

## Quick Start

```bash
# 1. Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 2. Initialize
terraform init

# 3. Plan
terraform plan -out=tfplan

# 4. Apply
terraform apply tfplan
```

## Security Features

- **KMS encryption** on all S3 buckets (server-side, key rotation enabled)
- **S3 public access blocked** on every bucket
- **VPC endpoint** for S3 — traffic never touches public internet
- **Private subnets only** — Redshift is not publicly accessible
- **Least-privilege IAM** — Glue and Redshift get only the permissions they need
- **Sensitive variables** marked as `sensitive` in Terraform (passwords, usernames)
- **Lifecycle policies** auto-archive Bronze/Silver to Glacier

## Cost Optimization

- Redshift Serverless with `base_capacity = 8 RPU` (scales to zero when idle)
- S3 Intelligent-Tiering via lifecycle rules
- Glue crawlers on schedule (not continuous)
- `AUTO_SUSPEND` on all warehouses

## File Structure

```
terraform/
  main.tf                  # All resources (S3, VPC, IAM, Glue, Redshift)
  variables.tf             # Input variables with defaults and validation
  outputs.tf               # Exported values for downstream use
  terraform.tfvars.example # Template — copy to terraform.tfvars
```

> **Note**: This is a reference implementation for portfolio demonstration.
> Review security, compliance, and cost implications before production use.
