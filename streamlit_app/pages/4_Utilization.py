"""Utilization Metrics — Admissions, LOS, facility analysis."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from db import query

st.set_page_config(page_title="Utilization", page_icon="🏥", layout="wide")
st.title("🏥 Utilization Metrics")

# ---------------------------------------------------------------------------
# ADT Event Summary
# ---------------------------------------------------------------------------

event_summary = query("""
    SELECT
        event_type,
        CASE event_type
            WHEN 'A01' THEN 'Admission'
            WHEN 'A02' THEN 'Transfer'
            WHEN 'A03' THEN 'Discharge'
            WHEN 'A04' THEN 'Registration'
            WHEN 'A08' THEN 'Update'
            ELSE 'Unknown'
        END as event_description,
        count(*) as event_count,
        count(distinct member_id) as unique_members
    FROM fact_adt_events
    GROUP BY event_type
    ORDER BY event_count DESC
""")

col1, col2, col3, col4 = st.columns(4)

admissions = event_summary[event_summary["event_type"] == "A01"]["event_count"].sum()
discharges = event_summary[event_summary["event_type"] == "A03"]["event_count"].sum()
transfers = event_summary[event_summary["event_type"] == "A02"]["event_count"].sum()
total_events = event_summary["event_count"].sum()

with col1:
    st.metric("Total ADT Events", f"{total_events:,.0f}")
with col2:
    st.metric("Admissions (A01)", f"{admissions:,.0f}")
with col3:
    st.metric("Discharges (A03)", f"{discharges:,.0f}")
with col4:
    st.metric("Transfers (A02)", f"{transfers:,.0f}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Event Distribution
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Event Type Distribution")
    fig = px.pie(event_summary, values="event_count", names="event_description",
                 color_discrete_sequence=px.colors.qualitative.Set2,
                 hole=0.4)
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Monthly Event Trends")
    monthly_events = query("""
        SELECT
            event_year_month,
            CASE event_type
                WHEN 'A01' THEN 'Admission'
                WHEN 'A02' THEN 'Transfer'
                WHEN 'A03' THEN 'Discharge'
                WHEN 'A04' THEN 'Registration'
                WHEN 'A08' THEN 'Update'
            END as event_type,
            count(*) as events
        FROM fact_adt_events
        GROUP BY event_year_month, event_type
        ORDER BY event_year_month
    """)

    fig = px.line(monthly_events, x="event_year_month", y="events",
                  color="event_type",
                  labels={"event_year_month": "Month", "events": "Event Count"})
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Facility Analysis
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Facility Utilization")

facility_data = query("""
    SELECT
        facility_name,
        department,
        count(*) as total_events,
        count(distinct member_id) as unique_patients,
        count(case when event_type = 'A01' then 1 end) as admissions,
        count(case when event_type = 'A03' then 1 end) as discharges,
        count(case when event_type = 'A02' then 1 end) as transfers
    FROM fact_adt_events
    GROUP BY facility_name, department
    ORDER BY total_events DESC
""")

col_left, col_right = st.columns(2)

with col_left:
    # Top facilities by volume
    facility_agg = facility_data.groupby("facility_name").agg(
        total_events=("total_events", "sum"),
        unique_patients=("unique_patients", "sum"),
        admissions=("admissions", "sum"),
    ).reset_index().sort_values("total_events", ascending=False).head(10)

    fig = px.bar(facility_agg, x="total_events", y="facility_name", orientation="h",
                 color="admissions", color_continuous_scale="Reds",
                 labels={"total_events": "Total Events", "facility_name": "Facility"})
    fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    # Department breakdown
    dept_agg = facility_data.groupby("department").agg(
        total_events=("total_events", "sum"),
        unique_patients=("unique_patients", "sum"),
    ).reset_index().sort_values("total_events", ascending=False).head(10)

    fig = px.bar(dept_agg, x="department", y="total_events",
                 color="unique_patients", color_continuous_scale="Blues",
                 text_auto=True,
                 labels={"total_events": "Events", "department": "Department"})
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Detail Table
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Facility-Department Detail")

st.dataframe(
    facility_data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "total_events": st.column_config.NumberColumn("Total Events", format="%d"),
        "unique_patients": st.column_config.NumberColumn("Unique Patients", format="%d"),
        "admissions": st.column_config.NumberColumn("Admissions", format="%d"),
        "discharges": st.column_config.NumberColumn("Discharges", format="%d"),
        "transfers": st.column_config.NumberColumn("Transfers", format="%d"),
    }
)
