-- ==============================================================================
-- 04_customer_lifetime_value.sql
-- Goal: Calculate Customer Lifetime Value (CLV) and Retention Economics by Tier & Industry
-- Technique: Aggregations, Conditional Net Margins, Tenure Calculation
-- ==============================================================================

WITH CustomerTenureAndSpend AS (
    SELECT 
        a.account_id,
        a.company_name,
        a.tier,
        a.industry,
        a.status,
        a.signup_date,
        a.churn_date,
        COUNT(u.activity_month) AS active_tenure_months,
        ROUND(SUM(u.monthly_mrr), 2) AS cumulative_lifetime_revenue,
        ROUND(AVG(u.monthly_mrr), 2) AS avg_monthly_revenue
    FROM accounts a
    JOIN monthly_usage u ON a.account_id = u.account_id
    GROUP BY a.account_id
)
SELECT 
    tier,
    COUNT(account_id) AS total_accounts,
    SUM(CASE WHEN status = 'Churned' THEN 1 ELSE 0 END) AS churned_accounts,
    ROUND((SUM(CASE WHEN status = 'Churned' THEN 1.0 ELSE 0.0 END) * 100.0) / COUNT(account_id), 1) AS churn_rate_pct,
    ROUND(AVG(active_tenure_months), 1) AS avg_lifespan_months,
    ROUND(AVG(avg_monthly_revenue), 2) AS avg_mrr,
    ROUND(AVG(cumulative_lifetime_revenue), 2) AS realized_clv,
    -- Theoretical CLV formula: (ARPU * Gross Margin 80%) / Churn Rate
    ROUND(
        (AVG(avg_monthly_revenue) * 0.80) / 
        NULLIF((SUM(CASE WHEN status = 'Churned' THEN 1.0 ELSE 0.0 END) / COUNT(account_id)), 0)
    , 2) AS theoretical_clv
FROM CustomerTenureAndSpend
GROUP BY tier
ORDER BY realized_clv DESC;
