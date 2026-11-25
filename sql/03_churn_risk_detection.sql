-- ==============================================================================
-- 03_churn_risk_detection.sql
-- Goal: Identify Active Accounts with Severe Usage Drop-off Signals (Revenue at Risk)
-- Technique: Multi-level CTEs, 3-Month Rolling Averages, Window Functions (LAG, OVER),
--            Recent Window Filtering, and Accurate Revenue-at-Risk Allocation
-- ==============================================================================

WITH MaxDate AS (
    -- Anchor to the latest observation period to guard against stale historical snapshots
    SELECT MAX(activity_month) AS latest_month FROM monthly_usage
),
UsageRollingStats AS (
    SELECT 
        account_id,
        activity_month,
        monthly_mrr,
        total_logins,
        features_adopted,
        account_health_score,
        -- Prior month login volume via LAG
        LAG(total_logins, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_month_logins,
        -- 3-Month Rolling Average of login activity prior to the current month
        AVG(total_logins) OVER (
            PARTITION BY account_id ORDER BY activity_month ASC
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS avg_logins_prior_3m,
        LAG(account_health_score, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_health_score
    FROM monthly_usage
),
CurrentMonthUsage AS (
    SELECT 
        u.*,
        COALESCE(u.avg_logins_prior_3m, u.prev_month_logins) AS baseline_logins,
        CASE 
            WHEN COALESCE(u.avg_logins_prior_3m, u.prev_month_logins, 0) > 0 
            THEN ROUND(((u.total_logins - COALESCE(u.avg_logins_prior_3m, u.prev_month_logins)) * 100.0) / 
                       COALESCE(u.avg_logins_prior_3m, u.prev_month_logins), 1)
            ELSE 0.0 
        END AS login_drop_pct
    FROM UsageRollingStats u
    JOIN MaxDate m ON u.activity_month = m.latest_month
),
RecentSupportMetrics AS (
    -- Limit support ticket evaluation to recent window (last 6 months)
    SELECT 
        account_id,
        COUNT(ticket_id) AS total_recent_tickets,
        ROUND(AVG(csat_score), 2) AS avg_csat,
        SUM(is_escalated) AS escalated_tickets
    FROM support_tickets
    WHERE created_at >= (SELECT DATE(latest_month, '-6 months') FROM MaxDate)
    GROUP BY account_id
),
ScoredAccounts AS (
    SELECT 
        a.account_id,
        a.company_name,
        a.industry,
        a.tier,
        a.contract_type,
        c.monthly_mrr,
        ROUND(c.monthly_mrr * 12, 2) AS current_arr,
        c.account_health_score AS latest_health_score,
        c.prev_health_score,
        (c.account_health_score - c.prev_health_score) AS health_score_change,
        c.total_logins AS latest_logins,
        c.baseline_logins,
        c.login_drop_pct,
        COALESCE(s.total_recent_tickets, 0) AS recent_support_tickets,
        COALESCE(s.avg_csat, 5.0) AS avg_csat,
        COALESCE(s.escalated_tickets, 0) AS escalated_tickets,
        -- Robust Composite Churn Risk Classification (with NULL-safe CSAT evaluation)
        CASE 
            WHEN c.account_health_score < 40 
              OR c.login_drop_pct <= -60.0 
              OR (c.login_drop_pct <= -40.0 AND COALESCE(s.avg_csat, 5.0) <= 2.5) 
            THEN 'CRITICAL RISK'
            WHEN c.account_health_score < 60 
              OR c.login_drop_pct <= -30.0 
              OR COALESCE(s.escalated_tickets, 0) >= 2 
            THEN 'HIGH RISK'
            WHEN c.account_health_score < 75 
            THEN 'MODERATE RISK'
            ELSE 'HEALTHY'
        END AS risk_category
    FROM accounts a
    JOIN CurrentMonthUsage c ON a.account_id = c.account_id
    LEFT JOIN RecentSupportMetrics s ON a.account_id = s.account_id
    WHERE a.status = 'Active'
)
SELECT 
    account_id,
    company_name,
    industry,
    tier,
    contract_type,
    monthly_mrr,
    current_arr,
    -- arr_at_risk is assigned ONLY to accounts in vulnerable risk categories
    CASE 
        WHEN risk_category = 'CRITICAL RISK' THEN current_arr
        WHEN risk_category = 'HIGH RISK' THEN ROUND(current_arr * 0.50, 2)
        ELSE 0.00
    END AS arr_at_risk,
    risk_category,
    latest_health_score,
    prev_health_score,
    health_score_change,
    latest_logins,
    baseline_logins,
    login_drop_pct,
    recent_support_tickets,
    avg_csat,
    escalated_tickets
FROM ScoredAccounts
ORDER BY 
    CASE risk_category 
        WHEN 'CRITICAL RISK' THEN 1 
        WHEN 'HIGH RISK' THEN 2 
        WHEN 'MODERATE RISK' THEN 3 
        ELSE 4 
    END ASC,
    arr_at_risk DESC;
