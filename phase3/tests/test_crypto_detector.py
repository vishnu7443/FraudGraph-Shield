import os
import shutil
import pytest
from phase3.services.crypto_detector import detector
from phase3.storage.db import CryptoAlertsDB
from phase3.models.crypto_alert import CryptoAlert
from phase3.services.str_generator import STRGenerator
from phase3.services.travel_rule import TravelRuleLogger

def test_alias_detection():
    # 1. Exact match
    res = detector.detect_crypto("WAZIRX")
    assert res["is_crypto"] is True
    assert res["exchange"] == "WAZIRX"
    assert res["confidence"] == 1.0

    # 2. Substring/Alias match
    res2 = detector.detect_crypto("WazirX India Tech Pvt Ltd")
    assert res2["is_crypto"] is True
    assert res2["exchange"] == "WAZIRX"
    assert res2["confidence"] == 0.95

    # 3. Non-crypto destination
    res3 = detector.detect_crypto("Amazon Shopping")
    assert res3["is_crypto"] is False
    assert res3["exchange"] is None

def test_database_persistence():
    test_db_path = "phase3/storage/test_crypto_alerts.db"
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass
        
    db = CryptoAlertsDB(db_path=test_db_path)
    
    alert = CryptoAlert(
        alert_id="ALT-TEST-123",
        txn_id="TXN-TEST-123",
        account_id=1247,
        exchange="WAZIRX",
        amount=50000.0,
        risk_score=85.0,
        severity="HIGH",
        hold_reason="Test reason",
        timestamp="2026-06-14T08:00:00Z",
        status="OPEN"
    )
    
    assert db.save_alert(alert) is True
    
    # Retrieve all
    all_alerts = db.get_all_alerts()
    assert len(all_alerts) == 1
    assert all_alerts[0].alert_id == "ALT-TEST-123"
    
    # Retrieve detail
    retrieved = db.get_alert_by_id("ALT-TEST-123")
    assert retrieved is not None
    assert retrieved.txn_id == "TXN-TEST-123"
    
    # Clean up test DB
    try:
        os.remove(test_db_path)
    except OSError:
        pass

def test_str_and_travel_rule_generation():
    test_reports_dir = "phase3/reports/test_reports"
    test_logs_dir = "phase3/travel_rule_logs/test_logs"
    
    if os.path.exists(test_reports_dir):
        shutil.rmtree(test_reports_dir)
    if os.path.exists(test_logs_dir):
        shutil.rmtree(test_logs_dir)
        
    str_gen = STRGenerator(reports_dir=test_reports_dir)
    tr_log = TravelRuleLogger(logs_dir=test_logs_dir)
    
    str_file = str_gen.generate_vda_str(
        txn_id="TXN-999",
        account_id=999,
        exchange="COINDCX",
        amount=15000.0,
        score=76.2,
        hold_reason="Funds exit to CoinDCX"
    )
    
    tr_file = tr_log.log_travel_rule(
        txn_id="TXN-999",
        account_id=999,
        exchange="COINDCX",
        amount=15000.0
    )
    
    assert os.path.exists(str_file) is True
    assert os.path.exists(tr_file) is True
    
    # Clean up test dirs
    shutil.rmtree(test_reports_dir)
    shutil.rmtree(test_logs_dir)
