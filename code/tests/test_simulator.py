"""
Unit test for Phase 3: Cashflow Simulator, Safe Amount, and Earliest Date.
Tests deterministic core simulation on all 25 sample requests.
"""

import sys
from pathlib import Path
CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

import config
from data.loader import (
    load_financial_profiles, load_financial_events,
    load_requests, load_sample_requests,
    load_payment_options, load_messages, load_images
)
from data.models import RequestItem
from data.joins import DataRepository
from extraction.vision import VisionExtractor
from extraction.messages import MessageClassifier
from engine.state_reconstructor import StateReconstructor
from engine.cashflow_simulator import CashflowSimulator
from engine.safe_amount import calculate_safe_amount
from engine.earliest_date import calculate_earliest_full_payment_date

def test_phase3_simulation():
    print("=== STARTING PHASE 3 SIMULATOR TEST ===")

    # Initialize components
    vision = VisionExtractor()
    vision_map = vision.get_event_amount_map(config.IMAGES_CSV)
    classifier = MessageClassifier()
    messages = load_messages(config.MESSAGES_CSV)
    message_effects = classifier.classify_all(messages)

    profiles = load_financial_profiles(config.PROFILES_CSV)
    events = load_financial_events(config.EVENTS_CSV)
    requests = load_requests(config.REQUESTS_CSV)
    options = load_payment_options(config.PAYMENT_OPTIONS_CSV)
    images = load_images(config.IMAGES_CSV)

    sample_dicts = load_sample_requests(config.SAMPLE_REQUESTS_CSV)
    sample_items = [
        RequestItem(
            request_id=d["request_id"],
            user_id=d["user_id"],
            request_date=d["request_date"],
            request_type=d["request_type"],
            requested_amount=float(d["requested_amount"]),
            desired_completion_date=d["desired_completion_date"],
            allows_partial_payment=bool(d["allows_partial_payment"]),
            request_text=d.get("request_text", "")
        )
        for d in sample_dicts
    ]

    all_requests = requests + sample_items
    repo = DataRepository(profiles, events, all_requests, options, messages, images)
    reconstructor = StateReconstructor(vision_map, message_effects)

    print(f"\nEvaluating {len(sample_dicts)} Sample Requests...")
    earliest_matches = 0
    safe_matches = 0

    for d in sample_dicts:
        req_id = d["request_id"]
        ctx = repo.get_context(req_id)
        entries, _ = reconstructor.reconstruct(ctx.user, ctx.request, ctx.events)

        simulator = CashflowSimulator(
            initial_balance=ctx.user.current_available_balance,
            minimum_balance_to_keep=ctx.user.minimum_balance_to_keep,
            request_date=ctx.request.request_date,
            base_entries=entries,
            forecast_days=90
        )

        safe_calc = calculate_safe_amount(simulator, ctx.request.requested_amount)
        earliest_calc = calculate_earliest_full_payment_date(simulator, ctx.request.requested_amount)

        gt_safe = float(d["amount_safe_to_pay"])
        gt_earliest = str(d.get("earliest_date_for_full_payment", "") or "")
        if gt_earliest == "nan":
            gt_earliest = ""

        safe_diff = abs(safe_calc - gt_safe)
        safe_ok = safe_diff < 1.0 or (gt_safe > 0 and safe_diff / gt_safe < 0.05)
        earliest_ok = (earliest_calc == gt_earliest)

        if safe_ok:
            safe_matches += 1
        if earliest_ok:
            earliest_matches += 1

        print(f"[{req_id}] Safe Calc: {safe_calc:12.2f} (GT: {gt_safe:12.2f}) | Earliest: {earliest_calc:10s} (GT: {gt_earliest:10s}) | Status: {d['affordability_status']}")

    print(f"\n--- Phase 3 Summary ---")
    print(f"Safe Amount Matches: {safe_matches} / {len(sample_dicts)}")
    print(f"Earliest Date Matches: {earliest_matches} / {len(sample_dicts)}")

def test_intraday_settlement_ordering():
    """
    Test that debits settle before credits on the same calendar day.
    Initial balance: 500, Min keep: 200.
    Day 2: Debit of 400, Credit of 600.
    Under net daily delta: net is +200, balance ends at 700, no breach.
    Under debit-first: intra-day trough is 500 - 400 = 100 (< 200 min keep).
    Simulator must record a breach and min_cushion = -100.
    """
    from engine.state_reconstructor import CashFlowEntry
    base_entries = [
        CashFlowEntry(
            date="2026-03-02",
            amount=400.0,
            direction="debit",
            category="rent",
            description="Monthly Rent",
            event_id="ev_debit_1"
        ),
        CashFlowEntry(
            date="2026-03-02",
            amount=600.0,
            direction="credit",
            category="salary",
            description="Monthly Salary",
            event_id="ev_credit_1"
        )
    ]
    sim = CashflowSimulator(
        initial_balance=500.0,
        minimum_balance_to_keep=200.0,
        request_date="2026-03-01",
        base_entries=base_entries,
        forecast_days=10
    )
    res = sim.simulate()
    assert not res.is_safe, "Debit-first ordering should have detected intra-day breach"
    assert "2026-03-02" in res.breach_dates, "Breach date must be 2026-03-02"
    assert abs(res.min_cushion - (-100.0)) < 1e-4, f"Min cushion should be -100.0, got {res.min_cushion}"
    assert abs(res.daily_balances["2026-03-02"] - 700.0) < 1e-4, "End-of-day balance should be 700.0 after credit"
    print("\n[PASS] test_intraday_settlement_ordering passed successfully!")

if __name__ == "__main__":
    test_phase3_simulation()
    test_intraday_settlement_ordering()
