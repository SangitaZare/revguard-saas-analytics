import pandas as pd

class RetentionSimulator:
    """
    Financial Simulation Engine for SaaS Retention Campaigns.
    
    Provides executive decision modeling:
    - Campaign Cost vs. Retained Annual Recurring Revenue (ARR)
    - Net Saved Revenue, Return on Investment (ROI %), and Payback Period
    - Break-Even Win-Back Rate analysis
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
        - target_accounts_df (pd.DataFrame): DataFrame of selected accounts at risk
        - intervention_type (str): e.g., 'Dedicated CSM Outreach', '15% Renewal Discount'
        - intervention_cost_per_account (float): Dollar budget spent per targeted account
        - expected_winback_rate_pct (float): Expected % of targeted at-risk accounts saved (0-100)
        - time_horizon_months (int): Horizon for preserved recurring revenue (default 12 mos = 1 ARR cycle)
        
        Returns:
        - dict: Comprehensive financial outcome metrics including break-even rate
        """
        targeted_count = len(target_accounts_df)
        if targeted_count == 0:
            return {
                "targeted_count": 0,
                "total_campaign_cost": 0.0,
                "expected_saved_accounts": 0.0,
                "avg_targeted_mrr": 0.0,
                "gross_revenue_saved": 0.0,
                "net_profit_saved": 0.0,
                "roi_percentage": 0.0,
                "payback_months": 0.0,
                "breakeven_winback_rate_pct": 0.0
            }

        # 1. Total Campaign Cost
        total_campaign_cost = float(targeted_count * intervention_cost_per_account)
        
        # 2. Account Recovery
        winback_fraction = max(0.0, min(100.0, float(expected_winback_rate_pct))) / 100.0
        expected_saved_accounts = round(targeted_count * winback_fraction, 1)

        # 3. Average MRR of targeted cohort
        avg_targeted_mrr = float(target_accounts_df["monthly_mrr"].mean())
        
        # 4. Gross Revenue Preserved over the specified time horizon
        # Formula: Recovered Accounts * Average MRR * Horizon (Months)
        gross_revenue_saved = expected_saved_accounts * avg_targeted_mrr * float(time_horizon_months)
        
        # 5. Net Profit Saved (Gross Revenue Preserved - Direct Campaign Cost)
        net_profit_saved = gross_revenue_saved - total_campaign_cost
        
        # 6. Return on Investment (ROI %)
        # Formula: (Net Profit Saved / Total Campaign Cost) * 100
        roi_percentage = (net_profit_saved / total_campaign_cost * 100.0) if total_campaign_cost > 0 else 0.0
        
        # 7. Payback Period (Months)
        monthly_revenue_saved = expected_saved_accounts * avg_targeted_mrr
        if monthly_revenue_saved > 0:
            payback_months = total_campaign_cost / monthly_revenue_saved
        else:
            payback_months = float('inf') if total_campaign_cost > 0 else 0.0

        # 8. Break-Even Win-Back Rate
        # Minimum win-back % required for Net Profit Saved = $0
        max_potential_revenue = targeted_count * avg_targeted_mrr * float(time_horizon_months)
        if max_potential_revenue > 0:
            breakeven_winback_rate_pct = min(100.0, (total_campaign_cost / max_potential_revenue) * 100.0)
        else:
            breakeven_winback_rate_pct = 0.0

        return {
            "targeted_count": targeted_count,
            "total_campaign_cost": round(total_campaign_cost, 2),
            "expected_saved_accounts": expected_saved_accounts,
            "avg_targeted_mrr": round(avg_targeted_mrr, 2),
            "gross_revenue_saved": round(gross_revenue_saved, 2),
            "net_profit_saved": round(net_profit_saved, 2),
            "roi_percentage": round(roi_percentage, 1),
            "payback_months": round(payback_months, 1) if payback_months != float('inf') else None,
            "breakeven_winback_rate_pct": round(breakeven_winback_rate_pct, 1)
        }
