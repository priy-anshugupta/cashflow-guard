import sys
from pathlib import Path
CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

import config
import pandas as pd
from data.loader import *
from data.joins import DataRepository
from extraction.vision import VisionExtractor
from extraction.messages import MessageClassifier
from engine.state_reconstructor import StateReconstructor
from engine.cashflow_simulator import CashflowSimulator
from engine.safe_amount import calculate_safe_amount
from engine.earliest_date import calculate_earliest_full_payment_date
from engine.plan_generator import PlanGenerator, rank_plans, CandidatePlan
from output.explanation import ExplanationGenerator
from engine.validator import OutputValidator

# Run on 25 sample requests
sample_dicts = load_sample_requests(config.SAMPLE_REQUESTS_CSV)
profiles = load_financial_profiles(config.PROFILES_CSV)
events = load_financial_events(config.EVENTS_CSV)
requests = load_requests(config.REQUESTS_CSV)
options = load_payment_options(config.PAYMENT_OPTIONS_CSV)
messages = load_messages(config.MESSAGES_CSV)
images = load_images(config.IMAGES_CSV)

sample_items = [
    RequestItem(
        request_id=d["request_id"], user_id=d["user_id"],
        request_date=d["request_date"], request_type=d["request_type"],
        requested_amount=float(d["requested_amount"]),
        desired_completion_date=d["desired_completion_date"],
        allows_partial_payment=bool(d["allows_partial_payment"]),
        request_text=d.get("request_text", "")
    ) for d in sample_dicts
]

repo = DataRepository(profiles, events, requests + sample_items, options, messages, images)
vision = VisionExtractor()
vision_map = vision.get_event_amount_map(config.IMAGES_CSV)
classifier = MessageClassifier()
message_effects = classifier.classify_all(messages)
reconstructor = StateReconstructor(vision_map, message_effects)

rows = []
for req in sample_items:
    ctx = repo.get_context(req.request_id)
    entries, _ = reconstructor.reconstruct(ctx.user, ctx.request, ctx.events)
    sim = CashflowSimulator(ctx.user.current_available_balance, ctx.user.minimum_balance_to_keep, ctx.request.request_date, entries)
    safe = calculate_safe_amount(sim, ctx.request.requested_amount)
    earliest = calculate_earliest_full_payment_date(sim, ctx.request.requested_amount, ctx.request.desired_completion_date)

    generator = PlanGenerator(
        user=ctx.user, request=ctx.request, base_entries=entries,
        payment_options=ctx.payment_options, safe_amount=safe, earliest_full_date=earliest
    )
    candidates = generator.generate_all_candidates()
    ranked = rank_plans(candidates)

    if ranked and ranked[0].completes_by_deadline:
        best_plan = ranked[0]
    else:
        best_plan = CandidatePlan(
            plan_id="not_rec", payment_method="not_recommended",
            affordability_status="not_affordable", payment_plan_str="none",
            completes_by_deadline=False, requires_spending_changes=False, is_safe=False
        )

    # Format fields
    status = best_plan.affordability_status
    method = best_plan.payment_method
    plan_str = best_plan.payment_plan_str
    
    if status == "affordable_now":
        earliest_out = req.request_date
    elif status == "not_affordable":
        earliest_out = ""
    else:
        earliest_out = earliest if earliest else ""

    if best_plan.spending_changes:
        changes_out = "|".join(sc.to_output_str() for sc in best_plan.spending_changes)
    else:
        changes_out = "none"

    exp_out = ExplanationGenerator.generate(
        user=ctx.user, request=ctx.request, plan=best_plan,
        safe_amount=safe, earliest_full_date=earliest_out
    )

    rows.append({
        "request_id": req.request_id,
        "amount_safe_to_pay": safe,
        "affordability_status": status,
        "recommended_payment_method": method,
        "payment_plan": plan_str,
        "earliest_date_for_full_payment": earliest_out,
        "spending_changes_needed": changes_out,
        "decision_explanation": exp_out
    })

out_df = pd.DataFrame(rows)
out_csv = "code/tests/sample_output_test.csv"
out_df.to_csv(out_csv, index=False)

# Validate
sample_req_df = pd.DataFrame(sample_dicts)
is_valid, errors = OutputValidator.validate_csv(out_csv, sample_req_df)
print(f"Sample pipeline valid: {is_valid}")
if errors:
    print("Errors found:")
    for e in errors:
        print("  ", e)
else:
    print("Zero errors found! 100% compliant!")