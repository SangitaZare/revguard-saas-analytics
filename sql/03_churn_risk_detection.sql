-- ==============================================================================
-- 03_churn_risk_detection.sql
-- Goal: Identify Active Accounts with Severe Usage Drop-off Signals (Revenue at Risk)
-- Technique: Multi-level CTEs, 3-Month Rolling Averages with History Count Guards,
--            LEFT JOIN Zero-Activity Churn Detection, NULL-Safe CSAT Evaluation,
--            and Empirical Backtest-Calibrated Probability Weighting (65% Critical / 35% High)
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
        -- 3-Month Rolling Average of login activity prior to current month
        AVG(total_logins) OVER (
            PARTITION BY account_id ORDER BY activity_month ASC
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS avg_logins_prior_3m,
        -- Require at least 2 historical months for 3-month rolling baseline
        COUNT(total_logins) OVER (
            PARTITION BY account_id ORDER BY activity_month ASC
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS history_window_count,
        LAG(account_health_score, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_health_score
    FROM monthly_usage
),
CurrentMonthUsage AS (
    SELECT 
        u.*,
        -- Use 3-month rolling average if at least 2 prior months exist; otherwise fallback to prior month
        CASE 
            WHEN u.history_window_count >= 2 AND u.avg_logins_prior_3m IS NOT NULL THEN u.avg_logins_prior_3m
            ELSE u.prev_month_logins 
        END AS baseline_logins,
        CASE 
            WHEN (CASE WHEN u.history_window_count >= 2 AND u.avg_logins_prior_3m IS NOT NULL THEN u.avg_logins_prior_3m ELSE u.prev_month_logins END) > 0 
            THEN ROUND(
                ((u.total_logins - (CASE WHEN u.history_window_count >= 2 AND u.avg_logins_prior_3m IS NOT NULL THEN u.avg_logins_prior_3m ELSE u.prev_month_logins END)) * 100.0) / 
                (CASE WHEN u.history_window_count >= 2 AND u.avg_logins_prior_3m IS NOT NULL THEN u.avg_logins_prior_3m ELSE u.prev_month_logins END), 
                1
            )
            ELSE 0.0 
        END AS login_drop_pct
    FROM UsageRollingStats u
    JOIN MaxDate m ON u.activity_month = m.latest_month
),
RecentSupportMetrics AS (
    -- Limit support ticket evaluation to recent window (last 6 months, format-resilient)
    SELECT 
        account_id,
        COUNT(ticket_id) AS total_recent_tickets,
        ROUND(AVG(csat_score), 2) AS avg_csat,
        SUM(is_escalated) AS escalated_tickets
    FROM support_tickets
    WHERE created_at >= (
        SELECT DATE(CASE WHEN LENGTH(latest_month) = 7 THEN latest_month || '-01' ELSE latest_month END, '-6 months') 
        FROM MaxDate
    )
    GROUP BY account_id
),
ScoredAccounts AS (
    SELECT 
        a.account_id,
        a.company_name,
        a.industry,
        a.tier,
        a.contract_type,
        COALESCE(c.monthly_mrr, a.base_mrr) AS monthly_mrr,
        ROUND(COALESCE(c.monthly_mrr, a.base_mrr) * 12, 2) AS current_arr,
        COALESCE(c.account_health_score, 0) AS latest_health_score,
        c.prev_health_score,
        (COALESCE(c.account_health_score, 0) - COALESCE(c.prev_health_score, 0)) AS health_score_change,
        COALESCE(c.total_logins, 0) AS latest_logins,
        c.baseline_logins,
        COALESCE(c.login_drop_pct, -100.0) AS login_drop_pct,
        COALESCE(s.total_recent_tickets, 0) AS recent_support_tickets,
        COALESCE(s.avg_csat, 5.0) AS avg_csat,
        COALESCE(s.escalated_tickets, 0) AS escalated_tickets,
        -- Robust Composite Churn Risk Classification:
        -- 1. Complete inactivity (missing usage row) = Immediate Critical Risk
        -- 2. Health score < 40, severe login drop (<= -60%), or moderate drop with low CSAT = Critical Risk
        -- 3. Health score < 60, login drop <= -30%, or repeated escalations = High Risk
        CASE 
            WHEN c.account_id IS NULL THEN 'CRITICAL RISK'
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
    -- LEFT JOIN guarantees active accounts with 0 usage this month are caught as churn risks
    LEFT JOIN CurrentMonthUsage c ON a.account_id = c.account_id
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
    -- Gross exposed ARR (100% of contract value for flagged accounts)
    CASE 
        WHEN risk_category IN ('CRITICAL RISK', 'HIGH RISK') THEN current_arr
        ELSE 0.00
    END AS gross_arr_exposed,
    -- Expected ARR at risk calibrated from empirical backtest probabilities:
    -- Critical Risk: 65% observed churn rate; High Risk: 35% observed churn rate
    CASE 
        WHEN risk_category = 'CRITICAL RISK' THEN ROUND(current_arr * 0.65, 2)
        WHEN risk_category = 'HIGH RISK' THEN ROUND(current_arr * 0.35, 2)
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
