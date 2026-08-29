import random
import csv
import os

def generate_revora_ml_dataset(n_samples=3500, output_path="data/revora_ml_training_data.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42) # Deterministic reproduction

    types = ["failed_payment", "partial_payment", "overdue_payment", "refund_mismatch"]
    type_weights = [40, 25, 25, 10]
    
    methods = ["upi", "card", "netbanking", "mandate"]
    method_weights = [55, 25, 12, 8]
    
    records = []

    for i in range(n_samples):
        opp_type = random.choices(types, weights=type_weights)[0]
        method = random.choices(methods, weights=method_weights)[0]
        
        if opp_type == "failed_payment":
            amount = round(random.choice([299, 499, 850, 999, 1499, 2499, 4999, 8200]), 2)
            age_days = random.randint(1, 3)
            base_prob = 0.82
        elif opp_type == "partial_payment":
            amount = round(random.choice([1500, 3000, 6000, 8500, 12500, 18000]), 2)
            age_days = random.randint(1, 10)
            base_prob = 0.76
        elif opp_type == "overdue_payment":
            amount = round(random.choice([5000, 12000, 18500, 25000, 45000]), 2)
            age_days = random.randint(3, 20)
            base_prob = 0.70
        else: # refund_mismatch
            amount = round(random.choice([1200, 3400, 5200, 9800]), 2)
            age_days = random.randint(1, 5)
            base_prob = 0.65

        customer_risk = random.choices(["LOW", "MEDIUM", "HIGH"], weights=[70, 22, 8])[0]
        past_successful_payments = random.choices([0, 1, 3, 6, 10, 15], weights=[15, 15, 30, 20, 12, 8])[0]
        past_late_payments = random.choices([0, 1, 2, 4], weights=[60, 25, 10, 5])[0]
        retry_count = random.choices([0, 1, 2, 3], weights=[70, 20, 7, 3])[0]

        # Domain physics mechanics
        prob = base_prob
        prob -= (min(age_days, 15) * 0.015) # Aging decay
        prob -= (retry_count * 0.10)        # Attempt decay

        if customer_risk == "LOW":
            prob += 0.05
        elif customer_risk == "HIGH":
            prob -= 0.25

        if past_successful_payments >= 5:
            prob += 0.06
        elif past_successful_payments == 0:
            prob -= 0.07

        if past_late_payments >= 2:
            prob -= 0.08

        final_prob = max(0.03, min(0.96, prob))
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

    print(f"[SUCCESS] Generated {len(records)} realistic training samples in {output_path}")

if __name__ == "__main__":
    generate_revora_ml_dataset()