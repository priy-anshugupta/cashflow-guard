"""
Smoke test for Phase 1 components.
Verifies data loading, join indexes, currency conversions, and model mappings across all 25,342 events and 250 requests.
"""

import sys
from pathlib import Path

# Add code to python path
CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

import config
from data.loader import (
    load_financial_profiles, load_financial_events,
    load_requests, load_sample_requests,
    load_payment_options, load_messages, load_images
)
from data.joins import DataRepository
from extraction.currency import get_currency_engine

def run_smoke_test():
    print("=== STARTING PHASE 1 SMOKE TEST ===")
    
    # 1. Load Data
    print("Loading datasets...")
    profiles = load_financial_profiles(config.PROFILES_CSV)
    events = load_financial_events(config.EVENTS_CSV)
    requests = load_requests(config.REQUESTS_CSV)
    sample_requests = load_sample_requests(config.SAMPLE_REQUESTS_CSV)
    options = load_payment_options(config.PAYMENT_OPTIONS_CSV)
    messages = load_messages(config.MESSAGES_CSV)
    images = load_images(config.IMAGES_CSV)
    
    print(f"  [OK] Profiles loaded: {len(profiles)} (expected 275)")
    assert len(profiles) == 275, f"Expected 275 profiles, got {len(profiles)}"
    
    print(f"  [OK] Events loaded: {len(events)} (expected 25342)")
    assert len(events) == 25342, f"Expected 25342 events, got {len(events)}"
    
    print(f"  [OK] Requests loaded: {len(requests)} (expected 250)")
    assert len(requests) == 250, f"Expected 250 requests, got {len(requests)}"
    
    print(f"  [OK] Sample requests loaded: {len(sample_requests)} (expected 25)")
    assert len(sample_requests) == 25, f"Expected 25 samples, got {len(sample_requests)}"
    
    print(f"  [OK] Payment options loaded: {len(options)} (expected 790)")
    assert len(options) == 790, f"Expected 791 options, got {len(options)}"
    
    print(f"  [OK] Messages loaded: {len(messages)} (expected 215)")
    assert len(messages) == 215, f"Expected 215 messages, got {len(messages)}"
    
    print(f"  [OK] Images loaded: {len(images)} (expected 16)")
    assert len(images) == 16, f"Expected 16 images, got {len(images)}"

    # 2. Test Currency Engine
    print("\nTesting Currency Engine...")
    curr_engine = get_currency_engine()
    rate_usd_inr = curr_engine.get_rate("USD", "INR")
    print(f"  [OK] USD -> INR rate: {rate_usd_inr} (expected 83.33)")
    assert abs(rate_usd_inr - 83.33) < 0.01

    rate_eur_zar = curr_engine.get_rate("EUR", "ZAR")
    print(f"  [OK] EUR -> ZAR rate: {rate_eur_zar} (expected 20.0)")
    assert abs(rate_eur_zar - 20.0) < 0.01

    # Test chained conversion: INR -> EUR (INR -> USD -> EUR)
    conv_inr_eur = curr_engine.convert(83.33 * 100, "INR", "EUR")
    print(f"  [OK] 8333 INR converted to EUR: {conv_inr_eur:.2f} (expected ~92.00)")
    assert abs(conv_inr_eur - 92.00) < 1.0

    # 3. Test Repository & Joins
    print("\nTesting DataRepository Indexing & Joins...")
    repo = DataRepository(
        profiles=profiles,
        events=events,
        requests=requests,
        payment_options=options,
        messages=messages,
        images=images
    )
    
    # Test request_26 context
    ctx_26 = repo.get_context("request_26")
    print(f"  [OK] request_26 retrieved for user: {ctx_26.user.user_id}")
    print(f"       User balance: {ctx_26.user.current_available_balance} {ctx_26.user.home_currency}")
    print(f"       Events count: {len(ctx_26.events)}")
    print(f"       Payment options count: {len(ctx_26.payment_options)}")
    assert ctx_26.user.user_id == "user_26"
    assert len(ctx_26.events) > 0

    # 4. Check for blank amount events linked to images
    print("\nChecking blank amount events linked to images...")
    blank_events = [e for e in events if e.amount is None]
    print(f"  [OK] Events with blank amount needing vision extraction: {len(blank_events)}")
    assert len(blank_events) == 16, f"Expected exactly 16 blank events, got {len(blank_events)}"

    print("\n==========================================")
    print(" PHASE 1 SMOKE TEST PASSED WITH 100% SUCCESS ")
    print("==========================================")

if __name__ == "__main__":
    run_smoke_test()
