"""Quick script to export Gold Delta/Parquet tables to DuckDB."""
import duckdb
from pathlib import Path

gold_path = Path("data/gold")
db_path = gold_path / "healthcare_warehouse.duckdb"

# Remove old empty file
if db_path.exists():
    db_path.unlink()

con = duckdb.connect(str(db_path))

tables = [
    "dim_member", "dim_provider", "dim_payer",
    "dim_diagnosis", "dim_procedure",
    "fact_claims", "fact_adt_events",
]

for table in tables:
    parquet_dir = gold_path / table
    # Check for parquet files (non-partitioned tables)
    parquet_files = list(parquet_dir.glob("*.parquet"))
    # Also check for partitioned tables (e.g., service_year_month=2024-01/*.parquet)
    nested_parquet = list(parquet_dir.glob("**/*.parquet"))

    if parquet_files:
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM parquet_scan('data/gold/{table}/*.parquet')")
    elif nested_parquet:
        # Partitioned table — use recursive glob
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM parquet_scan('data/gold/{table}/**/*.parquet', hive_partitioning=true)")
    else:
        print(f"  {table}: NO PARQUET FILES FOUND")
        continue

    count = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {count:,} rows")

# Copy to sample for Streamlit Cloud
import shutil
sample_path = Path("data/sample/sample_warehouse.duckdb")
sample_path.parent.mkdir(parents=True, exist_ok=True)
con.close()
shutil.copy(str(db_path), str(sample_path))
print(f"\nExported to {db_path} and copied to {sample_path}")
