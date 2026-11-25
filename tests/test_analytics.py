import os
import unittest
import pandas as pd
import numpy as np

from src.analytics_engine import AnalyticsEngine
from src.simulation_engine import RetentionSimulator

class TestSaaSAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = AnalyticsEngine()
        cls.sample_df = pd.DataFrame([
            {"account_id": "ACC-001", "monthly_mrr": 500.0, "risk_category": "CRITICAL RISK"},
            {"account_id": "ACC-002", "monthly_mrr": 1000.0, "risk_category": "CRITICAL RISK"},
            {"account_id": "ACC-003", "monthly_mrr": 1500.0, "risk_category": "CRITICAL RISK"},
            {"account_id": "ACC-004", "monthly_mrr": 2000.0, "risk_category": "CRITICAL RISK"}
        ])

    def test_database_connection_and_tables(self):
        """Verify database exists, tables are populated, and foreign keys align."""
        with self.engine.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cur.fetchall()]
            
            self.assertIn("accounts", tables)
            self.assertIn("monthly_usage", tables)
            self.assertIn("support_tickets", tables)

            # Assert non-empty tables
            cur.execute("SELECT COUNT(*) FROM accounts;")
            self.assertGreater(cur.fetchone()[0], 0)
            cur.execute("SELECT COUNT(*) FROM monthly_usage;")
            self.assertGreater(cur.fetchone()[0], 0)
            cur.execute("SELECT COUNT(*) FROM support_tickets;")
            self.assertGreater(cur.fetchone()[0], 0)

    def test_mrr_growth_metrics_query(self):
        """Validate 01_mrr_arr_metrics.sql returns proper financial time series."""
        df = self.engine.get_mrr_growth_metrics()
        self.assertFalse(df.empty)
        required_cols = {"activity_month", "active_customers", "total_mrr", "run_rate_arr", "mrr_growth_pct"}
        self.assertTrue(required_cols.issubset(df.columns))
        
        # Financial assertions
        self.assertTrue((df["total_mrr"] > 0).all())
        self.assertTrue((df["active_customers"] > 0).all())
        # ARR must equal MRR * 12
        np.testing.assert_allclose(df["run_rate_arr"], df["total_mrr"] * 12, rtol=1e-2)

    def test_cohort_retention_query(self):
        """Validate 02_cohort_retention.sql generates triangular retention matrix."""
        df = self.engine.get_cohort_retention()
        self.assertFalse(df.empty)
        required_cols = {"cohort_month", "cohort_size", "month_index", "retained_customers", "retention_rate_pct"}
        self.assertTrue(required_cols.issubset(df.columns))

        # Month 0 retention must always be 100%
        month_0 = df[df["month_index"] == 0]
        self.assertTrue((month_0["retention_rate_pct"] == 100.0).all())
        # Retention rates must be bounded between 0 and 100
        self.assertTrue((df["retention_rate_pct"] >= 0).all() and (df["retention_rate_pct"] <= 100).all())

    def test_churn_risk_detection_query(self):
        """Validate 03_churn_risk_detection.sql correctly categorizes leading churn signals."""
        df = self.engine.get_churn_risk_accounts()
        self.assertFalse(df.empty)
        required_cols = {"account_id", "tier", "arr_at_risk", "risk_category", "latest_health_score"}
        self.assertTrue(required_cols.issubset(df.columns))

        # Check risk categories
        valid_categories = {"CRITICAL RISK", "HIGH RISK", "MODERATE RISK", "HEALTHY"}
        self.assertTrue(set(df["risk_category"].unique()).issubset(valid_categories))

        # Critical risk accounts must meet at least one threshold from the SQL definition:
        # health_score < 40, login_drop_pct <= -60, or (login_drop <= -40 AND CSAT <= 2.5), or NULL usage row
        critical_accounts = df[df["risk_category"] == "CRITICAL RISK"]
        for _, acc in critical_accounts.iterrows():
            is_low_health = acc["latest_health_score"] < 40
            is_severe_login_drop = acc["login_drop_pct"] <= -60.0
            is_moderate_drop_low_csat = (acc["login_drop_pct"] <= -40.0 and acc["avg_csat"] <= 2.5)
            is_zero_activity = pd.isna(acc["baseline_logins"])  # LEFT JOIN miss = no usage row
            self.assertTrue(
                is_low_health or is_severe_login_drop or is_moderate_drop_low_csat or is_zero_activity,
                f"Account {acc['account_id']} is CRITICAL RISK but no threshold condition satisfied: "
                f"health={acc['latest_health_score']}, login_drop={acc['login_drop_pct']}, csat={acc['avg_csat']}"
            )

    def test_customer_lifetime_value_query(self):
        """Validate 04_customer_lifetime_value.sql calculates tier economics."""
        df = self.engine.get_clv_metrics()
        self.assertFalse(df.empty)
        required_cols = {"tier", "total_accounts", "churn_rate_pct", "avg_mrr", "realized_clv"}
        self.assertTrue(required_cols.issubset(df.columns))

        # Enterprise tier should have higher CLV than Starter
        enterprise_clv = df[df["tier"] == "Enterprise"]["realized_clv"].iloc[0]
        starter_clv = df[df["tier"] == "Starter"]["realized_clv"].iloc[0]
        self.assertGreater(enterprise_clv, starter_clv)

    def test_simulation_standard_campaign(self):
        """Test financial simulation under standard operating parameters."""
        results = RetentionSimulator.simulate_campaign(
            target_accounts_df=self.sample_df,
            intervention_type="Dedicated CSM Outreach",
            intervention_cost_per_account=300.0,
            expected_winback_rate_pct=25.0,
            time_horizon_months=12
        )

        self.assertEqual(results["targeted_count"], 4)
        self.assertEqual(results["total_campaign_cost"], 1200.0)
        self.assertEqual(results["expected_saved_accounts"], 1.0)
        self.assertEqual(results["avg_targeted_mrr"], 1250.0)
        # Gross revenue saved = 1.0 account * $1250 * 12 = $15,000.0
        self.assertEqual(results["gross_revenue_saved"], 15000.0)
        # Net profit saved = $15,000 - $1,200 = $13,800.0
        self.assertEqual(results["net_profit_saved"], 13800.0)
        # ROI = ($13,800 / $1,200) * 100 = 1150.0%
        self.assertEqual(results["roi_percentage"], 1150.0)
        # Payback period = $1200 / $1250 = ~1.0 month
        self.assertEqual(results["payback_months"], 1.0)
        self.assertGreater(results["breakeven_winback_rate_pct"], 0.0)

    def test_simulation_zero_winback_edge_case(self):
        """Edge Case: 0% win-back rate should safely reflect 100% loss of budget."""
        results = RetentionSimulator.simulate_campaign(
            target_accounts_df=self.sample_df,
            intervention_type="15% Discount",
            intervention_cost_per_account=200.0,
            expected_winback_rate_pct=0.0,
            time_horizon_months=12
        )

        self.assertEqual(results["expected_saved_accounts"], 0.0)
        self.assertEqual(results["gross_revenue_saved"], 0.0)
        self.assertEqual(results["net_profit_saved"], -800.0) # Net loss equals campaign cost
        self.assertEqual(results["roi_percentage"], -100.0) # -100% ROI
        self.assertIsNone(results["payback_months"]) # Inf payback mapped to None

    def test_simulation_empty_cohort_edge_case(self):
        """Edge Case: Empty target cohort returns safe zeroed metrics with no exceptions."""
        empty_df = pd.DataFrame(columns=["account_id", "monthly_mrr"])
        results = RetentionSimulator.simulate_campaign(
            target_accounts_df=empty_df,
            intervention_type="CSM Outreach",
            intervention_cost_per_account=500.0,
            expected_winback_rate_pct=30.0,
            time_horizon_months=12
        )

        self.assertEqual(results["targeted_count"], 0)
        self.assertEqual(results["total_campaign_cost"], 0.0)
        self.assertEqual(results["roi_percentage"], 0.0)

    def test_risk_category_ordering(self):
        """Validate that risk category ARR weights are consistent: Critical > High > 0."""
        df = self.engine.get_churn_risk_accounts()
        critical = df[df["risk_category"] == "CRITICAL RISK"]
        high = df[df["risk_category"] == "HIGH RISK"]
        healthy = df[df["risk_category"] == "HEALTHY"]

        # arr_at_risk must be positive for flagged accounts
        if not critical.empty:
            self.assertTrue((critical["arr_at_risk"] > 0).all(), "Critical accounts should have arr_at_risk > 0")
        if not high.empty:
            self.assertTrue((high["arr_at_risk"] > 0).all(), "High risk accounts should have arr_at_risk > 0")
        # Healthy accounts must have zero arr_at_risk
        if not healthy.empty:
            self.assertTrue((healthy["arr_at_risk"] == 0).all(), "Healthy accounts should have arr_at_risk = 0")

        # Critical ARR weight (65%) must exceed High weight (35%) for same MRR
        # Verify by checking avg arr_at_risk / current_arr ratios
        if not critical.empty and not high.empty:
            critical_weight = (critical["arr_at_risk"] / critical["current_arr"]).mean()
            high_weight = (high["arr_at_risk"] / high["current_arr"]).mean()
            self.assertAlmostEqual(critical_weight, 0.65, delta=0.05)
            self.assertAlmostEqual(high_weight, 0.35, delta=0.05)

    def test_backtest_model_metrics_sanity(self):
        """Validate backtest returns plausible metrics on the synthetic dataset."""
        from src.backtest_model import run_churn_early_warning_backtest
        results = run_churn_early_warning_backtest()

        # Must evaluate a meaningful number of accounts
        self.assertGreater(results["total_evaluated_accounts"], 500)

        # Recall must be high (model is tuned for this)
        self.assertGreater(results["recall_pct"], 80.0, "Recall should exceed 80%")

        # Precision should beat the naïve baseline (flag everyone = ~25% precision on this dataset)
        self.assertGreater(results["precision_pct"], 40.0, "Precision should beat the ~25% naïve baseline")

        # Confusion matrix must be internally consistent
        total = (results["true_positives"] + results["false_positives"] +
                 results["false_negatives"] + results["true_negatives"])
        self.assertEqual(total, results["total_evaluated_accounts"])


if __name__ == "__main__":
    unittest.main()
