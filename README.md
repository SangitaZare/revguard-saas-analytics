# 🛡️ RevGuard: SaaS Customer Retention & Revenue-at-Risk Simulator

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-Advanced%20CTEs%20%26%20Window%20Functions-orange.svg)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-Interactive%20App-FF4B4B.svg)](https://streamlit.io/)
[![Business Impact](https://img.shields.io/badge/Business%20Impact-%241.4M%20ARR%20Identified-success.svg)]()

> An end-to-end B2B SaaS analytics intelligence engine that bridges raw database queries with executive financial decision-making. Pinpoints high-risk accounts using leading behavioral indicators and simulates the Net ROI of retention campaigns.

---

## 📌 Executive Summary & Business Problem

In high-growth B2B SaaS companies, **customer churn is the silent killer of Annual Recurring Revenue (ARR)**. Most analytics teams report churn *after* the customer cancels—when it is already too late.

* **Target Organization:** A B2B SaaS enterprise generating **$8.72M in ARR** across 900+ active enterprise, professional, and starter accounts.
* **The Vulnerability:** 149 accounts exhibited severe usage degradation, representing **$1,435,212 in ARR at risk (16.5% exposure)**.
* **The Solution:** Built **RevGuard**, an early-warning churn detection engine and interactive financial simulator that models proactive customer success interventions to project Net ROI and payback periods before committing marketing spend.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐
│     Raw Relational Data         │
│ (Accounts, Usage Logs, Tickets) │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    SQLite Analytics Database    │
│  (Indexed for High Performance) │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Production SQL Engine       │
│  • Multi-Level CTEs             │
│  • Window Functions (LAG, OVER) │
│  • Triangular Retention Cohorts │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Python Analytical Engine      │
│  • Leading Churn Indicators     │
│  • Financial Simulation Engine  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Interactive Executive UI      │
│  • Real-time Churn Radar        │
│  • "What-If" ROI Simulator      │
│  • Live SQL Execution Lab       │
└─────────────────────────────────┘
```

---

## 🎯 Key Business Questions Answered

1. **Revenue Run-Rate & Trajectory:** What is our current MRR, ARR, and month-over-month growth rate?
2. **Cohort Health:** At which specific month of customer tenure do we experience the steepest drop-off?
3. **Leading Churn Indicators:** Can we detect churn 60 days *before* cancellation through login velocity and support ticket escalation?
4. **Financial Simulation:** If leadership invests \$50,000 in dedicated CSM outreach, how many accounts must be saved to break even, and what is the expected Net Profit?

---

## 📊 Core Features & Capabilities

### 1. 📈 Triangular Cohort Retention Matrix
* Visualizes month-over-month customer retention and Net Dollar Retention (NDR) from Month 0 to Month 12.
* Pinpoints Month 2–3 as the primary friction window (promotional expiry).

### 2. 🚨 Churn Early-Warning Radar
* Filters accounts by **Composite Risk Score**:
  * **Critical Risk:** Health score < 40, login drop > 50%, or negative CSAT.
  * **High Risk:** Health score 40–60 with declining seat utilization.
* Generates an actionable CSV export for the Customer Success Management (CSM) team.

### 3. 🎯 What-If Retention Campaign Simulator
* Allows executives to adjust:
  * **Target Cohort:** Critical vs. High-Risk accounts.
  * **Intervention Strategy:** CSM outreach, pricing discount, or executive business review.
  * **Cost per Account:** \$50 to \$2,000.
  * **Expected Win-Back Rate:** 5% to 60%.
* Outputs: **Total Budget**, **Gross ARR Preserved**, **Net Saved Revenue**, **ROI %**, and **Payback Period in Months**.

### 4. 💻 Production SQL Lab
* Allows technical recruiters and hiring managers to inspect and execute the production SQL queries directly within the application.

---

## 🗄️ SQL Techniques Demonstrated

All queries are located in the [`sql/`](sql/) directory:
* [`01_mrr_arr_metrics.sql`](sql/01_mrr_arr_metrics.sql): Common Table Expressions (CTEs), `LAG()` window function, MoM growth calculations.
* [`02_cohort_retention.sql`](sql/02_cohort_retention.sql): Triangular retention grid, cross-cohort month indexing, Net Revenue Retention (NDR).
* [`03_churn_risk_detection.sql`](sql/03_churn_risk_detection.sql): Rolling averages, login drop percentage, composite health classification.
* [`04_customer_lifetime_value.sql`](sql/04_customer_lifetime_value.sql): Grouped aggregations, realized vs theoretical CLV modeling.

---

## 🚀 Quickstart: Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/your-username/revguard-saas-analytics.git
cd revguard-saas-analytics
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Re-generate data & build SQLite database
```bash
python src/data_generator.py
```

### 4. Launch the Interactive Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 💼 Resume & Interview Pitch

### Resume Bullet Points:
> * **RevGuard: SaaS Customer Retention & Revenue-at-Risk Engine | SQL, Python, Streamlit**
>   * Engineered an end-to-end B2B SaaS analytics engine analyzing 1,200+ accounts and 14,000+ usage records using advanced SQL (CTEs, Window Functions) and SQLite.
>   * Uncovered \$1.43M in ARR at risk (16.5% exposure) by designing a multi-factor churn early-warning model based on login decay and support CSAT trends.
>   * Built an interactive Streamlit executive app featuring a What-If Campaign Simulator that modeled dynamic intervention costs, projecting a 3.4x Net ROI on retention budgets.

### 30-Second Interview Pitch:
> *"Most churn projects only look backward at who already canceled. For RevGuard, I wanted to build an executive decision tool that bridges data with dollars. I used advanced SQL window functions and cohort analysis to identify $1.4M in vulnerable ARR, and then built an interactive financial simulator in Streamlit that allows leadership to test retention campaign budgets, win-back rates, and calculate net ROI in real-time."*
