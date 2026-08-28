import random
import csv
import os
from datetime import datetime, timedelta, timezone

def generate_ml_training_data(n_samples=3000, output_path="data/ml_historical_transactions.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    random.seed(42) # Reproducible ground truth
    
    failure_types = [
        "INSUFFICIENT_FUNDS",
        "GATEWAY_TIMEOUT",
        "AUTHENTICATION_FAILED",
        "BANK_DOWN",
        "MANDATE_EXPIRED",
        "CARD_DECLINED"
    ]
    failure_weights = [35, 25, 18, 12, 7, 3] # Realistic failure occurrence weights
    
    methods = ["upi", "card", "netbanking", "mandate"]
    method_weights = [55, 25, 12, 8]
    
    actions = ["retry_now", "retry_later", "recovery_link"]
    
    records = []
    
    for i in range(n_samples):
        failure_code = random.choices(failure_types, weights=failure_weights)[0]
        method = random.choices(methods, weights=method_weights)[0]
        action = random.choice(actions)
        
        # Realistic amount distribution
        if method == "upi":
            amount = round(random.choice([299, 499, 850, 999, 1499, 2499, 4999, 7500]), 2)
        elif method == "mandate":
            amount = round(random.choice([499, 999, 1499, 2999, 4999, 14500]), 2)
        elif method == "netbanking":
            amount = round(random.choice([2500, 5000, 8200, 15000, 35000, 75000]), 2)
        else: # Card
            amount = round(random.choice([999, 1999, 3499, 5999, 12000, 25000, 45000]), 2)
            
        attempt_number = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
        hour_of_day = random.randint(0, 23)
        past_successful_payments = random.choices([0, 1, 3, 5, 8, 12, 20], weights=[20, 15, 25, 20, 10, 7, 3])[0]
        
        # Ground Truth Probability Formula (Realistic domain mechanics)
        base_prob = 0.50
        
        if failure_code == "GATEWAY_TIMEOUT":
            if action == "retry_later":
                base_prob = 0.85 # Timeout clears after buffer window
            elif action == "retry_now":
                base_prob = 0.55
            else:
                base_prob = 0.60
                
        elif failure_code == "AUTHENTICATION_FAILED": # 3DS OTP drop
            if action == "recovery_link":
                base_prob = 0.74 # 1-click WhatsApp/SMS link gets user back to checkout
            elif action == "retry_later":
                base_prob = 0.35
            else:
                base_prob = 0.18 # Customer dropped OTP; instant automated retry fails again
                
        elif failure_code == "BANK_DOWN":
            if action == "retry_later":
                base_prob = 0.52 # Switch maintenance resolves
            elif action == "recovery_link":
                base_prob = 0.45
            else:
                base_prob = 0.05 # Bank switch still down
                
        elif failure_code == "MANDATE_EXPIRED":
            if action == "retry_later":
                base_prob = 0.78 # Next banking clearing cycle
            else:
                base_prob = 0.30
                
        elif failure_code == "INSUFFICIENT_FUNDS":
            if action == "recovery_link":
                base_prob = 0.38 # Customer can choose credit card / pay later
            elif action == "retry_later":
                base_prob = 0.14
            else:
                base_prob = 0.03 # Account balance remains empty immediately
                
        elif failure_code == "CARD_DECLINED":
            if action == "recovery_link":
                base_prob = 0.42 # Lets user provide another card
            else:
                base_prob = 0.08 # Re-swiping rejected card fails
                
        # Modifiers
        # 1. Payment method modifier
        if method == "upi" and action in ["retry_later", "recovery_link"]:
            base_prob += 0.05
        elif method == "netbanking":
            base_prob -= 0.05
            
        # 2. Attempt decay penalty
        base_prob -= ((attempt_number - 1) * 0.12)
        
        # 3. Customer trust bonus
        if past_successful_payments >= 5:
            base_prob += 0.06
        elif past_successful_payments == 0:
            base_prob -= 0.08
            
        # 4. Night time banking maintenance window (01:00 to 04:00 AM)
        if 1 <= hour_of_day <= 4 and action == "retry_now":
            base_prob -= 0.15
            
        # Clamp probability
        final_prob = max(0.02, min(0.96, base_prob))
        
        # Assign Binary Label: 1 = Recovered, 0 = Not Recovered
        outcome = 1 if random.random() < final_prob else 0
        
        records.append({
            "amount": amount,
            "method": method,
            "failure_code": failure_code,
            "attempt_number": attempt_number,
            "hour_of_day": hour_of_day,
            "past_successful_payments": past_successful_payments,
            "action_type": action,
            "recovered": outcome
        })
        
    # Write CSV
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        
    print(f"[SUCCESS] Generated {len(records)} historical training records in {output_path}")

if __name__ == "__main__":
    generate_ml_training_data(3000)