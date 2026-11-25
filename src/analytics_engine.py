import os
import sqlite3
import pandas as pd

class AnalyticsEngine:
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "saas_analytics.db")
        self.db_path = db_path
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def load_sql_query(self, filename):
        filepath = os.path.join(self.base_dir, "sql", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def run_query(self, query):
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn)

    def get_mrr_growth_metrics(self):
        sql = self.load_sql_query("01_mrr_arr_metrics.sql")
        return self.run_query(sql)

    def get_cohort_retention(self):
        sql = self.load_sql_query("02_cohort_retention.sql")
        return self.run_query(sql)

    def get_churn_risk_accounts(self):
        sql = self.load_sql_query("03_churn_risk_detection.sql")
        return self.run_query(sql)

    def get_clv_metrics(self):
        sql = self.load_sql_query("04_customer_lifetime_value.sql")
        return self.run_query(sql)

    def get_executive_kpis(self):
        # Summary high-level metrics for C-suite view
        with self.get_connection() as conn:
            latest_month_mrr = pd.read_sql_query(
                "SELECT SUM(monthly_mrr) as current_mrr, COUNT(DISTINCT account_id) as active_accounts "
                "FROM monthly_usage WHERE activity_month = (SELECT MAX(activity_month) FROM monthly_usage)", 
                conn
            ).iloc[0]
            
            churn_stats = pd.read_sql_query(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN status='Churned' THEN 1 ELSE 0 END) as churned "
                "FROM accounts", 
                conn
            ).iloc[0]

            risk_df = self.get_churn_risk_accounts()
            critical_risk = risk_df[risk_df["risk_category"] == "CRITICAL RISK"]
            high_risk = risk_df[risk_df["risk_category"] == "HIGH RISK"]

            total_arr = latest_month_mrr["current_mrr"] * 12
            revenue_at_risk_arr = float(risk_df["arr_at_risk"].sum())
            gross_exposed_arr = float(risk_df["gross_arr_exposed"].sum())

            return {
                "current_mrr": float(latest_month_mrr["current_mrr"]),
                "current_arr": float(total_arr),
                "active_accounts": int(latest_month_mrr["active_accounts"]),
                "overall_churn_rate": round((churn_stats["churned"] / churn_stats["total"]) * 100, 1),
                "critical_risk_accounts": len(critical_risk),
                "high_risk_accounts": len(high_risk),
                "arr_at_risk": round(revenue_at_risk_arr, 2),
                "gross_exposed_arr": round(gross_exposed_arr, 2),
                "risk_exposure_pct": round((revenue_at_risk_arr / total_arr) * 100, 1) if total_arr > 0 else 0.0
            }
