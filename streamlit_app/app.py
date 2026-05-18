"""Healthcare Data Lakehouse — Analytics Dashboard.

Multi-page Streamlit app powered by DuckDB.
Deployable free on Streamlit Community Cloud.

Usage:
    streamlit run streamlit_app/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st.set_page_config(
    page_title="Healthcare Data Lakehouse",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Healthcare Lakehouse")
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Medallion Architecture Demo**

    Bronze → Silver → Gold → Analytics

    Built with PySpark, Delta Lake, dbt, and DuckDB.

    [GitHub Repo](https://github.com/ManojBarkam17/healthcare-data-lakehouse-platform)
    """
)

# ---------------------------------------------------------------------------
# Home Page
# ---------------------------------------------------------------------------

st.title("Healthcare Data Lakehouse Platform")
st.markdown("#### Interactive analytics dashboard powered by a medallion architecture pipeline")

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📊")
    st.markdown("**Claims Analytics**")
    st.caption("Monthly trends, payer mix, financial KPIs")

with col2:
    st.markdown("### 🎯")
    st.markdown("**Member Risk**")
    st.caption("Risk stratification, cost distribution")

with col3:
    st.markdown("### 🏆")
    st.markdown("**Provider Scorecard**")
    st.caption("Performance tiers, denial rates")

with col4:
    st.markdown("### 🏥")
    st.markdown("**Utilization**")
    st.caption("Admissions, LOS, facility metrics")

st.markdown("---")

st.markdown(
    """
    ### Architecture Overview

    | Layer | Technology | Purpose |
    |-------|-----------|---------|
    | **Bronze** | PySpark + Delta Lake | Raw ingestion with metadata |
    | **Silver** | PySpark + Delta Lake | Cleansed, deduplicated, PHI masked |
    | **Gold** | PySpark → DuckDB | Star schema dimensions & facts |
    | **Analytics** | dbt + DuckDB | 16 transformation models |
    | **Dashboard** | Streamlit | Interactive visualization |

    Use the sidebar to navigate between analytics pages.
    """
)
