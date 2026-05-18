"""Claims Analytics — Monthly trends, payer mix, financial KPIs."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from db import query

st.set_page_config(page_title="Claims Analytics", page_icon="📊", layout="wide")
st.title("📊 Claims Analytics")

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------

kpi_data = query("""
    SELECT
        count(distinct claim_id) as total_claims,
        count(distinct member_id) as unique_members,
        sum(line_charge_amount) as total_charged,
        sum(paid_amount) as total_paid,
        avg(paid_amount / nullif(line_charge_amount, 0)) as avg_payment_ratio,
        count(distinct case when claim_status = 'denied' then claim_id end) as denied_claims
    FROM fact_claims
""")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("Total Claims", f"{kpi_data['total_claims'].iloc[0]:,.0f}")
with col2:
    st.metric("Unique Members", f"{kpi_data['unique_members'].iloc[0]:,.0f}")
with col3:
    st.metric("Total Charged", f"${kpi_data['total_charged'].iloc[0]:,.0f}")
with col4:
    st.metric("Total Paid", f"${kpi_data['total_paid'].iloc[0]:,.0f}")
with col5:
    st.metric("Payment Ratio", f"{kpi_data['avg_payment_ratio'].iloc[0]:.1%}")
with col6:
    st.metric("Denied Claims", f"{kpi_data['denied_claims'].iloc[0]:,.0f}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Monthly Trends
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Monthly Claims Volume & Spend")
    monthly = query("""
        SELECT
            service_year_month,
            count(distinct claim_id) as claims,
            sum(line_charge_amount) as charged,
            sum(paid_amount) as paid
        FROM fact_claims
        GROUP BY service_year_month
        ORDER BY service_year_month
    """)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["service_year_month"], y=monthly["charged"],
                         name="Charged", marker_color="#4e79a7"))
    fig.add_trace(go.Bar(x=monthly["service_year_month"], y=monthly["paid"],
                         name="Paid", marker_color="#59a14f"))
    fig.add_trace(go.Scatter(x=monthly["service_year_month"], y=monthly["claims"],
                             name="Claims Count", yaxis="y2",
                             line=dict(color="#e15759", width=2)))
    fig.update_layout(
        yaxis=dict(title="Amount ($)"),
        yaxis2=dict(title="Claims Count", overlaying="y", side="right"),
        barmode="group", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Claims by Status")
    status = query("""
        SELECT
            claim_status,
            count(distinct claim_id) as claims,
            sum(line_charge_amount) as total_charged
        FROM fact_claims
        GROUP BY claim_status
        ORDER BY claims DESC
    """)

    fig = px.pie(status, values="claims", names="claim_status",
                 color_discrete_sequence=px.colors.qualitative.Set2,
                 hole=0.4)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Payer Analysis
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Payer Mix Analysis")

payer_data = query("""
    SELECT
        p.payer_name,
        p.payer_type,
        count(distinct f.claim_id) as claims,
        sum(f.line_charge_amount) as total_charged,
        sum(f.paid_amount) as total_paid,
        round(avg(f.paid_amount / nullif(f.line_charge_amount, 0)), 3) as payment_ratio
    FROM fact_claims f
    JOIN dim_payer p ON f.payer_id = p.payer_id
    GROUP BY p.payer_name, p.payer_type
    ORDER BY total_charged DESC
""")

col_left, col_right = st.columns(2)

with col_left:
    fig = px.bar(payer_data, x="payer_name", y=["total_charged", "total_paid"],
                 barmode="group", title="Charged vs Paid by Payer",
                 color_discrete_sequence=["#4e79a7", "#59a14f"])
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    fig = px.bar(payer_data, x="payer_name", y="payment_ratio",
                 title="Payment Ratio by Payer",
                 color="payment_ratio",
                 color_continuous_scale="RdYlGn")
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Top Diagnoses
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Top 10 Diagnoses by Claim Volume")

dx_data = query("""
    SELECT
        f.diagnosis_code,
        d.diagnosis_description,
        count(distinct f.claim_id) as claims,
        sum(f.paid_amount) as total_paid
    FROM fact_claims f
    JOIN dim_diagnosis d ON f.diagnosis_code = d.diagnosis_code
    GROUP BY f.diagnosis_code, d.diagnosis_description
    ORDER BY claims DESC
    LIMIT 10
""")

fig = px.bar(dx_data, x="claims", y="diagnosis_description", orientation="h",
             color="total_paid", color_continuous_scale="Blues",
             labels={"diagnosis_description": "Diagnosis", "claims": "Claim Count"})
fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)
