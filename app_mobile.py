import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="PREVAN SHIPPING - Real-Time Optimization Dashboard",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================
# Responsive styling
# =========================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 1400px;
        }
        .prevan-card {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }
        .prevan-title {
            font-size: 2rem;
            font-weight: 800;
            color: #173a67;
            margin-bottom: 0.1rem;
        }
        .prevan-subtitle {
            font-size: 1rem;
            color: #5b6b7c;
            margin-bottom: 0;
        }
        .small-help {
            color: #5b6b7c;
            font-size: 0.92rem;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.65rem;
                padding-right: 0.65rem;
            }
            .prevan-title {
                font-size: 1.45rem;
            }
            .prevan-subtitle {
                font-size: 0.92rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
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


def scenario_table(
    current_fleet,
    total_deliveries,
    avg_distance_per_delivery,
    fuel_per_mile,
    co2_per_liter,
    route_opt_miles_reduction,
    fleet_opt_reduction_pct,
    quantum_reduction_pct,
):
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
        },
    }

    return pd.DataFrame(scenarios).T.reset_index().rename(columns={"index": "scenario"})


def baseline_model(
    current_fleet,
    total_deliveries,
    avg_distance_per_delivery,
    fuel_per_mile,
    co2_per_liter,
    fleet_reduction_pct,
):
    current_total_miles = total_deliveries * avg_distance_per_delivery
    current_total_fuel = current_total_miles * fuel_per_mile
    current_total_co2 = current_total_fuel * co2_per_liter

    optimized_fleet = math.ceil(current_fleet * (1 - fleet_reduction_pct))
    optimized_total_miles = current_total_miles * (optimized_fleet / current_fleet)
    optimized_total_fuel = optimized_total_miles * fuel_per_mile
    optimized_total_co2 = optimized_total_fuel * co2_per_liter

    return {
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


def fuel_co2_model(scenarios_df):
    work = scenarios_df.copy()
    work["model2_score"] = (work["fuel"] / 1_000_000) + (work["co2"] / 1_000_000)
    best_row = work.sort_values("model2_score", ascending=True).iloc[0]

    return {
        "model": "Model 2 - Fuel and CO2 Optimized Scenario",
        "best_scenario": best_row["scenario"],
        "selected_fleet": int(best_row["fleet"]),
        "selected_miles": best_row["miles"],
        "selected_fuel": best_row["fuel"],
        "selected_co2": best_row["co2"],
        "score": best_row["model2_score"],
    }, work


def weighted_score_model(scenarios_df, w_fleet, w_miles, w_fuel, w_co2):
    work = scenarios_df.copy()
    base = work.loc[work["scenario"] == "Current"].iloc[0]

    work["norm_fleet"] = work["fleet"] / base["fleet"]
    work["norm_miles"] = work["miles"] / base["miles"]
    work["norm_fuel"] = work["fuel"] / base["fuel"]
    work["norm_co2"] = work["co2"] / base["co2"]

    work["weighted_score"] = (
        w_fleet * work["norm_fleet"]
        + w_miles * work["norm_miles"]
        + w_fuel * work["norm_fuel"]
        + w_co2 * work["norm_co2"]
    )

    best_row = work.sort_values("weighted_score", ascending=True).iloc[0]

    return {
        "model": "Model 3 - Multi-Objective Weighted Score",
        "best_scenario": best_row["scenario"],
        "selected_fleet": int(best_row["fleet"]),
        "selected_miles": best_row["miles"],
        "selected_fuel": best_row["fuel"],
        "selected_co2": best_row["co2"],
        "score": best_row["weighted_score"],
    }, work


def nice_num(x, digits=2):
    return f"{x:,.{digits}f}"


# =========================
# Header
# =========================
logo = load_logo()
head1, head2 = st.columns([1, 4], vertical_alignment="center")
with head1:
    if logo:
        st.image(logo, use_container_width=True)
with head2:
    st.markdown("<div class='prevan-title'>PREVAN SHIPPING</div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='prevan-subtitle'>Responsive Real-Time Optimization Dashboard</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class='prevan-card'>
        Use this dashboard on mobile, tablet, or desktop to test operational values in real time and compare:
        <b>Model 1</b> baseline fleet optimization, <b>Model 2</b> fuel + CO₂ scenario optimization,
        and <b>Model 3</b> multi-objective weighted scoring.
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# Input area
# =========================
st.subheader("Inputs")
input_tab1, input_tab2, input_tab3 = st.tabs([
    "Operations",
    "Scenario Assumptions",
    "Model 3 Weights",
])

with input_tab1:
    c1, c2 = st.columns(2)
    with c1:
        current_fleet = st.number_input("Current Fleet Size", min_value=1, value=1200, step=1)
        total_deliveries = st.number_input("Total Deliveries", min_value=1, value=450000, step=1000)
        avg_distance_per_delivery = st.number_input(
            "Average Distance per Delivery", min_value=0.1, value=4.2, step=0.1
        )
    with c2:
        fuel_per_mile = st.number_input("Fuel per Mile (liters)", min_value=0.01, value=1.4, step=0.01)
        co2_per_liter = st.number_input("CO₂ per Liter (kg)", min_value=0.1, value=2.3, step=0.1)
        st.markdown("<p class='small-help'>These are the main operational drivers used by all three models.</p>", unsafe_allow_html=True)

with input_tab2:
    c3, c4, c5 = st.columns(3)
    with c3:
        route_opt_miles_reduction = st.slider("Route Optimization Reduction %", 0.00, 0.50, 0.05, 0.01)
    with c4:
        fleet_reduction_pct = st.slider("Fleet Optimization Reduction %", 0.00, 0.50, 0.18, 0.01)
    with c5:
        quantum_reduction_pct = st.slider("Quantum Hybrid Reduction %", 0.00, 0.50, 0.20, 0.01)

with input_tab3:
    w_fleet = st.slider("Weight - Fleet", 0.0, 1.0, 0.25, 0.05)
    w_miles = st.slider("Weight - Miles", 0.0, 1.0, 0.25, 0.05)
    w_fuel = st.slider("Weight - Fuel", 0.0, 1.0, 0.25, 0.05)
    w_co2 = st.slider("Weight - CO₂", 0.0, 1.0, 0.25, 0.05)
    weight_total = w_fleet + w_miles + w_fuel + w_co2
    if abs(weight_total - 1.0) > 0.001:
        st.warning(f"Current weight total = {weight_total:.2f}. Keeping it close to 1.00 makes interpretation easier.")


# =========================
# Run models
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
    scenario_df,
    w_fleet=w_fleet,
    w_miles=w_miles,
    w_fuel=w_fuel,
    w_co2=w_co2,
)


# =========================
# KPI cards
# =========================
st.subheader("Key Results")
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Model 1 Best Fleet", f"{baseline_result['optimized_fleet']:,}", delta=f"-{baseline_result['fleet_saved']:,} vans")
with k2:
    st.metric("Model 2 Best Scenario", fuel_result["best_scenario"], delta=f"Fuel {fuel_result['selected_fuel']:,.0f} | CO₂ {fuel_result['selected_co2']:,.0f}")
with k3:
    st.metric("Model 3 Best Scenario", weighted_result["best_scenario"], delta=f"Score {weighted_result['score']:.4f}")


# =========================
# Scenario overview
# =========================
st.subheader("Scenario Overview")
display_df = scenario_df.copy()
for col in ["miles", "fuel", "co2"]:
    display_df[col] = display_df[col].round(2)
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.download_button(
    "Download Scenario Table (CSV)",
    data=scenario_df.to_csv(index=False).encode("utf-8"),
    file_name="prevan_shipping_scenarios.csv",
    mime="text/csv",
    use_container_width=True,
)


# =========================
# Charts
# =========================
st.subheader("Visual Comparison")
chart_tabs = st.tabs(["Fuel", "CO₂", "Miles", "Fleet"])

with chart_tabs[0]:
    fig1 = px.bar(scenario_df, x="scenario", y="fuel", title="Fuel by Scenario", text_auto=".2s")
    fig1.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=420)
    st.plotly_chart(fig1, use_container_width=True)

with chart_tabs[1]:
    fig2 = px.bar(scenario_df, x="scenario", y="co2", title="CO₂ by Scenario", text_auto=".2s")
    fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=420)
    st.plotly_chart(fig2, use_container_width=True)

with chart_tabs[2]:
    fig3 = px.bar(scenario_df, x="scenario", y="miles", title="Miles by Scenario", text_auto=".2s")
    fig3.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=420)
    st.plotly_chart(fig3, use_container_width=True)

with chart_tabs[3]:
    fig4 = px.bar(scenario_df, x="scenario", y="fleet", title="Fleet by Scenario", text_auto=True)
    fig4.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=420)
    st.plotly_chart(fig4, use_container_width=True)


# =========================
# Detailed model outputs
# =========================
st.subheader("Detailed Model Outputs")
model_tab1, model_tab2, model_tab3 = st.tabs([
    "Model 1 - Baseline",
    "Model 2 - Fuel + CO₂",
    "Model 3 - Weighted Score",
])

with model_tab1:
    baseline_df = pd.DataFrame([baseline_result]).T.reset_index()
    baseline_df.columns = ["Metric", "Value"]
    st.dataframe(baseline_df, use_container_width=True, hide_index=True)

with model_tab2:
    st.dataframe(pd.DataFrame([fuel_result]), use_container_width=True, hide_index=True)
    fuel_display = fuel_detail_df.copy()
    fuel_display["model2_score"] = fuel_display["model2_score"].round(4)
    st.dataframe(fuel_display, use_container_width=True, hide_index=True)

with model_tab3:
    st.dataframe(pd.DataFrame([weighted_result]), use_container_width=True, hide_index=True)
    weighted_display = weighted_detail_df.copy()
    for col in ["norm_fleet", "norm_miles", "norm_fuel", "norm_co2", "weighted_score"]:
        weighted_display[col] = weighted_display[col].round(4)
    st.dataframe(weighted_display, use_container_width=True, hide_index=True)


# =========================
# Recommendation summary
# =========================
st.subheader("Recommendation Summary")
r1, r2, r3 = st.columns(3)
with r1:
    st.success(
        f"Model 1 recommends {baseline_result['optimized_fleet']:,} vans with {baseline_result['fuel_saved']:,.0f} liters of fuel saved."
    )
with r2:
    st.info(
        f"Model 2 selects {fuel_result['best_scenario']} because it gives the lowest combined fuel + CO₂ score."
    )
with r3:
    st.warning(
        f"Model 3 selects {weighted_result['best_scenario']} based on your current weight settings."
    )

with st.expander("Mobile access note"):
    st.write(
        "To open this on any device, deploy the app to Streamlit Community Cloud, Render, or Railway. "
        "Once deployed, the same URL will work on mobile phones, tablets, iPads, laptops, and desktops."
    )

st.markdown("---")
st.caption("Built for PREVAN SHIPPING | Responsive Streamlit dashboard for phone, tablet, and desktop")
