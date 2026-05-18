"""Member Risk Stratification — Risk tiers, cost distribution, demographics."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from db import query

st.set_page_config(page_title="Member Risk", page_icon="🎯", layout="wide")
st.title("🎯 Member Risk Stratification")

# ---------------------------------------------------------------------------
# Risk Tier Distribution
# ---------------------------------------------------------------------------

# Build risk tiers from claims data (since mart tables aren't in DuckDB yet)
risk_data = query("""
    WITH member_summary AS (
        SELECT
            f.member_id,
            m.gender,
            m.state,
            m.plan_type,
            count(distinct f.claim_id) as total_claims,
            sum(f.paid_amount) as total_paid,
            count(distinct f.diagnosis_code) as distinct_diagnoses
        FROM fact_claims f
        JOIN dim_member m ON f.member_id = m.member_id
        GROUP BY f.member_id, m.gender, m.state, m.plan_type
    ),
    risk_scored AS (
        SELECT *,
            percent_rank() OVER (ORDER BY total_paid) as spend_pctile,
            percent_rank() OVER (ORDER BY distinct_diagnoses) as complexity_pctile,
            percent_rank() OVER (ORDER BY total_claims) as util_pctile
        FROM member_summary
    )
    SELECT *,
        round(spend_pctile * 0.4 + complexity_pctile * 0.35 + util_pctile * 0.25, 4) as risk_score,
        CASE
            WHEN (spend_pctile * 0.4 + complexity_pctile * 0.35 + util_pctile * 0.25) >= 0.85 THEN 'Very High'
            WHEN (spend_pctile * 0.4 + complexity_pctile * 0.35 + util_pctile * 0.25) >= 0.65 THEN 'High'
            WHEN (spend_pctile * 0.4 + complexity_pctile * 0.35 + util_pctile * 0.25) >= 0.35 THEN 'Medium'
            ELSE 'Low'
        END as risk_tier
    FROM risk_scored
""")

# KPI row
col1, col2, col3, col4 = st.columns(4)

tier_counts = risk_data["risk_tier"].value_counts()
with col1:
    st.metric("Very High Risk", tier_counts.get("Very High", 0))
with col2:
    st.metric("High Risk", tier_counts.get("High", 0))
with col3:
    st.metric("Medium Risk", tier_counts.get("Medium", 0))
with col4:
    st.metric("Low Risk", tier_counts.get("Low", 0))

st.markdown("---")

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Risk Tier Distribution")
    tier_order = ["Low", "Medium", "High", "Very High"]
    tier_colors = {"Low": "#59a14f", "Medium": "#edc949", "High": "#f28e2b", "Very High": "#e15759"}

    tier_df = risk_data.groupby("risk_tier").agg(
        members=("member_id", "count"),
        avg_paid=("total_paid", "mean")
    ).reset_index()

    fig = px.bar(tier_df, x="risk_tier", y="members",
                 color="risk_tier",
                 color_discrete_map=tier_colors,
                 category_orders={"risk_tier": tier_order},
                 text="members")
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Average Spend by Risk Tier")
    fig = px.bar(tier_df, x="risk_tier", y="avg_paid",
                 color="risk_tier",
                 color_discrete_map=tier_colors,
                 category_orders={"risk_tier": tier_order},
                 text_auto="$.2s",
                 labels={"avg_paid": "Avg Total Paid ($)"})
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Risk Score Distribution
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Risk Score Distribution")

fig = px.histogram(risk_data, x="risk_score", nbins=30,
                   color="risk_tier",
                   color_discrete_map=tier_colors,
                   category_orders={"risk_tier": tier_order},
                   labels={"risk_score": "Composite Risk Score"})
fig.update_layout(height=350, barmode="stack")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Demographics Breakdown
# ---------------------------------------------------------------------------

st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Risk by Plan Type")
    plan_risk = risk_data.groupby(["plan_type", "risk_tier"]).size().reset_index(name="count")
    fig = px.bar(plan_risk, x="plan_type", y="count", color="risk_tier",
                 color_discrete_map=tier_colors,
                 category_orders={"risk_tier": tier_order})
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Risk by Gender")
    gender_risk = risk_data.groupby(["gender", "risk_tier"]).size().reset_index(name="count")
    fig = px.bar(gender_risk, x="gender", y="count", color="risk_tier",
                 color_discrete_map=tier_colors,
                 category_orders={"risk_tier": tier_order})
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# High Risk Members Table
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("High & Very High Risk Members")

high_risk = risk_data[risk_data["risk_tier"].isin(["High", "Very High"])].sort_values(
    "risk_score", ascending=False
).head(20)

st.dataframe(
    high_risk[["member_id", "risk_tier", "risk_score", "total_claims",
               "total_paid", "distinct_diagnoses", "plan_type", "state"]],
    use_container_width=True,
    hide_index=True,
)
