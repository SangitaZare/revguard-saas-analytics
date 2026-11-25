import os
import random
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set deterministic seed
random.seed(42)
np.random.seed(42)

def generate_saas_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    raw_dir = os.path.join(data_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "saas_analytics.db")

    print(f"Generating realistic B2B SaaS dataset in: {data_dir}")

    # 1. Accounts & Subscriptions
    # Let's create 1,200 B2B customers over a 24-month historical window (Nov 2024 to Nov 2026)
    num_accounts = 1200
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2026, 11, 1)
    days_range = (end_date - start_date).days

    industries = ["Fintech", "Healthcare Tech", "E-Commerce / Retail", "EdTech", "DevOps & Cloud", "Cybersecurity", "HR Tech"]
    tiers = {
        "Starter": {"mrr": 149, "seats": 5, "weight": 0.45},
        "Professional": {"mrr": 599, "seats": 20, "weight": 0.40},
        "Enterprise": {"mrr": 2499, "seats": 100, "weight": 0.15}
    }
    tier_choices = list(tiers.keys())
    tier_weights = [tiers[t]["weight"] for t in tier_choices]

    company_prefixes = ["Apex", "Cloud", "Nexus", "Pulse", "Sync", "Vanguard", "Data", "Hyper", "Strata", "Aero", "Omni", "Synthetix", "Quantum", "Peak", "BlueFin", "Elevate"]
    company_suffixes = ["Systems", "Labs", "Technologies", "Logistics", "Digital", "Analytics", "Networks", "Solutions", "Media", "Scale", "Capital", "Works"]

    accounts = []
    company_names = set()

    for i in range(1, num_accounts + 1):
        # Generate unique company name
        while True:
            name = f"{random.choice(company_prefixes)} {random.choice(company_suffixes)} {random.randint(10, 999)}"
            if name not in company_names:
                company_names.add(name)
                break
        
        industry = random.choice(industries)
        tier = np.random.choice(tier_choices, p=tier_weights)
        mrr = tiers[tier]["mrr"]
        contract_type = random.choice(["Monthly", "Annual", "Annual"]) # 66% annual
        
        # Signup date
        signup_offset = random.randint(0, days_range - 60) # at least 60 days active potential
        signup_date = start_date + timedelta(days=signup_offset)
        
        # Determine churn and active risk status
        # Enterprise churns less (10%), Starter churns more (35%)
        base_churn_prob = 0.35 if tier == "Starter" else (0.22 if tier == "Professional" else 0.08)
        is_churned = random.random() < base_churn_prob
        
        churn_date = None
        is_active_at_risk = False
        if is_churned:
            # Churn happens after 2 to 14 months of signup, before end_date
            max_lifespan_days = min((end_date - signup_date).days, 450)
            if max_lifespan_days > 45:
                lifespan_days = random.randint(45, max_lifespan_days)
                churn_date = signup_date + timedelta(days=lifespan_days)
                if churn_date > end_date:
                    churn_date = None
                    is_churned = False
            else:
                is_churned = False

        if not is_churned:
            # 18% of currently active accounts are in a decaying / at-risk state
            is_active_at_risk = random.random() < 0.18

        status = "Churned" if is_churned else "Active"
        
        accounts.append({
            "account_id": f"ACC-{i:05d}",
            "company_name": name,
            "industry": industry,
            "tier": tier,
            "base_mrr": mrr,
            "contract_type": contract_type,
            "signup_date": signup_date.strftime("%Y-%m-%d"),
            "churn_date": churn_date.strftime("%Y-%m-%d") if churn_date else None,
            "status": status,
            "is_active_at_risk": is_active_at_risk
        })

    df_accounts = pd.DataFrame(accounts)

    # 2. Monthly Usage & Health Metrics
    # For each account, generate monthly aggregated records for each active month
    usage_records = []
    for _, acc in df_accounts.iterrows():
        acc_signup = datetime.strptime(str(acc["signup_date"]), "%Y-%m-%d")
        acc_churn = datetime.strptime(str(acc["churn_date"]), "%Y-%m-%d") if pd.notna(acc["churn_date"]) else end_date
        
        # Loop through each calendar month active
        current_m = datetime(acc_signup.year, acc_signup.month, 1)
        prev_logins = random.randint(80, 500)
        
        while current_m <= acc_churn and current_m <= end_date:
            month_str = current_m.strftime("%Y-%m-01")
            
            # If approaching churn date within 60 days, usage drops sharply (leading indicator!)
            days_to_churn = (acc_churn - current_m).days if acc["status"] == "Churned" else 9999
            
            # Also for active at-risk accounts in their most recent 2-3 months:
            months_from_end = (end_date.year - current_m.year) * 12 + (end_date.month - current_m.month)
            is_recent_decay = acc.get("is_active_at_risk", False) and months_from_end <= 2

            if days_to_churn < 45 or (is_recent_decay and months_from_end <= 1):
                trend_factor = random.uniform(0.15, 0.45) # massive drop
                health_score = random.randint(18, 38)
            elif days_to_churn < 90 or is_recent_decay:
                trend_factor = random.uniform(0.45, 0.65) # moderate drop
                health_score = random.randint(39, 58)
            else:
                trend_factor = random.uniform(0.85, 1.25) # healthy variation
                health_score = random.randint(65, 98)
            
            seats_used = max(1, int(tiers[acc["tier"]]["seats"] * trend_factor * random.uniform(0.7, 1.0)))
            logins = max(5, int(prev_logins * trend_factor))
            api_calls = int(logins * random.uniform(40, 120))
            features_used = min(10, max(1, int(10 * (health_score / 100.0) * random.uniform(0.8, 1.0))))
            
            # MRR might have upsell / expansion
            expansion_factor = 1.0
            if health_score > 85 and random.random() < 0.15:
                expansion_factor = 1.2 # expansion MRR
            
            actual_mrr = round(acc["base_mrr"] * expansion_factor, 2)
            
            usage_records.append({
                "account_id": acc["account_id"],
                "activity_month": month_str,
                "monthly_mrr": actual_mrr,
                "active_seats": seats_used,
                "total_logins": logins,
                "api_calls": api_calls,
                "features_adopted": features_used,
                "account_health_score": health_score
            })
            
            prev_logins = logins
            # Next month
            if current_m.month == 12:
                current_m = datetime(current_m.year + 1, 1, 1)
            else:
                current_m = datetime(current_m.year, current_m.month + 1, 1)

    df_usage = pd.DataFrame(usage_records)

    # 3. Customer Support Tickets
    # Churning customers or frustrated customers generate high-urgency or negative sentiment tickets
    tickets = []
    ticket_id = 1
    categories = ["Billing Inquiry", "Feature Request", "Integration / API Bug", "Performance / Lag", "Onboarding Help"]
    
    for _, acc in df_accounts.iterrows():
        # High health accounts have 0-2 tickets/year, Low health / at-risk accounts have 3-7 tickets
        is_decaying = (acc["status"] == "Churned") or acc.get("is_active_at_risk", False)
        t_count = random.randint(3, 7) if is_decaying else random.randint(1, 3)
        acc_signup = datetime.strptime(str(acc["signup_date"]), "%Y-%m-%d")
        acc_churn = datetime.strptime(str(acc["churn_date"]), "%Y-%m-%d") if pd.notna(acc["churn_date"]) else end_date
        
        for _ in range(t_count):
            t_days = random.randint(10, max(20, (acc_churn - acc_signup).days))
            t_date = acc_signup + timedelta(days=t_days)
            if t_date > end_date:
                continue
            
            category = random.choice(categories)
            if is_decaying:
                csat = np.random.choice([1, 2, 3, 4], p=[0.40, 0.35, 0.20, 0.05])
                res_time_hours = round(random.uniform(24, 96), 1)
                escalated = random.choice([True, True, False])
            else:
                csat = np.random.choice([3, 4, 5], p=[0.15, 0.50, 0.35])
                res_time_hours = round(random.uniform(2, 24), 1)
                escalated = random.choice([False, False, False, True])
                
            tickets.append({
                "ticket_id": f"TCK-{ticket_id:06d}",
                "account_id": acc["account_id"],
                "created_at": t_date.strftime("%Y-%m-%d"),
                "category": category,
                "csat_score": int(csat),
                "resolution_hours": res_time_hours,
                "is_escalated": 1 if escalated else 0
            })
            ticket_id += 1

    df_tickets = pd.DataFrame(tickets)

    # Save to CSV
    accounts_csv = os.path.join(raw_dir, "accounts.csv")
    usage_csv = os.path.join(raw_dir, "monthly_usage.csv")
    tickets_csv = os.path.join(raw_dir, "support_tickets.csv")

    df_accounts.to_csv(accounts_csv, index=False)
    df_usage.to_csv(usage_csv, index=False)
    df_tickets.to_csv(tickets_csv, index=False)

    print(f"Saved CSVs: {len(df_accounts)} accounts, {len(df_usage)} usage rows, {len(df_tickets)} tickets.")

    # Save to SQLite Database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    df_accounts.to_sql("accounts", conn, index=False)
    df_usage.to_sql("monthly_usage", conn, index=False)
    df_tickets.to_sql("support_tickets", conn, index=False)
    
    # Create indexes for blazing-fast analytical queries
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_accounts_status ON accounts(status);")
    cur.execute("CREATE INDEX idx_usage_acc_month ON monthly_usage(account_id, activity_month);")
    cur.execute("CREATE INDEX idx_tickets_acc ON support_tickets(account_id);")
    conn.commit()
    conn.close()

    print(f"SQLite database created successfully with indexes at: {db_path}")

if __name__ == "__main__":
    generate_saas_data()
