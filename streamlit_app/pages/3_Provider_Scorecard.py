"""Provider Scorecard — Performance tiers, denial rates, efficiency."""

import streamlit as st
import plotly.express as px

from db import query

st.set_page_config(page_title="Provider Scorecard", page_icon="🏆", layout="wide")
st.title("🏆 Provider Scorecard")

# ---------------------------------------------------------------------------
# Provider Performance Data
# ---------------------------------------------------------------------------

provider_data = query("""
    SELECT
        p.provider_id,
        p.first_name || ' ' || p.last_name as provider_name,
        p.specialty,
        p.facility_name,
        p.state,
        count(distinct f.claim_id) as total_claims,
        count(distinct f.member_id) as unique_patients,
        sum(f.line_charge_amount) as total_charged,
        sum(f.paid_amount) as total_paid,
        round(avg(f.paid_amount / nullif(f.line_charge_amount, 0)), 3) as payment_ratio,
        count(distinct case when f.claim_status = 'denied' then f.claim_id end) as denied_claims,
        round(
            count(distinct case when f.claim_status = 'denied' then f.claim_id end) * 100.0
            / nullif(count(distinct f.claim_id), 0), 1
        ) as denial_rate_pct,
        CASE
            WHEN count(distinct case when f.claim_status = 'denied' then f.claim_id end) * 100.0
                 / nullif(count(distinct f.claim_id), 0) <= 10
                 AND avg(f.paid_amount / nullif(f.line_charge_amount, 0)) >= 0.7
                THEN 'Top Performer'
            WHEN count(distinct case when f.claim_status = 'denied' then f.claim_id end) * 100.0
                 / nullif(count(distinct f.claim_id), 0) <= 20
                THEN 'Meets Expectations'
            WHEN count(distinct case when f.claim_status = 'denied' then f.claim_id end) * 100.0
                 / nullif(count(distinct f.claim_id), 0) <= 30
                THEN 'Needs Improvement'
            ELSE 'Under Review'
        END as performance_tier
    FROM fact_claims f
    JOIN dim_provider p ON f.provider_id = p.provider_id
    GROUP BY p.provider_id, p.first_name, p.last_name, p.specialty, p.facility_name, p.state
    ORDER BY total_claims DESC
""")

# KPI row
tier_counts = provider_data["performance_tier"].value_counts()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Top Performers", tier_counts.get("Top Performer", 0))
with col2:
    st.metric("Meets Expectations", tier_counts.get("Meets Expectations", 0))
with col3:
    st.metric("Needs Improvement", tier_counts.get("Needs Improvement", 0))
with col4:
    st.metric("Under Review", tier_counts.get("Under Review", 0))

st.markdown("---")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

col_f1, col_f2 = st.columns(2)
with col_f1:
    specialties = ["All"] + sorted(provider_data["specialty"].dropna().unique().tolist())
    selected_specialty = st.selectbox("Filter by Specialty", specialties)
with col_f2:
    tiers = ["All"] + sorted(provider_data["performance_tier"].dropna().unique().tolist())
    selected_tier = st.selectbox("Filter by Performance Tier", tiers)

filtered = provider_data.copy()
if selected_specialty != "All":
    filtered = filtered[filtered["specialty"] == selected_specialty]
if selected_tier != "All":
    filtered = filtered[filtered["performance_tier"] == selected_tier]

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

tier_colors = {
    "Top Performer": "#59a14f",
    "Meets Expectations": "#4e79a7",
    "Needs Improvement": "#f28e2b",
    "Under Review": "#e15759",
}

with col_left:
    st.subheader("Denial Rate vs Volume")
    fig = px.scatter(filtered, x="total_claims", y="denial_rate_pct",
                     color="performance_tier",
                     color_discrete_map=tier_colors,
                     size="total_paid",
                     hover_name="provider_name",
                     hover_data=["specialty", "facility_name"],
                     labels={"total_claims": "Total Claims",
                             "denial_rate_pct": "Denial Rate (%)"})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Performance by Specialty")
    specialty_agg = filtered.groupby("specialty").agg(
        providers=("provider_id", "count"),
        avg_denial=("denial_rate_pct", "mean"),
        avg_payment=("payment_ratio", "mean"),
    ).reset_index().sort_values("avg_denial")

    fig = px.bar(specialty_agg, x="specialty", y="avg_denial",
                 color="avg_payment", color_continuous_scale="RdYlGn",
                 text_auto=".1f",
                 labels={"avg_denial": "Avg Denial Rate (%)",
                         "avg_payment": "Avg Payment Ratio"})
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Provider Table
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader(f"Provider Details ({len(filtered)} providers)")

st.dataframe(
    filtered[["provider_name", "specialty", "facility_name", "performance_tier",
              "total_claims", "unique_patients", "total_charged", "total_paid",
              "denial_rate_pct", "payment_ratio"]].sort_values("total_claims", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "total_charged": st.column_config.NumberColumn("Total Charged", format="$%,.0f"),
        "total_paid": st.column_config.NumberColumn("Total Paid", format="$%,.0f"),
        "denial_rate_pct": st.column_config.NumberColumn("Denial Rate %", format="%.1f%%"),
        "payment_ratio": st.column_config.ProgressColumn("Payment Ratio", min_value=0, max_value=1),
    }
)
