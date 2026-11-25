import os
import sqlite3
import pandas as pd
import numpy as np

def run_churn_early_warning_backtest():
    """
    Backtests the rule-based early warning churn detection heuristic against
    historical accounts to measure Precision, Recall, Specificity, and F1-Score.
    
    Evaluates:
    Did accounts that experienced severe login drop-offs and health score degradation
    within 60 days of renewal actually churn, vs accounts that remained active and healthy?
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "saas_analytics.db")

    conn = sqlite3.connect(db_path)
    
    # Query all historical accounts with their ultimate status and their penultimate usage telemetry
    query = """
    WITH AccountLifecycle AS (
        SELECT 
            account_id,
            status,
            signup_date,
            churn_date
        FROM accounts
    ),
    PenultimateTelemetry AS (
        SELECT 
            account_id,
            activity_month,
            account_health_score,
            total_logins,
            LAG(total_logins, 1) OVER (PARTITION BY account_id ORDER BY activity_month ASC) AS prev_logins,
            ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY activity_month DESC) AS rn_rev
        FROM monthly_usage
    ),
    SupportHistory AS (
        SELECT 
            account_id,
            AVG(csat_score) AS avg_csat
        FROM support_tickets
        GROUP BY account_id
    )
    SELECT 
        a.account_id,
        a.status,
        p.account_health_score,
        p.total_logins,
        p.prev_logins,
        CASE 
            WHEN p.prev_logins > 0 THEN ((p.total_logins - p.prev_logins) * 100.0) / p.prev_logins
            ELSE 0.0 
        END AS login_drop_pct,
        COALESCE(s.avg_csat, 4.0) AS avg_csat
    FROM AccountLifecycle a
    JOIN PenultimateTelemetry p ON a.account_id = p.account_id AND p.rn_rev = 2 -- Look back 1-2 months prior to end of tenure
    LEFT JOIN SupportHistory s ON a.account_id = s.account_id;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Ground truth: 1 if Churned, 0 if Active
    y_true = (df["status"] == "Churned").astype(int)

    # Heuristic Flag: Critical / High Risk prediction
    # Predict Churn (1) if health score < 50 OR (login drop <= -40% AND avg_csat <= 3.0)
    y_pred = (
        (df["account_health_score"] < 50) | 
        ((df["login_drop_pct"] <= -40.0) & (df["avg_csat"] <= 3.0))
    ).astype(int)

    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())

    precision = round((tp / (tp + fp)) * 100, 1) if (tp + fp) > 0 else 0.0
    recall = round((tp / (tp + fn)) * 100, 1) if (tp + fn) > 0 else 0.0
    specificity = round((tn / (tn + fp)) * 100, 1) if (tn + fp) > 0 else 0.0
    f1 = round((2 * precision * recall) / (precision + recall), 1) if (precision + recall) > 0 else 0.0
    accuracy = round(((tp + tn) / len(df)) * 100, 1)

    results = {
        "total_evaluated_accounts": len(df),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "accuracy_pct": accuracy,
        "precision_pct": precision,
        "recall_pct": recall,
        "specificity_pct": specificity,
        "f1_score": f1
    }
    return results

if __name__ == "__main__":
    res = run_churn_early_warning_backtest()
    print("Historical Churn Signal Backtest Validation:")
    for k, v in res.items():
        print(f"  {k}: {v}")
