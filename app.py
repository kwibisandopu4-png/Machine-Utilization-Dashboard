
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import IsolationForest

st.set_page_config(
    page_title="Machine Utilization & Reliability Dashboard",
    page_icon="⚙️",
    layout="wide"
)

st.title("Machine Utilization, OEE & Reliability Dashboard")
st.caption("Industrial Engineering / Production Performance Decision-Support System")

REQUIRED_COLUMNS = [
    "date", "shift", "machine", "shift_minutes", "break_minutes",
    "planned_minutes", "running_minutes", "downtime_minutes",
    "target_output", "actual_output", "rejected_output",
    "primary_downtime_reason"
]

DEFAULT_FILE = "sample_production_data_v2.csv"

@st.cache_data
def load_data(file_obj=None):
    if file_obj is not None:
        df = pd.read_csv(file_obj)
    else:
        df = pd.read_csv(DEFAULT_FILE)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = [
        "shift_minutes", "break_minutes", "planned_minutes",
        "running_minutes", "downtime_minutes", "target_output",
        "actual_output", "rejected_output"
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Core production KPIs
    df["availability_pct"] = (
        df["running_minutes"] / df["planned_minutes"] * 100
    ).clip(0, 100)

    # Ideal rate is estimated from target output and planned production time.
    # This makes performance internally consistent with the supplied production target.
    df["ideal_rate"] = df["target_output"] / df["planned_minutes"]

    df["performance_pct"] = (
        df["actual_output"] /
        (df["running_minutes"] * df["ideal_rate"])
        * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)

    df["quality_pct"] = (
        (df["actual_output"] - df["rejected_output"])
        / df["actual_output"] * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)

    df["oee_pct"] = (
        df["availability_pct"]
        * df["performance_pct"]
        * df["quality_pct"]
        / 10000
    ).clip(0, 100)

    df["utilization_pct"] = df["availability_pct"]
    df["downtime_pct"] = (
        df["downtime_minutes"] / df["planned_minutes"] * 100
    ).clip(0, 100)
    df["target_achievement_pct"] = (
        df["actual_output"] / df["target_output"] * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0)
    df["waste_pct"] = (
        df["rejected_output"] / df["actual_output"] * 100
    ).replace([np.inf, -np.inf], np.nan).fillna(0)

    return df

# Sidebar
st.sidebar.header("Dashboard Controls")

uploaded = st.sidebar.file_uploader(
    "Upload production CSV (optional)",
    type=["csv"]
)

try:
    df = load_data(uploaded)
except Exception as e:
    st.error(f"Could not load the production dataset: {e}")
    st.stop()

st.sidebar.info(
    "Shift model: 480 minutes total, 30-minute scheduled break, "
    "450 minutes planned production time."
)

machines = sorted(df["machine"].dropna().unique())
shifts = sorted(df["shift"].dropna().unique())

selected_machines = st.sidebar.multiselect(
    "Machine",
    machines,
    default=machines
)

selected_shifts = st.sidebar.multiselect(
    "Shift",
    shifts,
    default=shifts
)

min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    df["machine"].isin(selected_machines)
    & df["shift"].isin(selected_shifts)
    & (df["date"].dt.date >= start_date)
    & (df["date"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# Top KPIs
st.subheader("Overall Production KPIs")

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Availability", f"{filtered['availability_pct'].mean():.1f}%")
k2.metric("Performance", f"{filtered['performance_pct'].mean():.1f}%")
k3.metric("Quality", f"{filtered['quality_pct'].mean():.1f}%")
k4.metric("OEE", f"{filtered['oee_pct'].mean():.1f}%")
k5.metric("Downtime", f"{filtered['downtime_minutes'].sum():.0f} min")
k6.metric(
    "Target Achievement",
    f"{filtered['target_achievement_pct'].mean():.1f}%"
)

st.caption(
    "OEE is calculated as Availability × Performance × Quality. "
    "Performance uses each record's target production rate as the ideal-rate reference."
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Performance",
    "Downtime & Pareto",
    "Reliability",
    "AI Anomaly Flags",
    "Data"
])

with tab1:
    st.header("Performance & OEE")

    c1, c2 = st.columns(2)

    with c1:
        machine_oee = (
            filtered.groupby("machine", as_index=False)
            [["availability_pct", "performance_pct", "quality_pct", "oee_pct"]]
            .mean()
        )
        machine_oee_long = machine_oee.melt(
            id_vars="machine",
            var_name="KPI",
            value_name="Percentage"
        )
        machine_oee_long["KPI"] = machine_oee_long["KPI"].map({
            "availability_pct": "Availability",
            "performance_pct": "Performance",
            "quality_pct": "Quality",
            "oee_pct": "OEE"
        })

        fig = px.bar(
            machine_oee_long,
            x="machine",
            y="Percentage",
            color="KPI",
            barmode="group",
            range_y=[0, 105],
            title="OEE Components by Machine"
        )
        fig.update_layout(yaxis_title="Percentage (%)")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        daily_oee = (
            filtered.groupby("date", as_index=False)
            [["availability_pct", "performance_pct", "quality_pct", "oee_pct"]]
            .mean()
        )
        daily_long = daily_oee.melt(
            id_vars="date",
            var_name="KPI",
            value_name="Percentage"
        )
        daily_long["KPI"] = daily_long["KPI"].map({
            "availability_pct": "Availability",
            "performance_pct": "Performance",
            "quality_pct": "Quality",
            "oee_pct": "OEE"
        })

        fig = px.line(
            daily_long,
            x="date",
            y="Percentage",
            color="KPI",
            markers=True,
            range_y=[0, 105],
            title="Daily OEE Trend"
        )
        fig.update_layout(yaxis_title="Percentage (%)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Machine Comparison")

    comparison = (
        filtered.groupby("machine")
        .agg(
            Availability=("availability_pct", "mean"),
            Performance=("performance_pct", "mean"),
            Quality=("quality_pct", "mean"),
            OEE=("oee_pct", "mean"),
            Downtime_min=("downtime_minutes", "sum"),
            Target_Achievement=("target_achievement_pct", "mean")
        )
        .reset_index()
    )

    for col in [
        "Availability", "Performance", "Quality", "OEE",
        "Target_Achievement"
    ]:
        comparison[col] = comparison[col].round(1)

    st.dataframe(comparison, use_container_width=True)

    st.subheader("Production Trend")
    trend = (
        filtered.groupby("date", as_index=False)
        [["target_output", "actual_output", "rejected_output"]]
        .sum()
    )

    fig = px.line(
        trend,
        x="date",
        y=["target_output", "actual_output"],
        markers=True,
        title="Target vs Actual Production"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Downtime Analysis & Pareto")

    downtime_summary = (
        filtered.groupby("primary_downtime_reason", as_index=False)
        ["downtime_minutes"]
        .sum()
        .sort_values("downtime_minutes", ascending=False)
    )

    total_dt = downtime_summary["downtime_minutes"].sum()
    downtime_summary["percentage"] = (
        downtime_summary["downtime_minutes"] / total_dt * 100
        if total_dt > 0 else 0
    )
    downtime_summary["cumulative_pct"] = downtime_summary["percentage"].cumsum()

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            downtime_summary,
            x="primary_downtime_reason",
            y="downtime_minutes",
            title="Downtime by Cause"
        )
        fig.update_layout(
            xaxis_title="Downtime Cause",
            yaxis_title="Minutes"
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.bar(
            downtime_summary,
            x="primary_downtime_reason",
            y="percentage",
            title="Pareto Contribution"
        )
        fig.add_scatter(
            x=downtime_summary["primary_downtime_reason"],
            y=downtime_summary["cumulative_pct"],
            mode="lines+markers",
            name="Cumulative %"
        )
        fig.update_layout(
            yaxis_title="Percentage (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        downtime_summary.round(2),
        use_container_width=True
    )

    st.info(
        "The Pareto analysis helps the reliability and production teams "
        "prioritize the few downtime causes contributing most to total lost time."
    )

with tab3:
    st.header("Reliability & Maintenance Indicators")

    # Shift-level proxies, not formal event-level MTBF/MTTR
    records_with_dt = (filtered["downtime_minutes"] > 0).sum()
    total_running = filtered["running_minutes"].sum()
    total_downtime = filtered["downtime_minutes"].sum()

    mtbf_proxy = (
        total_running / records_with_dt
        if records_with_dt > 0 else 0
    )
    mttr_proxy = (
        total_downtime / records_with_dt
        if records_with_dt > 0 else 0
    )

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("MTBF Proxy", f"{mtbf_proxy:.1f} min")
    r2.metric("MTTR Proxy", f"{mttr_proxy:.1f} min")
    r3.metric("Downtime Events/Records", f"{records_with_dt}")
    r4.metric("Average Availability", f"{filtered['availability_pct'].mean():.1f}%")

    st.warning(
        "MTBF and MTTR shown here are shift-level proxies. Formal MTBF/MTTR "
        "requires event-level failure and repair timestamps."
    )

    reliability_by_machine = (
        filtered.groupby("machine")
        .agg(
            Availability=("availability_pct", "mean"),
            Downtime_Minutes=("downtime_minutes", "sum"),
            Downtime_Records=("downtime_minutes", lambda x: (x > 0).sum()),
            Average_Downtime=("downtime_minutes", "mean"),
            OEE=("oee_pct", "mean")
        )
        .reset_index()
    )

    st.subheader("Reliability Comparison")
    st.dataframe(
        reliability_by_machine.round(2),
        use_container_width=True
    )

    st.subheader("Availability Trend")
    availability_trend = (
        filtered.groupby(["date", "machine"], as_index=False)
        ["availability_pct"]
        .mean()
    )

    fig = px.line(
        availability_trend,
        x="date",
        y="availability_pct",
        color="machine",
        markers=True,
        range_y=[0, 105],
        title="Daily Availability by Machine"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Reliability Interpretation")

    for _, row in reliability_by_machine.iterrows():
        st.write(
            f"**{row['machine']}** — average availability "
            f"{row['Availability']:.1f}%, total downtime "
            f"{row['Downtime_Minutes']:.0f} minutes, and average shift "
            f"downtime {row['Average_Downtime']:.1f} minutes."
        )

with tab4:
    st.header("AI Anomaly Detection")

    ai_features = [
        "availability_pct",
        "downtime_minutes",
        "target_achievement_pct",
        "quality_pct"
    ]

    X = filtered[ai_features].fillna(0)

    if len(X) >= 10:
        contamination = min(0.08, max(0.03, 2 / len(X)))

        model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42
        )
        filtered["ai_prediction"] = model.fit_predict(X)
        filtered["ai_anomaly"] = np.where(
            filtered["ai_prediction"] == -1,
            "Anomaly",
            "Normal"
        )

        anomalies = filtered[filtered["ai_anomaly"] == "Anomaly"].copy()

        a1, a2 = st.columns(2)
        a1.metric("Records Analysed", len(filtered))
        a2.metric("AI Anomalies", len(anomalies))

        if anomalies.empty:
            st.success("No unusual records were detected in the selected data.")
        else:
            st.warning(
                "AI flags indicate records that differ from normal patterns. "
                "They are review signals, not automatic fault diagnoses."
            )

            display_cols = [
                "date", "shift", "machine",
                "availability_pct", "downtime_minutes",
                "target_achievement_pct", "quality_pct",
                "oee_pct", "primary_downtime_reason"
            ]

            st.dataframe(
                anomalies[display_cols].sort_values(
                    "downtime_minutes", ascending=False
                ).round(2),
                use_container_width=True
            )

            fig = px.scatter(
                filtered,
                x="downtime_minutes",
                y="availability_pct",
                color="ai_anomaly",
                hover_data=["machine", "shift", "date", "oee_pct"],
                title="AI Anomaly Map"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Investigation Guidance")

            for _, row in anomalies.head(10).iterrows():
                indicators = []

                if row["downtime_minutes"] > filtered["downtime_minutes"].median():
                    indicators.append("above-median downtime")
                if row["availability_pct"] < filtered["availability_pct"].median():
                    indicators.append("below-median availability")
                if row["target_achievement_pct"] < filtered["target_achievement_pct"].median():
                    indicators.append("below-median target achievement")
                if row["quality_pct"] < filtered["quality_pct"].median():
                    indicators.append("below-median quality")

                reason = ", ".join(indicators) if indicators else "unusual KPI combination"

                st.write(
                    f"**{row['date'].date()} — {row['shift']} — {row['machine']}**: "
                    f"review because of {reason}. Primary recorded downtime reason: "
                    f"{row['primary_downtime_reason']}."
                )

    else:
        st.info("At least 10 records are recommended for AI anomaly detection.")

with tab5:
    st.header("Production Data")

    st.dataframe(
        filtered.sort_values(["date", "shift", "machine"]),
        use_container_width=True
    )

    csv_data = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered data as CSV",
        data=csv_data,
        file_name="filtered_machine_production_data.csv",
        mime="text/csv"
    )

st.divider()
st.caption(
    "Academic prototype: synthetic production data are used for demonstration "
    "unless replaced with approved real production data. AI outputs support "
    "investigation and do not replace engineering judgement."
)
