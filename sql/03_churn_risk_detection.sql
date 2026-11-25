-- ==============================================================================
-- 03_churn_risk_detection.sql
-- Goal: Identify Active Accounts with Severe Usage Drop-off Signals (Revenue at Risk)
-- Technique: Window functions (LAG), Rolling Averages, Multi-Factor Health Risk Scoring
-- ==============================================================================

WITH RecentUsage AS (
    SELECT 
        account_id,
        activity_month,
        monthly_mrr,
        total_logins,
        features_adopted,
        account_health_score,
        -- Fetch previous month activity using LAG window function
        LAG(total_logins, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_logins,
        LAG(account_health_score, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_health_score,
        -- Rank to identify the most recent observed month
        ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY activity_month DESC) AS recency_rank
    FROM monthly_usage
),
SupportMetrics AS (
    SELECT 
        account_id,
        COUNT(ticket_id) AS total_tickets,
        ROUND(AVG(csat_score), 2) AS avg_csat,
        SUM(is_escalated) AS escalated_tickets
    FROM support_tickets
    GROUP BY account_id
)
SELECT 
    a.account_id,
    a.company_name,
    a.industry,
    a.tier,
    a.contract_type,
    r.monthly_mrr,
    ROUND(r.monthly_mrr * 12, 2) AS arr_at_risk,
    r.account_health_score AS latest_health_score,
    r.prev_health_score,
    (r.account_health_score - r.prev_health_score) AS health_score_change,
    r.total_logins AS latest_logins,
    r.prev_logins,
    CASE 
        WHEN r.prev_logins > 0 
        THEN ROUND(((r.total_logins - r.prev_logins) * 100.0) / r.prev_logins, 1)
        ELSE 0.0 
    END AS login_drop_pct,
    COALESCE(s.total_tickets, 0) AS total_support_tickets,
    COALESCE(s.avg_csat, 5.0) AS avg_csat,
    COALESCE(s.escalated_tickets, 0) AS escalated_tickets,
    -- Composite Churn Risk Tier
    CASE 
        WHEN r.account_health_score < 40 OR (r.total_logins < r.prev_logins * 0.50 AND s.avg_csat <= 2.5) THEN 'CRITICAL RISK'
        WHEN r.account_health_score < 60 OR (r.total_logins < r.prev_logins * 0.70) THEN 'HIGH RISK'
        WHEN r.account_health_score < 75 THEN 'MODERATE RISK'
        ELSE 'HEALTHY'
    END AS risk_category
FROM accounts a
JOIN RecentUsage r ON a.account_id = r.account_id AND r.recency_rank = 1
LEFT JOIN SupportMetrics s ON a.account_id = s.account_id
WHERE a.status = 'Active'
ORDER BY arr_at_risk DESC, r.account_health_score ASC;
