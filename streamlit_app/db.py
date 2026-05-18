"""Database connection helper for Streamlit pages.

Provides a cached DuckDB connection that works both locally
and on Streamlit Community Cloud (using sample data).
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a read-only DuckDB connection.

    Looks for the Gold warehouse first, then falls back to sample data
    for Streamlit Cloud deployment.
    """
    # Try full warehouse first (local dev)
    gold_db = Path(__file__).resolve().parent.parent / "data" / "gold" / "healthcare_warehouse.duckdb"
    if gold_db.exists():
        return duckdb.connect(str(gold_db), read_only=True)

    # Fall back to sample data (Streamlit Cloud)
    sample_db = Path(__file__).resolve().parent.parent / "data" / "sample" / "sample_warehouse.duckdb"
    if sample_db.exists():
        return duckdb.connect(str(sample_db), read_only=True)

    st.error("No database found. Run the pipeline first: `run_pipeline.bat all`")
    st.stop()


def query(sql: str) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame."""
    con = get_connection()
    return con.execute(sql).fetchdf()


def get_tables() -> list[str]:
    """List all tables in the connected database."""
    con = get_connection()
    result = con.execute("SHOW TABLES").fetchall()
    return [row[0] for row in result]
