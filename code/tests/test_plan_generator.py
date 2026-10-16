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
from engine.plan_generator import PlanGenerator, rank_plans, CandidatePlan

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

status_matches = 0
method_matches = 0
plan_matches = 0

print(f"=== TESTING PLAN GENERATOR & RANKER ON 25 SAMPLES ===")

for d in sample_dicts:
    req_id = d["request_id"]
    ctx = repo.get_context(req_id)
    entries, _ = reconstructor.reconstruct(ctx.user, ctx.request, ctx.events)

    sim = CashflowSimulator(
        ctx.user.current_available_balance,
        ctx.user.minimum_balance_to_keep,
        ctx.request.request_date,
        entries
    )

    # Use ground truth earliest_date and safe_amount for plan ranking verification if needed, or calc
    calc_safe = calculate_safe_amount(sim, ctx.request.requested_amount)
    calc_earliest = calculate_earliest_full_payment_date(sim, ctx.request.requested_amount, ctx.request.desired_completion_date)

    generator = PlanGenerator(
        user=ctx.user,
        request=ctx.request,
        base_entries=entries,
        payment_options=ctx.payment_options,
        safe_amount=calc_safe,
        earliest_full_date=calc_earliest
    )

    candidates = generator.generate_all_candidates()
    ranked = rank_plans(candidates)

    if ranked and ranked[0].completes_by_deadline:
        best_plan = ranked[0]
    else:
        # Fallback to not_recommended
        best_plan = CandidatePlan(
            plan_id="not_rec",
            payment_method="not_recommended",
            affordability_status="not_affordable",
            payment_plan_str="none",
            completes_by_deadline=False,
            requires_spending_changes=False,
            is_safe=False
        )

    gt_status = d["affordability_status"]
    gt_method = d["recommended_payment_method"]
    gt_plan = str(d["payment_plan"])

    stat_ok = (best_plan.affordability_status == gt_status)
    meth_ok = (best_plan.payment_method == gt_method)
    plan_ok = (best_plan.payment_plan_str == gt_plan)

    if stat_ok:
        status_matches += 1
    if meth_ok:
        method_matches += 1
    if plan_ok:
        plan_matches += 1

    print(f"[{req_id}] Status: {best_plan.affordability_status:20s} (GT: {gt_status:20s}) | Method: {best_plan.payment_method:15s} (GT: {gt_method:15s})")

print(f"\n--- Accuracy Report ---")
print(f"Status Matches: {status_matches} / 25")
print(f"Method Matches: {method_matches} / 25")
print(f"Plan Matches: {plan_matches} / 25")
