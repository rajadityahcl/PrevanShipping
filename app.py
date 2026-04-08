
import math
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px


# =========================
# Page config
# =========================
st.set_page_config(
    page_title="PREVAN SHIPPING - Real-Time Optimization Dashboard",
    page_icon="🚚",
    layout="wide"
)


# =========================
# Helpers
# =========================
def load_logo():
    possible_paths = [
        Path(__file__).parent / "prevan_logo.png",
        Path("/mnt/data/1b7f2014-1008-465b-9f42-a71a425ddbfc.png"),
    ]
    for p in possible_paths:
        if p.exists():
            return str(p)
    return None


def scenario_table(current_fleet, total_deliveries, avg_distance_per_delivery, fuel_per_mile, co2_per_liter,
                   route_opt_miles_reduction, fleet_opt_reduction_pct, quantum_reduction_pct):
    """
    Builds the 4 scenarios used across the uploaded models:
    Current, Route_Opt, Fleet_Opt, Quantum_Hybrid
    """
    current_miles = total_deliveries * avg_distance_per_delivery
    current_fuel = current_miles * fuel_per_mile
    current_co2 = current_fuel * co2_per_liter

    scenarios = {
        "Current": {
            "fleet": int(round(current_fleet)),
            "miles": current_miles,
            "fuel": current_fuel,
            "co2": current_co2,
        },
        "Route_Opt": {
            "fleet": int(round(current_fleet)),
            "miles": current_miles * (1 - route_opt_miles_reduction),
            "fuel": current_fuel * (1 - route_opt_miles_reduction),
            "co2": current_co2 * (1 - route_opt_miles_reduction),
        },
        "Fleet_Opt": {
            "fleet": int(round(current_fleet * (1 - fleet_opt_reduction_pct))),
            "miles": current_miles * (1 - fleet_opt_reduction_pct),
            "fuel": current_fuel * (1 - fleet_opt_reduction_pct),
            "co2": current_co2 * (1 - fleet_opt_reduction_pct),
        },
        "Quantum_Hybrid": {
            "fleet": int(round(current_fleet * (1 - quantum_reduction_pct))),
            "miles": current_miles * (1 - quantum_reduction_pct),
            "fuel": current_fuel * (1 - quantum_reduction_pct),
            "co2": current_co2 * (1 - quantum_reduction_pct),
        }
    }

    df = pd.DataFrame(scenarios).T.reset_index().rename(columns={"index": "scenario"})
    return df


def baseline_model(current_fleet, total_deliveries, avg_distance_per_delivery, fuel_per_mile,
                   co2_per_liter, fleet_reduction_pct):
    """
    Mirrors uploaded baseline model:
    minimize fleet size subject to max reduction %
    Since objective is just vans and constraint is lower bound, the optimal answer is:
    optimized_fleet = ceil(current_fleet * (1 - fleet_reduction_pct))
    """
    current_total_miles = total_deliveries * avg_distance_per_delivery
    current_total_fuel = current_total_miles * fuel_per_mile
    current_total_co2 = current_total_fuel * co2_per_liter

    optimized_fleet = math.ceil(current_fleet * (1 - fleet_reduction_pct))
    optimized_total_miles = current_total_miles * (optimized_fleet / current_fleet)
    optimized_total_fuel = optimized_total_miles * fuel_per_mile
    optimized_total_co2 = optimized_total_fuel * co2_per_liter

    result = {
        "model": "Model 1 - Baseline Fleet Optimization",
        "best_scenario": "Fleet_Opt",
        "optimized_fleet": optimized_fleet,
        "fleet_saved": current_fleet - optimized_fleet,
        "optimized_total_miles": optimized_total_miles,
        "miles_saved": current_total_miles - optimized_total_miles,
        "optimized_total_fuel": optimized_total_fuel,
        "fuel_saved": current_total_fuel - optimized_total_fuel,
        "optimized_total_co2": optimized_total_co2,
        "co2_saved": current_total_co2 - optimized_total_co2,
    }
    return result


def fuel_co2_model(scenarios_df):
    """
    Mirrors uploaded fuel+CO2 weighted scenario model:
    choose the scenario with minimum fuel + co2
    """
    work = scenarios_df.copy()
    work["model2_score"] = (work["fuel"] / 1_000_000) + (work["co2"] / 1_000_000)
    best_row = work.sort_values("model2_score", ascending=True).iloc[0]

    result = {
        "model": "Model 2 - Fuel and CO2 Optimized Scenario",
        "best_scenario": best_row["scenario"],
        "selected_fleet": int(best_row["fleet"]),
        "selected_miles": best_row["miles"],
        "selected_fuel": best_row["fuel"],
        "selected_co2": best_row["co2"],
        "score": best_row["model2_score"],
    }
    return result, work


def weighted_score_model(scenarios_df, w_fleet, w_miles, w_fuel, w_co2):
    """
    Mirrors uploaded multi-objective weighted normalized score model.
    """
    work = scenarios_df.copy()

    base = work.loc[work["scenario"] == "Current"].iloc[0]
    work["norm_fleet"] = work["fleet"] / base["fleet"]
    work["norm_miles"] = work["miles"] / base["miles"]
    work["norm_fuel"] = work["fuel"] / base["fuel"]
    work["norm_co2"] = work["co2"] / base["co2"]

    work["weighted_score"] = (
        w_fleet * work["norm_fleet"] +
        w_miles * work["norm_miles"] +
        w_fuel * work["norm_fuel"] +
        w_co2 * work["norm_co2"]
    )

    best_row = work.sort_values("weighted_score", ascending=True).iloc[0]

    result = {
        "model": "Model 3 - Multi-Objective Weighted Score",
        "best_scenario": best_row["scenario"],
        "selected_fleet": int(best_row["fleet"]),
        "selected_miles": best_row["miles"],
        "selected_fuel": best_row["fuel"],
        "selected_co2": best_row["co2"],
        "score": best_row["weighted_score"],
    }
    return result, work


def format_number(x):
    if isinstance(x, (int, float)):
        return f"{x:,.2f}"
    return x


# =========================
# Header
# =========================
logo = load_logo()

left, right = st.columns([1, 5])
with left:
    if logo:
        st.image(logo, use_container_width=True)
with right:
    st.title("PREVAN SHIPPING")
    st.caption("Real-Time Optimization Dashboard")

st.markdown(
    """
    This dashboard lets users plug in operational values and instantly compare:
    - **Model 1:** Baseline Fleet Optimization
    - **Model 2:** Fuel and CO₂ Optimized Scenario
    - **Model 3:** Multi-Objective Weighted Score
    """
)

# =========================
# Sidebar inputs
# =========================
st.sidebar.header("Operational Inputs")

current_fleet = st.sidebar.number_input("Current Fleet Size", min_value=1, value=1200, step=1)
total_deliveries = st.sidebar.number_input("Total Deliveries", min_value=1, value=450000, step=1000)
avg_distance_per_delivery = st.sidebar.number_input("Average Distance per Delivery", min_value=0.1, value=4.2, step=0.1)
fuel_per_mile = st.sidebar.number_input("Fuel per Mile (liters)", min_value=0.01, value=1.4, step=0.01)
co2_per_liter = st.sidebar.number_input("CO₂ per Liter (kg)", min_value=0.1, value=2.3, step=0.1)

st.sidebar.header("Scenario Assumptions")
route_opt_miles_reduction = st.sidebar.slider("Route Optimization Reduction %", 0.00, 0.50, 0.05, 0.01)
fleet_reduction_pct = st.sidebar.slider("Fleet Optimization Reduction %", 0.00, 0.50, 0.18, 0.01)
quantum_reduction_pct = st.sidebar.slider("Quantum Hybrid Reduction %", 0.00, 0.50, 0.20, 0.01)

st.sidebar.header("Model 3 Weights")
w_fleet = st.sidebar.slider("Weight - Fleet", 0.0, 1.0, 0.25, 0.05)
w_miles = st.sidebar.slider("Weight - Miles", 0.0, 1.0, 0.25, 0.05)
w_fuel = st.sidebar.slider("Weight - Fuel", 0.0, 1.0, 0.25, 0.05)
w_co2 = st.sidebar.slider("Weight - CO₂", 0.0, 1.0, 0.25, 0.05)

weight_total = w_fleet + w_miles + w_fuel + w_co2
if abs(weight_total - 1.0) > 0.001:
    st.sidebar.warning(f"Weights currently sum to {weight_total:.2f}. For best interpretation, keep them close to 1.00.")


# =========================
# Build scenarios and run models
# =========================
scenario_df = scenario_table(
    current_fleet=current_fleet,
    total_deliveries=total_deliveries,
    avg_distance_per_delivery=avg_distance_per_delivery,
    fuel_per_mile=fuel_per_mile,
    co2_per_liter=co2_per_liter,
    route_opt_miles_reduction=route_opt_miles_reduction,
    fleet_opt_reduction_pct=fleet_reduction_pct,
    quantum_reduction_pct=quantum_reduction_pct,
)

baseline_result = baseline_model(
    current_fleet=current_fleet,
    total_deliveries=total_deliveries,
    avg_distance_per_delivery=avg_distance_per_delivery,
    fuel_per_mile=fuel_per_mile,
    co2_per_liter=co2_per_liter,
    fleet_reduction_pct=fleet_reduction_pct,
)

fuel_result, fuel_detail_df = fuel_co2_model(scenario_df)
weighted_result, weighted_detail_df = weighted_score_model(
    scenario_df, w_fleet=w_fleet, w_miles=w_miles, w_fuel=w_fuel, w_co2=w_co2
)

# =========================
# KPI cards
# =========================
st.subheader("Key Results")

k1, k2, k3 = st.columns(3)
with k1:
    st.metric(
        "Model 1 Best Fleet",
        f"{baseline_result['optimized_fleet']:,}",
        delta=f"-{baseline_result['fleet_saved']:,} vans"
    )
with k2:
    st.metric(
        "Model 2 Best Scenario",
        fuel_result["best_scenario"],
        delta=f"Fuel {fuel_result['selected_fuel']:,.0f} | CO₂ {fuel_result['selected_co2']:,.0f}"
    )
with k3:
    st.metric(
        "Model 3 Best Scenario",
        weighted_result["best_scenario"],
        delta=f"Score {weighted_result['score']:.4f}"
    )

# =========================
# Scenario overview
# =========================
st.subheader("Scenario Overview")
display_df = scenario_df.copy()
for col in ["miles", "fuel", "co2"]:
    display_df[col] = display_df[col].round(2)
st.dataframe(display_df, use_container_width=True)

download_csv = scenario_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Scenario Table (CSV)",
    data=download_csv,
    file_name="prevan_shipping_scenarios.csv",
    mime="text/csv"
)

# =========================
# Charts
# =========================
c1, c2 = st.columns(2)

with c1:
    fig1 = px.bar(
        scenario_df,
        x="scenario",
        y="fuel",
        title="Fuel by Scenario",
        text_auto=".2s"
    )
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    fig2 = px.bar(
        scenario_df,
        x="scenario",
        y="co2",
        title="CO₂ by Scenario",
        text_auto=".2s"
    )
    st.plotly_chart(fig2, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    fig3 = px.bar(
        scenario_df,
        x="scenario",
        y="miles",
        title="Miles by Scenario",
        text_auto=".2s"
    )
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    fig4 = px.bar(
        scenario_df,
        x="scenario",
        y="fleet",
        title="Fleet by Scenario",
        text_auto=True
    )
    st.plotly_chart(fig4, use_container_width=True)

# =========================
# Model tabs
# =========================
tab1, tab2, tab3 = st.tabs([
    "Model 1 - Baseline",
    "Model 2 - Fuel + CO₂",
    "Model 3 - Weighted Score"
])

with tab1:
    st.markdown("### Baseline Fleet Optimization Output")
    baseline_df = pd.DataFrame([baseline_result]).T.reset_index()
    baseline_df.columns = ["Metric", "Value"]
    st.dataframe(baseline_df, use_container_width=True)

with tab2:
    st.markdown("### Fuel and CO₂ Optimized Scenario Output")
    fuel_summary_df = pd.DataFrame([fuel_result])
    st.dataframe(fuel_summary_df, use_container_width=True)

    st.markdown("### Scenario Scoring Table")
    fuel_display = fuel_detail_df.copy()
    fuel_display["model2_score"] = fuel_display["model2_score"].round(4)
    st.dataframe(fuel_display, use_container_width=True)

with tab3:
    st.markdown("### Multi-Objective Weighted Score Output")
    weighted_summary_df = pd.DataFrame([weighted_result])
    st.dataframe(weighted_summary_df, use_container_width=True)

    st.markdown("### Normalized Weighted Scoring Table")
    weighted_display = weighted_detail_df.copy()
    numeric_cols = ["norm_fleet", "norm_miles", "norm_fuel", "norm_co2", "weighted_score"]
    for col in numeric_cols:
        weighted_display[col] = weighted_display[col].round(4)
    st.dataframe(weighted_display, use_container_width=True)

# =========================
# Recommendation box
# =========================
st.subheader("Dashboard Recommendation")
rec_col1, rec_col2, rec_col3 = st.columns(3)

with rec_col1:
    st.success(
        f"**Model 1 recommends:** {baseline_result['optimized_fleet']:,} vans "
        f"with {baseline_result['fuel_saved']:,.0f} liters fuel saved."
    )

with rec_col2:
    st.info(
        f"**Model 2 selects:** {fuel_result['best_scenario']} "
        f"because it gives the lowest combined fuel + CO₂ score."
    )

with rec_col3:
    st.warning(
        f"**Model 3 selects:** {weighted_result['best_scenario']} "
        f"based on your current weight settings."
    )

st.markdown("---")
st.caption("Built for PREVAN SHIPPING | Streamlit dashboard ready for local deployment from VS Code")
