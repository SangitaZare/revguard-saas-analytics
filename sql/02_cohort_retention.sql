-- ==============================================================================
-- 02_cohort_retention.sql
-- Goal: Calculate triangular Month-over-Month Retention Cohorts
-- Technique: Multi-level CTEs, DATE functions, Cross-Cohort Indexing, Pivot format
-- ==============================================================================

WITH CustomerCohorts AS (
    -- Step 1: Assign each customer to their original signup cohort month
    SELECT 
        account_id,
        SUBSTR(signup_date, 1, 7) || '-01' AS cohort_month
    FROM accounts
),
CohortActivity AS (
    -- Step 2: Track active months for each cohort member
    SELECT 
        c.cohort_month,
        u.activity_month,
        -- Calculate index month difference: (year_diff * 12 + month_diff)
        (CAST(SUBSTR(u.activity_month, 1, 4) AS INT) - CAST(SUBSTR(c.cohort_month, 1, 4) AS INT)) * 12 +
        (CAST(SUBSTR(u.activity_month, 6, 2) AS INT) - CAST(SUBSTR(c.cohort_month, 6, 2) AS INT)) AS month_index,
        COUNT(DISTINCT u.account_id) AS retained_customers,
        ROUND(SUM(u.monthly_mrr), 2) AS cohort_mrr
    FROM CustomerCohorts c
    JOIN monthly_usage u ON c.account_id = u.account_id
    GROUP BY c.cohort_month, u.activity_month
),
CohortSizes AS (
    -- Step 3: Get the initial cohort size (month 0)
    SELECT 
        cohort_month,
        retained_customers AS cohort_size,
        cohort_mrr AS initial_mrr
    FROM CohortActivity
    WHERE month_index = 0
)
SELECT 
    ca.cohort_month,
    cs.cohort_size,
    ca.month_index,
    ca.retained_customers,
    ROUND((ca.retained_customers * 100.0) / cs.cohort_size, 1) AS retention_rate_pct,
    ca.cohort_mrr,
    ROUND((ca.cohort_mrr * 100.0) / cs.initial_mrr, 1) AS revenue_retention_pct
FROM CohortActivity ca
JOIN CohortSizes cs ON ca.cohort_month = cs.cohort_month
WHERE ca.month_index >= 0 AND ca.month_index <= 12
ORDER BY ca.cohort_month ASC, ca.month_index ASC;
