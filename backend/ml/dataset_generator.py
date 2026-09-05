import random
import csv
import os

def generate_recoveriq_ml_dataset(n_samples=4000, output_path="data/recoveriq_ml_training_data.csv"):
    """
    Generates realistic historical ground-truth recovery outcomes across all 4 opportunity types.
    Each opportunity_type has distinct empirical domain recovery mechanics:
    - failed_payment: High recovery for transient network timeouts (~85%), low for bad card data.
    - partial_payment: High recovery (~78%) because customer already committed an initial deposit.
    - overdue_payment: Moderate-high (~70%) for fresh invoices, decaying with aging (-1.5%/day).
    - refund_mismatch: Moderate (~62%) recoverable via automated pre-auth capture.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42) # Reproducible ground truth

    types = ["failed_payment", "partial_payment", "overdue_payment", "refund_mismatch"]
    type_weights = [40, 25, 25, 10]
    
    methods = ["upi", "card", "netbanking", "mandate"]
    method_weights = [55, 25, 12, 8]
    
    records = []

    for _ in range(n_samples):
        opp_type = random.choices(types, weights=type_weights)[0]
        method = random.choices(methods, weights=method_weights)[0]
        
        # 1. Opportunity-specific amounts, aging, and baseline physics
        if opp_type == "failed_payment":
            amount = round(random.choice([299, 499, 850, 999, 1499, 2499, 4999, 8200]), 2)
            age_days = random.randint(1, 3)
            base_prob = 0.84 # Timeouts recover very well on delayed switch retry
        elif opp_type == "partial_payment":
            amount = round(random.choice([1500, 3000, 6000, 8500, 12500, 18000]), 2)
            age_days = random.randint(1, 10)
            base_prob = 0.78 # Advance already paid indicates high purchase commitment
        elif opp_type == "overdue_payment":
            amount = round(random.choice([5000, 12000, 18500, 25000, 45000]), 2)
            age_days = random.randint(3, 25)
            base_prob = 0.70 # B2B invoices recover well with 1-click reminders
        else: # refund_mismatch
            amount = round(random.choice([1200, 3400, 5200, 9800]), 2)
            age_days = random.randint(1, 5)
            base_prob = 0.62 # Uncaptured auth charges recoverable before 5-day TTL

        customer_risk = random.choices(["LOW", "MEDIUM", "HIGH"], weights=[70, 22, 8])[0]
        past_successful_payments = random.choices([0, 1, 3, 6, 10, 15], weights=[15, 15, 30, 20, 12, 8])[0]
        past_late_payments = random.choices([0, 1, 2, 4], weights=[60, 25, 10, 5])[0]
        retry_count = random.choices([0, 1, 2, 3], weights=[70, 20, 7, 3])[0]

        # 2. Mathematical modifiers reflecting realistic payment gateway behavior
        prob = base_prob
        prob -= (min(age_days, 20) * 0.015)  # Aging penalty: -1.5% per day overdue
        prob -= (retry_count * 0.11)         # Attempt fatigue: -11% per previous attempt

        # Payment method modifier (UPI 1-click links recover faster than Netbanking)
        if method == "upi":
            prob += 0.04
        elif method == "netbanking":
            prob -= 0.03

        # Customer history signals
        if customer_risk == "LOW":
            prob += 0.05
        elif customer_risk == "HIGH":
            prob -= 0.28 # High risk accounts have significantly lower recovery

        if past_successful_payments >= 5:
            prob += 0.06
        elif past_successful_payments == 0:
            prob -= 0.08

        if past_late_payments >= 2:
            prob -= 0.07

        # Clamp between 3% and 96%
        final_prob = max(0.03, min(0.96, prob))
        
        # Binary outcome label: 1 = Recovered, 0 = Not Recovered
        recovered_label = 1 if random.random() < final_prob else 0

        records.append({
            "opportunity_type": opp_type,
            "amount": amount,
            "payment_method": method,
            "age_days": age_days,
            "customer_risk": customer_risk,
            "past_successful_payments": past_successful_payments,
            "past_late_payments": past_late_payments,
            "retry_count": retry_count,
            "recovered": recovered_label
        })

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    print(f"[SUCCESS] Generated {len(records)} realistic training samples across 4 opportunity types in {output_path}")

if __name__ == "__main__":
    generate_recoveriq_ml_dataset()