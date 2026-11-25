import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os

from src.analytics_engine import AnalyticsEngine
from src.simulation_engine import RetentionSimulator

# Page configuration
st.set_page_config(
    page_title="RevGuard | SaaS Retention & Revenue-at-Risk Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern executive aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value-danger {
        color: #DC2626 !important;
        font-weight: 700;
    }
    .metric-value-success {
        color: #16A34A !important;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 6px;
        font-weight: 600;
    }
    /* Completely hide Streamlit toolbar, header icons, and footer */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
    .stAppDeployButton {display: none !important;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_analytics():
    return AnalyticsEngine()

analytics = get_analytics()

# Header
st.markdown('<div class="main-header">🛡️ RevGuard: SaaS Retention & Revenue-at-Risk Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Executive Decision Intelligence: Advanced SQL analytics, cohort churn diagnostics, and financial ROI simulation</div>', unsafe_allow_html=True)

# Top Executive KPI Cards
kpis = analytics.get_executive_kpis()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(
        label="Annual Run-Rate (ARR)",
        value=f"${kpis['current_arr']:,.0f}",
        delta=f"MRR: ${kpis['current_mrr']:,.0f}"
    )
with col2:
    st.metric(
        label="Active Subscriptions",
        value=f"{kpis['active_accounts']:,}",
        delta=f"{kpis['overall_churn_rate']}% Historical Churn"
    )
with col3:
    st.metric(
        label="ARR at Risk (Vulnerable)",
        value=f"${kpis['arr_at_risk']:,.0f}",
        delta=f"-{kpis['risk_exposure_pct']}% of Total ARR",
        delta_color="inverse"
    )
with col4:
    st.metric(
        label="Critical Risk Accounts",
        value=f"{kpis['critical_risk_accounts']} accounts",
        delta="Immediate action required",
        delta_color="inverse"
    )
with col5:
    st.metric(
        label="Gross Margin Estimate",
        value="80.0%",
        delta="Standard B2B SaaS"
    )

st.divider()

# Navigation Tabs
tab_exec, tab_cohort, tab_radar, tab_sim, tab_sql = st.tabs([
    "📊 Executive Overview",
    "📈 Cohort Retention Heatmap",
    "🚨 Churn Early-Warning Radar",
    "🎯 What-If Campaign Simulator",
    "💻 Production SQL Lab"
])

# ==============================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ==============================================================================
with tab_exec:
    st.subheader("Revenue Trajectory & Tier Economics")
    
    mrr_df = analytics.get_mrr_growth_metrics()
    clv_df = analytics.get_clv_metrics()

    col_mrr1, col_mrr2 = st.columns([7, 5])
    
    with col_mrr1:
        st.markdown("**Monthly Recurring Revenue (MRR) Growth Trajectory**")
        chart_mrr = alt.Chart(mrr_df).mark_area(
            color='#3B82F6',
            opacity=0.4,
            line={'color': '#1D4ED8', 'size': 2.5}
        ).encode(
            x=alt.X('activity_month:T', title='Month'),
            y=alt.Y('total_mrr:Q', title='MRR ($)', axis=alt.Axis(format='$,.0f')),
            tooltip=[
                alt.Tooltip('activity_month:T', title='Month'),
                alt.Tooltip('total_mrr:Q', title='MRR', format='$,.0f'),
                alt.Tooltip('active_customers:Q', title='Active Customers'),
                alt.Tooltip('mrr_growth_pct:Q', title='MoM Growth', format='.2f')
            ]
        ).properties(height=320)
        st.altair_chart(chart_mrr, use_container_width=True)

    with col_mrr2:
        st.markdown("**Customer Economics by Subscription Tier**")
        st.dataframe(
            clv_df.style.format({
                'churn_rate_pct': '{:.1f}%',
                'avg_lifespan_months': '{:.1f} mos',
                'avg_mrr': '${:,.2f}',
                'realized_clv': '${:,.2f}',
                'theoretical_clv': '${:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        st.caption("💡 *Insight: Enterprise accounts have the lowest churn rate and generate over 10x the realized CLV compared to Starter tiers.*")

# ==============================================================================
# TAB 2: COHORT RETENTION HEATMAP
# ==============================================================================
with tab_cohort:
    st.subheader("Triangular Cohort Retention Analysis")
    st.markdown("Track how customer groups retain over 12 months from their initial signup date.")

    cohort_raw = analytics.get_cohort_retention()
    
    col_opt1, col_opt2 = st.columns([3, 9])
    with col_opt1:
        metric_choice = st.radio(
            "Select Metric to Visualize:",
            ["Customer Retention Rate (%)", "Revenue Retention (NDR) (%)"],
            index=0
        )
    
    value_col = 'retention_rate_pct' if metric_choice == "Customer Retention Rate (%)" else 'revenue_retention_pct'
    
    # Pivot cohort matrix
    pivot_df = cohort_raw.pivot(index='cohort_month', columns='month_index', values=value_col)
    
    # Render interactive heatmap with Altair
    heatmap_chart = alt.Chart(cohort_raw).mark_rect().encode(
        x=alt.X('month_index:O', title='Months Since Signup (Month 0 to 12)'),
        y=alt.Y('cohort_month:O', title='Signup Cohort Month', sort='ascending'),
        color=alt.Color(f'{value_col}:Q', scale=alt.Scale(scheme='blues', domain=[0, 100]), title='% Retained'),
        tooltip=[
            alt.Tooltip('cohort_month:O', title='Cohort'),
            alt.Tooltip('cohort_size:Q', title='Initial Size'),
            alt.Tooltip('month_index:O', title='Month Index'),
            alt.Tooltip(f'{value_col}:Q', title='Retained %', format='.1f'),
            alt.Tooltip('retained_customers:Q', title='Retained Accounts')
        ]
    ).properties(height=420)

    text_overlay = alt.Chart(cohort_raw).mark_text(baseline='middle').encode(
        x=alt.X('month_index:O'),
        y=alt.Y('cohort_month:O', sort='ascending'),
        text=alt.Text(f'{value_col}:Q', format='.0f'),
        color=alt.condition(alt.datum[value_col] > 50, alt.value('white'), alt.value('black'))
    )

    st.altair_chart(heatmap_chart + text_overlay, use_container_width=True)
    st.caption("📌 *Note: Month 0 is 100%. Natural attrition occurs primarily around Month 2-3 when trial/promotional discounts expire.*")

# ==============================================================================
# TAB 3: CHURN EARLY-WARNING RADAR
# ==============================================================================
with tab_radar:
    st.subheader("🚨 Real-Time Churn Early-Warning Radar")
    st.markdown("Pinpoints active accounts exhibiting leading indicators of churn (steep drop in logins, degraded health scores, unresolved support tickets).")

    risk_df = analytics.get_churn_risk_accounts()

    # Filter controls
    available_risks = list(risk_df["risk_category"].unique())
    default_risks = [r for r in ["CRITICAL RISK", "HIGH RISK", "MODERATE RISK"] if r in available_risks]
    if not default_risks and available_risks:
        default_risks = [available_risks[0]]

    available_tiers = list(risk_df["tier"].unique())
    available_industries = list(risk_df["industry"].unique())

    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        selected_risk = st.multiselect("Risk Tier:", options=available_risks, default=default_risks)
    with f_col2:
        selected_tiers = st.multiselect("Subscription Tier:", options=available_tiers, default=available_tiers)
    with f_col3:
        selected_industries = st.multiselect("Industry:", options=available_industries, default=available_industries)

    filtered_risk = risk_df[
        (risk_df["risk_category"].isin(selected_risk)) &
        (risk_df["tier"].isin(selected_tiers)) &
        (risk_df["industry"].isin(selected_industries))
    ]

    st.markdown(f"**Found {len(filtered_risk)} accounts matching filters representing `${filtered_risk['arr_at_risk'].sum():,.2f}` in ARR at risk.**")

    # Display Table
    st.dataframe(
        filtered_risk[[
            "account_id", "company_name", "tier", "industry", "monthly_mrr", "arr_at_risk",
            "risk_category", "latest_health_score", "latest_logins", "login_drop_pct",
            "total_support_tickets", "avg_csat", "escalated_tickets"
        ]].style.format({
            'monthly_mrr': '${:,.2f}',
            'arr_at_risk': '${:,.2f}',
            'login_drop_pct': '{:.1f}%',
            'latest_health_score': '{:.0f}/100',
            'avg_csat': '{:.1f} / 5.0'
        }),
        use_container_width=True,
        hide_index=True
    )

    # Download button for Customer Success team
    csv_data = filtered_risk.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export At-Risk Target List (CSV for CSM Team)",
        data=csv_data,
        file_name="churn_radar_at_risk_accounts.csv",
        mime="text/csv"
    )

# ==============================================================================
# TAB 4: WHAT-IF CAMPAIGN ROI SIMULATOR
# ==============================================================================
with tab_sim:
    st.subheader("🎯 Executive What-If Retention Campaign Simulator")
    st.markdown("Model the financial impact and Net ROI of proactive retention interventions before committing budget.")

    sim_col1, sim_col2 = st.columns([5, 7])

    with sim_col1:
        st.markdown("#### 1. Configure Campaign Parameters")
        
        target_group = st.selectbox(
            "Target Cohort:",
            ["Critical Risk Accounts Only", "Critical + High Risk Accounts", "Enterprise Tier Accounts at Risk"]
        )
        
        all_risk = analytics.get_churn_risk_accounts()
        if target_group == "Critical Risk Accounts Only":
            cohort_to_sim = all_risk[all_risk["risk_category"] == "CRITICAL RISK"]
        elif target_group == "Critical + High Risk Accounts":
            cohort_to_sim = all_risk[all_risk["risk_category"].isin(["CRITICAL RISK", "HIGH RISK"])]
        else:
            cohort_to_sim = all_risk[(all_risk["tier"] == "Enterprise") & (all_risk["risk_category"] != "HEALTHY")]

        intervention = st.selectbox(
            "Intervention Strategy:",
            [
                "Dedicated Customer Success Manager (CSM) High-Touch Intervention",
                "15% Contract Renewal Discount",
                "Technical Architecture Audit & Optimization",
                "Executive Sponsor Engagement Dinner / QBR"
            ]
        )

        cost_per_acc = st.slider(
            "Cost per Targeted Account ($):",
            min_value=50, max_value=2000, value=350, step=25,
            help="Includes personnel hours, discount allowances, and onboarding support costs."
        )

        expected_winback = st.slider(
            "Expected Win-Back / Retention Success Rate (%):",
            min_value=5, max_value=60, value=25, step=5,
            help="Percentage of targeted at-risk customers successfully prevented from churning."
        )

        horizon = st.select_slider(
            "Revenue Preservation Horizon (Months):",
            options=[6, 12, 24], value=12,
            help="Number of months of recurring revenue preserved by saving these accounts."
        )

    with sim_col2:
        st.markdown("#### 2. Projected Financial Return")
        
        results = RetentionSimulator.simulate_campaign(
            target_accounts_df=cohort_to_sim,
            intervention_type=intervention,
            intervention_cost_per_account=cost_per_acc,
            expected_winback_rate_pct=expected_winback,
            time_horizon_months=horizon
        )

        res_c1, res_c2 = st.columns(2)
        with res_c1:
            st.metric("Targeted Accounts", f"{results['targeted_count']:,} accounts")
            st.metric("Total Campaign Budget", f"${results['total_campaign_cost']:,.2f}")
            st.metric("Payback Period", f"{results['payback_months']:.1f} months")
        with res_c2:
            st.metric("Projected Saved Accounts", f"{results['expected_saved_accounts']:.1f} accounts")
            st.metric("Gross Revenue Preserved", f"${results['gross_revenue_saved']:,.2f}")
            st.metric(
                "Net Dollar Profit Saved",
                f"${results['net_profit_saved']:,.2f}",
                delta=f"{results['roi_percentage']:.1f}% Net ROI"
            )

        st.markdown("---")
        st.markdown("#### 3. Sensitivity Analysis (ROI vs Win-Back Rate)")
        
        # Sensitivity curves
        rates = list(range(5, 55, 5))
        curve_data = []
        for r in rates:
            sim_res = RetentionSimulator.simulate_campaign(
                cohort_to_sim, intervention, cost_per_acc, r, horizon
            )
            curve_data.append({
                "Winback Rate (%)": r,
                "Net Profit Saved ($)": sim_res["net_profit_saved"],
                "ROI (%)": sim_res["roi_percentage"]
            })
        
        df_curve = pd.DataFrame(curve_data)
        chart_roi = alt.Chart(df_curve).mark_line(point=True, color='#16A34A').encode(
            x=alt.X('Winback Rate (%):Q', title='Win-Back Success Rate (%)'),
            y=alt.Y('Net Profit Saved ($):Q', title='Net Profit Saved ($)', axis=alt.Axis(format='$,.0f')),
            tooltip=['Winback Rate (%):Q', alt.Tooltip('Net Profit Saved ($):Q', format='$,.0f'), 'ROI (%):Q']
        ).properties(height=240)
        st.altair_chart(chart_roi, use_container_width=True)

# ==============================================================================
# TAB 5: PRODUCTION SQL LAB
# ==============================================================================
with tab_sql:
    st.subheader("💻 Production SQL Codebase & Query Execution")
    st.markdown("Inspect the modular, production-grade SQL scripts powering this system.")

    sql_files = {
        "1. MRR, ARR & MoM Trajectory": "01_mrr_arr_metrics.sql",
        "2. Cohort Retention Heatmap": "02_cohort_retention.sql",
        "3. Churn Early-Risk Detection": "03_churn_risk_detection.sql",
        "4. Customer Lifetime Value (CLV)": "04_customer_lifetime_value.sql"
    }

    selected_file_label = st.selectbox("Select SQL Query to Inspect:", list(sql_files.keys()))
    sql_filename = sql_files[selected_file_label]
    sql_code = analytics.load_sql_query(sql_filename)

    st.code(sql_code, language="sql")

    if st.button(f"▶️ Execute `{sql_filename}` against SQLite Database"):
        with st.spinner("Executing query..."):
            query_result = analytics.run_query(sql_code)
            st.success(f"Query returned {len(query_result)} rows successfully!")
            st.dataframe(query_result.head(50), use_container_width=True)
