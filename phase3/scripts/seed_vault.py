# phase3/scripts/seed_vault.py
#
# Helper script to populate the Cloud Account Holder Vault database with
# 100 encrypted customer profiles and 25 sample fraud alerts for demo validation.

import sys
import os
import random
import time
import hashlib

# Ensure phase3 dir is in path for resolving modules
current_dir = os.path.dirname(os.path.abspath(__file__))
phase3_dir = os.path.abspath(os.path.join(current_dir, ".."))
if phase3_dir not in sys.path:
    sys.path.append(phase3_dir)

from services.cahv_service import cahv_service
from vault.db import vault_db
from vault.hash_utils import hash_account_id

def seed_database():
    print("==================================================")
    print("[VAULT] Seeding Cloud Account Holder Vault (CAHV)...")
    print(f"Database Path: {vault_db.db_path}")
    print("==================================================")
    
    # 1. Lists for generating random demographics
    first_names = [
        "Aarav", "Aditi", "Amit", "Ananya", "Arjun", "Deepika", "Ishaan", "Kavya", "Nikhil", "Pooja", 
        "Rahul", "Siddharth", "Neha", "Rohan", "Sneha", "Vikram", "Priya", "Karan", "Riya", "Aditya",
        "Aishwarya", "Dev", "Divya", "Gaurav", "Harini", "Jaidev", "Meera", "Pranav", "Rajesh", "Shruti"
    ]
    last_names = [
        "Sharma", "Verma", "Gupta", "Mehta", "Patel", "Reddy", "Nair", "Joshi", "Rao", "Kumar", 
        "Singh", "Das", "Choudhury", "Sen", "Mishra", "Pandey", "Iyer", "Banerjee", "Chatterjee", "Deshmukh",
        "Kulkarni", "Pillai", "Shetty", "Roy", "Kapoor", "Bahl", "Malhotra", "Goel", "Bansal", "Saxena"
    ]
    
    # Pre-calculated demo IDs to ensure we align with existing system accounts
    special_accounts = [
        {"account_id": 1247, "name": "Arjun Mehta", "phone": "+91 98765 43210", "pan": "BVPPM7812K", "email": "arjun.mehta@outlook.com"},
        {"account_id": 3891, "name": "Priya Sharma", "phone": "+91 91234 56789", "pan": "APOPS2941L", "email": "priya.sharma@gmail.com"},
        {"account_id": 5042, "name": "Vikram Singh", "phone": "+91 98888 77777", "pan": "AHYPT1982A", "email": "vikram.singh@yahoo.com"}
    ]
    
    # Clear existing data for a clean seed
    try:
        with vault_db._get_connection() as conn:
            conn.execute("DELETE FROM account_profiles")
            conn.execute("DELETE FROM fraud_alerts")
            conn.commit()
        print("[DB] Cleared existing vault database tables.")
    except Exception as e:
        print(f"[WARN] Cleared tables error (non-critical): {e}")

    # Seed Special Demo accounts
    seeded_count = 0
    seeded_hashes = []
    
    for sa in special_accounts:
        success = cahv_service.create_profile(
            account_id=sa["account_id"],
            name=sa["name"],
            phone=sa["phone"],
            pan=sa["pan"],
            email=sa["email"]
        )
        if success:
            seeded_count += 1
            seeded_hashes.append(hash_account_id(sa["account_id"]))
            
    print(f"[SEED] Seeded {len(special_accounts)} primary demo accounts.")

    # Seed another 97 random profiles to reach 100 total profiles
    random.seed(42)  # consistent generation
    for i in range(1000, 1097):
        acc_id = i
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        phone = f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}"
        pan_chars = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        pan_digits = "".join(random.choices("0123456789", k=4))
        pan_chk = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        pan = f"{pan_chars}{pan_digits}{pan_chk}"
        email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@gmail.com"
        
        success = cahv_service.create_profile(
            account_id=acc_id,
            name=name,
            phone=phone,
            pan=pan,
            email=email
        )
        if success:
            seeded_count += 1
            seeded_hashes.append(hash_account_id(acc_id))
            
    print(f"[SEED] Generated and seeded {seeded_count - len(special_accounts)} additional encrypted customer profiles.")

    # 2. Seed 25 fraud alerts of varying categories & sources
    alert_categories = [
        {"category": "Transaction Risk", "alert_type": "HIGH_VELOCITY", "notes": "Rapid successive transactions breaching safety baseline."},
        {"category": "Identity Risk", "alert_type": "MULE_ACCOUNT", "notes": "Profile attributes match known shell account patterns."},
        {"category": "Network Risk", "alert_type": "MULE_RELAY_NODE", "notes": "Hop analysis identifies account routing credit-relay flows."},
        {"category": "Crypto Risk", "alert_type": "CRYPTO_EXIT", "notes": "Exit detection to high-risk VDA exchange."}
    ]
    
    alert_sources = ["Fusion Engine", "Crypto Detector", "Manual Investigator", "External Registry"]
    
    alert_count = 0
    # Seed alerts specifically for demo account 1247 (so the timeline has nice initial charts)
    h1247 = hash_account_id(1247)
    demo_alerts_1247 = [
        {"risk_score": 62.0, "alert_type": "MULE_ACCOUNT", "category": "Identity Risk", "source": "Manual Investigator", "notes": "Reported during physical field agent audit.", "days_ago": 4},
        {"risk_score": 75.2, "alert_type": "CRYPTO_EXIT", "category": "Crypto Risk", "source": "Crypto Detector", "notes": "Transaction route destination matches WazirX alias.", "days_ago": 2},
        {"risk_score": 88.5, "alert_type": "FUSION_ENGINE_ALERT", "category": "Transaction Risk", "source": "Fusion Engine", "notes": "Automated risk threshold breach: score=88.5", "days_ago": 0}
    ]
    
    for da in demo_alerts_1247:
        alert_id = f"VALT-{int(time.time() - (da['days_ago'] * 86400))}-1247"
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (da['days_ago'] * 86400)))
        
        success = vault_db.save_alert(
            alert_id=alert_id,
            hashed_id=h1247,
            risk_score=da["risk_score"],
            alert_type=da["alert_type"],
            category=da["category"],
            source=da["source"],
            notes=da["notes"],
            created_at=created_at
        )
        if success:
            alert_count += 1
            
    # Seed alerts for random accounts
    for i in range(22):
        target_hash = random.choice(seeded_hashes)
        # Avoid seeding duplicate alerts on 1247 to keep it clean
        if target_hash == h1247:
            continue
            
        alert_choice = random.choice(alert_categories)
        source = random.choice(alert_sources)
        risk = round(random.uniform(40.0, 99.0), 1)
        days_ago = random.randint(1, 30)
        
        alert_id = f"VALT-{int(time.time() - (days_ago * 86400))}-{target_hash[:6]}"
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (days_ago * 86400)))
        
        success = vault_db.save_alert(
            alert_id=alert_id,
            hashed_id=target_hash,
            risk_score=risk,
            alert_type=alert_choice["alert_type"],
            category=alert_choice["category"],
            source=source,
            notes=alert_choice["notes"],
            created_at=created_at
        )
        if success:
            alert_count += 1

    print(f"[SEED] Generated and seeded {alert_count} secure threat alerts.")
    print("==================================================")
    print("[SUCCESS] Database seeding completed successfully!")
    print("==================================================")

if __name__ == "__main__":
    seed_database()
