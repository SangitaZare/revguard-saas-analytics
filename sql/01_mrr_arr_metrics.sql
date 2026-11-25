-- ==============================================================================
-- 01_mrr_arr_metrics.sql
-- Goal: Calculate Monthly Recurring Revenue (MRR), ARR, and MoM Growth Trajectory
-- Technique: Common Table Expressions (CTEs), LAG() Window Function, Rounding
-- ==============================================================================

WITH MonthlyRevenue AS (
    SELECT 
        activity_month,
        COUNT(DISTINCT account_id) AS active_customers,
        ROUND(SUM(monthly_mrr), 2) AS total_mrr,
        ROUND(AVG(monthly_mrr), 2) AS arpu -- Average Revenue Per User
    FROM monthly_usage
    GROUP BY activity_month
),
MoMGrowth AS (
    SELECT 
        activity_month,
        active_customers,
        total_mrr,
        ROUND(total_mrr * 12, 2) AS run_rate_arr,
        arpu,
        LAG(total_mrr, 1) OVER (ORDER BY activity_month ASC) AS prev_month_mrr,
        LAG(active_customers, 1) OVER (ORDER BY activity_month ASC) AS prev_active_customers
    FROM MonthlyRevenue
)
SELECT 
    activity_month,
    active_customers,
    total_mrr,
    run_rate_arr,
    arpu,
    COALESCE(prev_month_mrr, total_mrr) AS prev_month_mrr,
    ROUND(total_mrr - COALESCE(prev_month_mrr, total_mrr), 2) AS net_new_mrr,
    CASE 
        WHEN prev_month_mrr IS NULL OR prev_month_mrr = 0 THEN 0.0
        ELSE ROUND(((total_mrr - prev_month_mrr) * 100.0) / prev_month_mrr, 2)
    END AS mrr_growth_pct,
    (active_customers - COALESCE(prev_active_customers, active_customers)) AS net_new_customers
FROM MoMGrowth
ORDER BY activity_month ASC;
