import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import numpy as np
st.write("Plotly version:", plotly.__version__)

# ---------------------------------------------------------
# Streamlit basic config
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clinic Analytics Dashboard",
    layout="wide"
)

# ---------------------------------------------------------
# Styling – professional blue theme, top filters
# ---------------------------------------------------------
st.markdown("""
<style>
:root {
    --primary-color: #2563eb;    /* blue */
    --text-color: #0f172a;
}

html, body, [class*="css"]  {
    font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Main background */
body {
    background-color: #0b1120;
    color: #e5e7eb;
}

/* Header card */
.main-header {
    background: linear-gradient(90deg, #020617, #0b1120);
    border-radius: 16px;
    padding: 18px 22px;
    margin-bottom: 12px;
    border: 1px solid #1f2937;
}

/* Filter bar */
.filter-bar {
    background: #020617;
    border-radius: 14px;
    padding: 10px 18px 4px 18px;
    margin-bottom: 10px;
    border: 1px solid #1f2937;
}

/* Cards */
.card {
    background: #020617;
    border-radius: 16px;
    padding: 18px 20px;
    border: 1px solid #1f2937;
    margin-bottom: 16px;
}

/* KPI metric styling */
.metric-label {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #9ca3af;
}
.metric-value {
    font-size: 26px;
    font-weight: 700;
    color: #e5e7eb;
}

/* Make select boxes slimmer and blue-focused */
.stSelectbox > div > div {
    border-radius: 999px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper – Indian season mapping
# ---------------------------------------------------------
def india_season(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Summer / Pre-Monsoon"
    elif month in (6, 7, 8, 9):
        return "Monsoon"
    elif month in (10, 11):
        return "Post-Monsoon"
    return "Unknown"

# Approx city coordinates for India map (marker locations)
CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.7041, 77.1025),
    "Jaipur": (26.9124, 75.7873),
    "Bangalore": (12.9716, 77.5946),
    "Ahmedabad": (23.0225, 72.5714),
    "Kolkata": (22.5726, 88.3639),
    "Kochi": (9.9312, 76.2673),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Lucknow": (26.8467, 80.9462),
    "Pune": (18.5204, 73.8567),
    "Chandigarh": (30.7333, 76.7794),
    "Indore": (22.7196, 75.8577),
    "Nagpur": (21.1458, 79.0882),
    "Patna": (25.5941, 85.1376),
    "Ludhiana": (30.9010, 75.8573),
    "Kanpur": (26.4499, 80.3319),
    "Surat": (21.1702, 72.8311),
}

# ---------------------------------------------------------
# Data loading
# ---------------------------------------------------------
@st.cache_data
def load_workbook():
    """
    Try to load Clinic_db_with_metadata.xlsx first,
    fallback to Clinic_db.xlsx if needed.
    """
    try:
        xls = pd.read_excel("Clinic_db_with_metadata.xlsx", sheet_name=None)
    except FileNotFoundError:
        xls = pd.read_excel("Clinic_db.xlsx", sheet_name=None)
    return xls

sheets = load_workbook()

appointments_df = sheets.get("appointments")
patients_df     = sheets.get("patient")
departments_df  = sheets.get("department")
doctors_df      = sheets.get("doctor")
rooms_df        = sheets.get("room")
billing_df      = sheets.get("billing")
reason_meta_df  = sheets.get("reason_categories")
doctor_meta_df  = sheets.get("doctor_meta")
room_meta_df    = sheets.get("room_meta")

if appointments_df is None or patients_df is None:
    st.error("Appointments or Patient sheet is missing in the workbook. Please check the Excel file.")
    st.stop()

# ---------------------------------------------------------
# Build enriched appointments dataframe
# ---------------------------------------------------------
df = appointments_df.copy()

# Merge patient info
df = df.merge(
    patients_df[["patientid", "patientname", "gender", "city", "dob"]],
    on="patientid",
    how="left"
)

# Merge doctor info
if doctors_df is not None:
    df = df.merge(
        doctors_df[["doctorid", "doctorname", "departmentid"]],
        on="doctorid",
        how="left",
        suffixes=("", "_doc")
    )

# Merge department info (via doctor's departmentid)
if departments_df is not None and "departmentid" in departments_df.columns and "departmentid_doc" in df.columns:
    df = df.merge(
        departments_df[["departmentid", "departmentname"]],
        left_on="departmentid_doc",
        right_on="departmentid",
        how="left"
    )

# Base date/time fields
df["appointmentdate"] = pd.to_datetime(df["appointmentdate"], errors="coerce")
df["appointmenttime"] = pd.to_datetime(df["appointmenttime"], format="%H:%M:%S", errors="coerce")

df["date"]       = df["appointmentdate"].dt.date
df["year"]       = df["appointmentdate"].dt.year
df["month"]      = df["appointmentdate"].dt.month
df["month_name"] = df["appointmentdate"].dt.month_name()
df["day_name"]   = df["appointmentdate"].dt.day_name()
df["hour"]       = df["appointmenttime"].dt.hour

# Age (approx)
df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
today = pd.to_datetime(date.today())
df["age"] = ((today - df["dob"]).dt.days / 365.25).round(0)

# Season based on Indian weather pattern
df["season"] = df["month"].apply(lambda m: india_season(int(m)) if pd.notna(m) else "Unknown")

# Clean city & department text
df["city"] = df["city"].astype(str).str.strip().replace("nan", np.nan)
if "departmentname" in df.columns:
    df["departmentname"] = df["departmentname"].astype(str).str.strip().replace("nan", np.nan)

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("""
<div class="main-header">
  <h2 style="margin-bottom:4px; color:#e5e7eb;">Clinic Analytics Dashboard</h2>
  <div style="color:#9ca3af; font-size:13px;">
    Interactive health management view with filters, seasonal analysis, geography, and ML-based forecasts.
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Global filter bar (single row on top)
# ---------------------------------------------------------
min_date = df["date"].min()
max_date = df["date"].max()
if pd.isna(min_date) or pd.isna(max_date):
    min_date = date.today() - timedelta(days=30)
    max_date = date.today()

years_list  = sorted([int(y) for y in df["year"].dropna().unique().tolist()])
cities_list = sorted([c for c in df["city"].dropna().unique().tolist()])
dept_list   = sorted([d for d in df.get("departmentname", pd.Series([])).dropna().unique().tolist()])
gender_list = sorted([g for g in df.get("gender", pd.Series([])).dropna().unique().tolist()])
season_list = sorted([s for s in df.get("season", pd.Series([])).dropna().unique().tolist()])

st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
f1, f2, f3, f4, f5, f6 = st.columns([2, 1.2, 1.6, 1.6, 1.2, 1.6])

with f1:
    date_range = st.date_input(
        "📅 Date range",
        value=(min_date, max_date)
    )
with f2:
    selected_year = st.selectbox(
        "Year",
        options=["All"] + years_list,
        index=0
    )
with f3:
    selected_city = st.multiselect(
        "City",
        options=cities_list,
        default=[]
    )
with f4:
    selected_dept = st.multiselect(
        "Department",
        options=dept_list,
        default=[]
    )
with f5:
    selected_gender = st.multiselect(
        "Gender",
        options=gender_list,
        default=[]
    )
with f6:
    selected_season = st.multiselect(
        "Season",
        options=season_list,
        default=[]
    )

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Apply filters to df -> df_filtered
# ---------------------------------------------------------
df_filtered = df.copy()

# Date range
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = min_date, max_date

df_filtered = df_filtered[
    (df_filtered["date"] >= start_d) &
    (df_filtered["date"] <= end_d)
]

# Year filter
if selected_year != "All":
    df_filtered = df_filtered[df_filtered["year"] == selected_year]

# City filter (keep city, no state filter)
if selected_city:
    df_filtered = df_filtered[df_filtered["city"].isin(selected_city)]

# Department filter
if selected_dept and "departmentname" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["departmentname"].isin(selected_dept)]

# Gender filter
if selected_gender and "gender" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["gender"].isin(selected_gender)]

# Season filter
if selected_season and "season" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["season"].isin(selected_season)]

# ---------------------------------------------------------
# KPI Row
# ---------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)

total_patients = patients_df["patientid"].nunique() if patients_df is not None else 0
total_appointments = df_filtered["appointmentid"].nunique()

unique_cities = df_filtered["city"].nunique()
top_dept = "—"
if "departmentname" in df_filtered.columns and not df_filtered.empty:
    dept_counts = df_filtered["departmentname"].value_counts()
    if not dept_counts.empty:
        top_dept = dept_counts.index[0]

# Bed capacity
total_beds = 0
if rooms_df is not None and "noofbeds" in rooms_df.columns:
    total_beds = int(rooms_df["noofbeds"].fillna(0).sum())
today_count = df[df["date"] == date.today()].shape[0] if "date" in df.columns else 0
estimated_occ = (today_count / total_beds) if total_beds > 0 else 0
available_beds = max(total_beds - today_count, 0) if total_beds > 0 else 0

with k1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Total Patients</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(total_patients):,}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Appointments (Filtered)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(total_appointments):,}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Cities Covered</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(unique_cities):,}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Busiest Department</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{top_dept}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Bed Capacity / Today</div>', unsafe_allow_html=True)
    if total_beds > 0:
        st.markdown(
            f'<div class="metric-value">{today_count}/{total_beds} used</div>'
            f'<div style="color:#9ca3af;font-size:12px;">Estimated occupancy: {estimated_occ:.1%} | Free: {available_beds}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="metric-value">N/A</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Tabs layout
# ---------------------------------------------------------
tab_overview, tab_time, tab_geo, tab_dept_doc, tab_ml, tab_data = st.tabs(
    ["Overview", "Time & Season", "Geographical", "Dept & Doctors", "ML Prediction", "Raw Data"]
)

# ---------------------------------------------------------
# Overview tab
# ---------------------------------------------------------
with tab_overview:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Patients & Appointments Overview")

    if df_filtered.empty:
        st.info("No data for the selected filters.")
    else:
        c1, c2 = st.columns([2, 1.7])

        # Appointment volume trend (multi visualization)
        with c1:
            st.markdown("**Appointment volume trend**")
            chart_type = st.radio(
                "Chart type",
                ["Line", "Bar", "Area"],
                horizontal=True,
                key="trend_chart_type"
            )
            daily = (
                df_filtered.groupby("date")["appointmentid"]
                .count()
                .reset_index(name="appointments")
                .sort_values("date")
            )
            if not daily.empty:
                if chart_type == "Line":
                    fig = px.line(
                        daily,
                        x="date",
                        y="appointments",
                        markers=True,
                        title="Appointments per day"
                    )
                elif chart_type == "Bar":
                    fig = px.bar(
                        daily,
                        x="date",
                        y="appointments",
                        title="Appointments per day"
                    )
                else:  # Area
                    fig = px.area(
                        daily,
                        x="date",
                        y="appointments",
                        title="Appointments per day"
                    )
                fig.update_layout(
                    margin=dict(l=10, r=10, t=40, b=10),
                    template="plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No appointments in current filter for trend plot.")

        # Appointment reasons & categories
        with c2:
            st.markdown("**Top appointment reasons**")
            if "app_reason" in df_filtered.columns:
                reasons_count = (
                    df_filtered["app_reason"]
                    .fillna("Unknown")
                    .value_counts()
                    .reset_index()
                )
                reasons_count.columns = ["reason", "count"]
                fig_r = px.bar(
                    reasons_count.head(10),
                    x="reason",
                    y="count",
                    title="Top 10 reasons",
                )
                fig_r.update_layout(
                    margin=dict(l=10, r=10, t=40, b=80),
                    xaxis_tickangle=-45,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.info("No appointment reason column found.")

    # Busiest hour distribution
    st.markdown("---")
    st.markdown("### Busiest hours (clinic load by time of day)")
    if "hour" in df_filtered.columns and df_filtered["hour"].notna().any():
        hour_counts = (
            df_filtered.groupby("hour")["appointmentid"]
            .count()
            .reset_index(name="appointments")
            .sort_values("hour")
        )
        fig_h = px.bar(
            hour_counts,
            x="hour",
            y="appointments",
            title="Appointments by hour",
        )
        fig_h.update_layout(
            xaxis_title="Hour of day",
            yaxis_title="Appointments",
            template="plotly_dark"
        )
        st.plotly_chart(fig_h, use_container_width=True)

        # Heatmap Day x Hour
        pivot = (
            df_filtered.pivot_table(
                index="day_name",
                columns="hour",
                values="appointmentid",
                aggfunc="count",
                fill_value=0
            )
            .reindex(
                ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            )
        )
        fig_heat = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                coloraxis="coloraxis"
            )
        )
        fig_heat.update_layout(
            title="Heatmap – Day vs Hour",
            xaxis_title="Hour",
            yaxis_title="Day of week",
            coloraxis_colorscale="Blues",
            template="plotly_dark",
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No appointment time information available to compute hourly distribution.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Time & Season tab
# ---------------------------------------------------------
with tab_time:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Time & Seasonal Analysis (India)")

    if df_filtered.empty:
        st.info("No data for the selected filters.")
    else:
        # Season-wise appointments
        st.markdown("#### Appointments by season")
        season_counts = (
            df_filtered.groupby("season")["appointmentid"]
            .count()
            .reset_index(name="appointments")
        ).sort_values("appointments", ascending=False)

        if not season_counts.empty:
            col_t1, col_t2 = st.columns([1.5, 1])
            with col_t1:
                fig_s_bar = px.bar(
                    season_counts,
                    x="season",
                    y="appointments",
                    title="Season-wise appointments",
                )
                fig_s_bar.update_layout(
                    template="plotly_dark",
                    xaxis_title="Season",
                    yaxis_title="Appointments"
                )
                st.plotly_chart(fig_s_bar, use_container_width=True)
            with col_t2:
                fig_s_pie = px.pie(
                    season_counts,
                    names="season",
                    values="appointments",
                    title="Season share",
                )
                fig_s_pie.update_layout(template="plotly_dark")
                st.plotly_chart(fig_s_pie, use_container_width=True)
        else:
            st.info("No season data in current filter.")

        st.markdown("---")

        # Month trend within season
        st.markdown("#### Monthly trend within seasons")
        monthly = (
            df_filtered.groupby(["year", "month", "month_name", "season"])["appointmentid"]
            .count()
            .reset_index(name="appointments")
            .sort_values(["year", "month"])
        )
        if not monthly.empty:
            fig_m = px.line(
                monthly,
                x="month_name",
                y="appointments",
                color="season",
                markers=True,
                line_group="year",
                title="Monthly appointment trend by season"
            )
            fig_m.update_layout(
                template="plotly_dark",
                xaxis_title="Month",
                yaxis_title="Appointments"
            )
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("No monthly trend data.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Geographical tab (India map by city)
# ---------------------------------------------------------
with tab_geo:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Geographical Analysis – India (City-level)")

    if df_filtered.empty:
        st.info("No data for the selected filters.")
    else:
        geo = (
            df_filtered.groupby("city")["appointmentid"]
            .count()
            .reset_index(name="appointments")
        )
        # Add coordinates
        geo["lat"] = geo["city"].map(lambda c: CITY_COORDS.get(str(c), (np.nan, np.nan))[0])
        geo["lon"] = geo["city"].map(lambda c: CITY_COORDS.get(str(c), (np.nan, np.nan))[1])
        geo = geo.dropna(subset=["lat", "lon"])

        if geo.empty:
            st.info("No mapped city coordinates available for current data.")
        else:
            fig_geo = px.scatter_geo(
                geo,
                lat="lat",
                lon="lon",
                size="appointments",
                color="appointments",
                hover_name="city",
                projection="mercator",
                title="Patients / Appointments by City"
            )
            fig_geo.update_geos(
                scope="asia",
                showland=True,
                landcolor="white",
                showcountries=True,
                showcoastlines=True,
                center=dict(lat=22.0, lon=80.0),
                lataxis_range=[5, 35],
                lonaxis_range=[65, 100],
)

            fig_geo.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                template="plotly_dark",
                coloraxis_colorscale="Blues"
            )
            st.plotly_chart(fig_geo, use_container_width=True)

            st.markdown("Top cities by appointments")
            st.dataframe(
                geo.sort_values("appointments", ascending=False).reset_index(drop=True),
                use_container_width=True,
                height=260
            )

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Department & Doctor tab
# ---------------------------------------------------------
with tab_dept_doc:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Department & Doctor Performance")

    if df_filtered.empty:
        st.info("No data for the selected filters.")
    else:
        col_d1, col_d2 = st.columns([1.2, 1])

        # Department-wise volume
        with col_d1:
            if "departmentname" in df_filtered.columns:
                dept_stats = (
                    df_filtered.groupby("departmentname")["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                    .sort_values("appointments", ascending=False)
                )
                fig_dept = px.bar(
                    dept_stats,
                    x="departmentname",
                    y="appointments",
                    title="Appointments by department",
                )
                fig_dept.update_layout(
                    template="plotly_dark",
                    xaxis_tickangle=-30,
                    xaxis_title="Department",
                    yaxis_title="Appointments"
                )
                st.plotly_chart(fig_dept, use_container_width=True)
            else:
                st.info("Department name column not available.")

        # Doctor performance (appointments + rating)
        with col_d2:
            if doctors_df is not None:
                doc_perf = (
                    df_filtered.groupby("doctorid")["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                )
                doc_perf = doc_perf.merge(
                    doctors_df[["doctorid", "doctorname", "departmentid"]],
                    on="doctorid",
                    how="left"
                )
                if doctor_meta_df is not None:
                    doc_perf = doc_perf.merge(
                        doctor_meta_df,
                        on="doctorid",
                        how="left"
                    )
                if departments_df is not None:
                    doc_perf = doc_perf.merge(
                        departments_df[["departmentid", "departmentname"]],
                        on="departmentid",
                        how="left",
                        suffixes=("", "_dept")
                    )
                if not doc_perf.empty:
                    fig_doc = px.scatter(
                        doc_perf,
                        x="appointments",
                        y="rating" if "rating" in doc_perf.columns else "appointments",
                        size="appointments",
                        color="departmentname",
                        hover_name="doctorname",
                        title="Doctor performance (appointments vs rating)",
                    )
                    fig_doc.update_layout(
                        template="plotly_dark",
                        xaxis_title="Appointments",
                        yaxis_title="Rating (if available)"
                    )
                    st.plotly_chart(fig_doc, use_container_width=True)
                else:
                    st.info("No doctor performance data after filtering.")
            else:
                st.info("Doctor sheet not available in workbook.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# ML Prediction tab – Forecasts & predictive visuals
# ---------------------------------------------------------
with tab_ml:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("ML Prediction – Future Volume & Patterns")

    if df_filtered.empty:
        st.info("No data for the selected filters.")
    else:
        # 1) FUTURE APPOINTMENT VOLUME FORECAST (simple regression)
        st.markdown("### 1️⃣ Future appointment volume forecast")

        daily = (
            df_filtered.groupby("date")["appointmentid"]
            .count()
            .reset_index(name="appointments")
            .sort_values("date")
        )

        if daily.shape[0] < 5:
            st.info("Not enough historical days for a meaningful forecast (need at least 5). Showing history only.")
            fig_hist = px.line(
                daily,
                x="date",
                y="appointments",
                markers=True,
                title="Historical daily appointments"
            )
            fig_hist.update_layout(template="plotly_dark")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            # Simple linear trend model without external libraries
            daily["day_index"] = range(len(daily))
            x = daily["day_index"].values
            y = daily["appointments"].values
            coeffs = np.polyfit(x, y, deg=1)
            a, b = coeffs  # y = a*x + b

            horizon = st.slider(
                "Forecast horizon (days)",
                min_value=7,
                max_value=30,
                value=14
            )

            last_idx = daily["day_index"].max()
            future_idx = np.arange(last_idx + 1, last_idx + 1 + horizon)
            future_dates = [daily["date"].min() + timedelta(days=int(i)) for i in future_idx]
            future_pred = a * future_idx + b
            future_pred = np.maximum(future_pred, 0)  # no negative counts

            hist_plot = daily[["date", "appointments"]].copy()
            hist_plot["type"] = "Actual"

            future_plot = pd.DataFrame({
                "date": future_dates,
                "appointments": future_pred,
                "type": "Forecast"
            })

            combined = pd.concat([hist_plot, future_plot], ignore_index=True)

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fig_fore_line = px.line(
                    combined,
                    x="date",
                    y="appointments",
                    color="type",
                    markers=True,
                    title="Daily appointments – history & forecast"
                )
                fig_fore_line.update_layout(
                    template="plotly_dark",
                    xaxis_title="Date",
                    yaxis_title="Appointments"
                )
                st.plotly_chart(fig_fore_line, use_container_width=True)

            with col_f2:
                fig_fore_bar = px.bar(
                    future_plot,
                    x="date",
                    y="appointments",
                    title="Forecasted daily appointments (future only)"
                )
                fig_fore_bar.update_layout(
                    template="plotly_dark",
                    xaxis_title="Date",
                    yaxis_title="Forecasted appointments"
                )
                st.plotly_chart(fig_fore_bar, use_container_width=True)

            # Simple statistic: next 7 days
            next_7_total = future_plot.head(7)["appointments"].sum()
            st.markdown(
                f"**Projected appointments for next 7 days:** `{next_7_total:.0f}` (based on linear trend)"
            )

        st.markdown("---")

        # 2) HEATMAP & CHARTS FOR PREDICTIVE FACTORS
        st.markdown("### 2️⃣ Predictive patterns – season, weekday, department")

        if not df_filtered.empty:
            # Season x Department heatmap
            if "season" in df_filtered.columns and "departmentname" in df_filtered.columns:
                cross = (
                    df_filtered
                    .groupby(["season", "departmentname"])["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                )
                if not cross.empty:
                    pivot_sd = cross.pivot(
                        index="season", columns="departmentname", values="appointments"
                    ).fillna(0)
                    fig_sd = go.Figure(
                        data=go.Heatmap(
                            z=pivot_sd.values,
                            x=pivot_sd.columns,
                            y=pivot_sd.index,
                            coloraxis="coloraxis"
                        )
                    )
                    fig_sd.update_layout(
                        title="Heatmap – Season vs Department (appointments)",
                        xaxis_title="Department",
                        yaxis_title="Season",
                        coloraxis_colorscale="Blues",
                        template="plotly_dark",
                        margin=dict(l=10, r=10, t=40, b=80)
                    )
                    st.plotly_chart(fig_sd, use_container_width=True)

            col_pf1, col_pf2 = st.columns(2)

            # Bar: season-wise volume
            with col_pf1:
                season_counts = (
                    df_filtered.groupby("season")["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                )
                if not season_counts.empty:
                    fig_season_bar = px.bar(
                        season_counts,
                        x="season",
                        y="appointments",
                        title="Season-wise appointment volume",
                    )
                    fig_season_bar.update_layout(
                        template="plotly_dark",
                        xaxis_title="Season",
                        yaxis_title="Appointments"
                    )
                    st.plotly_chart(fig_season_bar, use_container_width=True)

            # Pie: weekday share
            with col_pf2:
                weekday_counts = (
                    df_filtered.groupby("day_name")["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                )
                if not weekday_counts.empty:
                    # reorder weekdays
                    weekday_order = [
                        "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
                    ]
                    weekday_counts["day_name"] = pd.Categorical(
                        weekday_counts["day_name"], categories=weekday_order, ordered=True
                    )
                    weekday_counts = weekday_counts.sort_values("day_name")
                    fig_weekday_pie = px.pie(
                        weekday_counts,
                        names="day_name",
                        values="appointments",
                        title="Weekday share of appointments",
                    )
                    fig_weekday_pie.update_layout(template="plotly_dark")
                    st.plotly_chart(fig_weekday_pie, use_container_width=True)

        st.markdown("---")

        # 3) Bed demand projection (very simple ML-style estimate)
        st.markdown("### 3️⃣ Bed demand projection (simple estimate)")

        if rooms_df is not None and "noofbeds" in rooms_df.columns:
            total_beds = int(rooms_df["noofbeds"].fillna(0).sum())
            # Use recent 7 days from df_filtered (or full df if less)
            if not df_filtered.empty:
                recent_days = (
                    df_filtered
                    .groupby("date")["appointmentid"]
                    .count()
                    .reset_index(name="appointments")
                    .sort_values("date", ascending=False)
                    .head(7)
                )
                avg_recent = recent_days["appointments"].mean()

                # simple rule: assume one bed per appointment as an upper bound
                projected_bed_demand = min(total_beds, avg_recent)
                fig_bed = go.Figure()
                fig_bed.add_trace(
                    go.Bar(
                        x=["Total Beds"],
                        y=[total_beds],
                        name="Total Beds"
                    )
                )
                fig_bed.add_trace(
                    go.Bar(
                        x=["Projected Demand"],
                        y=[projected_bed_demand],
                        name="Projected Bed Demand (next 7 days avg)"
                    )
                )
                fig_bed.update_layout(
                    barmode="group",
                    title="Projected bed demand vs total capacity",
                    template="plotly_dark",
                    yaxis_title="Beds"
                )
                st.plotly_chart(fig_bed, use_container_width=True)

                st.markdown(
                    f"- **Total beds:** `{total_beds}`  \n"
                    f"- **Avg appointments (last 7 days in filter):** `{avg_recent:.1f}`  \n"
                    f"- **Projected peak demand:** `{projected_bed_demand:.1f}` beds"
                )
            else:
                st.info("No filtered appointments to compute bed demand.")
        else:
            st.info("Room / bed metadata not found in workbook.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Raw data tab
# ---------------------------------------------------------
with tab_data:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Filtered appointment dataset")

    st.dataframe(
        df_filtered.reset_index(drop=True),
        use_container_width=True,
        height=500
    )
    st.markdown(
        f"Rows: **{df_filtered.shape[0]}**, Columns: **{df_filtered.shape[1]}**"
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown(
    "<div style='text-align:center;color:#6b7280;font-size:12px;margin-top:10px;'>"
    "Dashboard: Filters on top • India seasonal logic • City-based map • ML predictions on appointment volume & bed demand."
    "</div>",
    unsafe_allow_html=True
)
