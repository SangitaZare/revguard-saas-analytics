import pandas as pd

class RetentionSimulator:
    """
    Financial Simulation Engine for SaaS Retention Campaigns.
    Allows leadership to simulate:
    - What happens if we deploy Customer Success Manager (CSM) interventions or pricing discounts?
    - What is the campaign cost vs. retained lifetime revenue?
    - What is the expected Net Saved Revenue and ROI?
    """

    @staticmethod
    def simulate_campaign(
        target_accounts_df: pd.DataFrame,
        intervention_type: str,
        intervention_cost_per_account: float,
        expected_winback_rate_pct: float,
        time_horizon_months: int = 12
    ):
        """
        Runs the financial simulation.
        
        Parameters:
        - target_accounts_df: DataFrame of selected accounts at risk
        - intervention_type: e.g., 'Dedicated CSM Outreach', '15% Renewal Discount', 'Custom Training & Onboarding'
        - intervention_cost_per_account: Dollar cost spent per targeted account
        - expected_winback_rate_pct: Expected % of targeted at-risk accounts that will be saved
        - time_horizon_months: Duration for which saved MRR is preserved (default 12 months = 1 ARR cycle)
        """
        targeted_count = len(target_accounts_df)
        if targeted_count == 0:
            return {
                "targeted_count": 0,
                "total_campaign_cost": 0.0,
                "expected_saved_accounts": 0,
                "gross_revenue_saved": 0.0,
                "net_profit_saved": 0.0,
                "roi_percentage": 0.0,
                "payback_months": 0.0
            }

        total_campaign_cost = targeted_count * intervention_cost_per_account
        winback_fraction = expected_winback_rate_pct / 100.0
        expected_saved_accounts = round(targeted_count * winback_fraction, 1)

        # Average MRR of targeted cohort
        avg_targeted_mrr = target_accounts_df["monthly_mrr"].mean()
        
        # Gross revenue saved over the specified time horizon
        gross_revenue_saved = expected_saved_accounts * avg_targeted_mrr * time_horizon_months
        
        # Net savings after deducting campaign budget
        net_profit_saved = gross_revenue_saved - total_campaign_cost
        
        # Return on Investment (%)
        roi_percentage = (net_profit_saved / total_campaign_cost * 100.0) if total_campaign_cost > 0 else 0.0
        
        # Payback period in months: Cost / (Monthly revenue saved)
        monthly_revenue_saved = expected_saved_accounts * avg_targeted_mrr
        payback_months = (total_campaign_cost / monthly_revenue_saved) if monthly_revenue_saved > 0 else 0.0

        return {
            "targeted_count": targeted_count,
            "total_campaign_cost": round(total_campaign_cost, 2),
            "expected_saved_accounts": expected_saved_accounts,
            "avg_targeted_mrr": round(avg_targeted_mrr, 2),
            "gross_revenue_saved": round(gross_revenue_saved, 2),
            "net_profit_saved": round(net_profit_saved, 2),
            "roi_percentage": round(roi_percentage, 1),
            "payback_months": round(payback_months, 1)
        }
