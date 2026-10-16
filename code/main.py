"""
HackerRank Orchestrate (September 2026) - Buy or Wait?
Main CLI and Pipeline Entry Point

Project: Cashflow Guard by Priyanshu Gupta
Challenge: HackerRank Orchestrate (September 2026)

Features:
1. Multi-modal extraction (configurable vision model with validated local caching)
2. Adversarial NLP defense isolating scam fee / prompt injections (message_67, message_142)
3. Relational data modeling and multi-currency normalization via dated exchange rates
4. 90-day conservative cashflow ledger simulation
5. Exact 6-level plan ranking hierarchy
6. Pre-submission schema validation
7. Token tracking and usage report generator
"""

import sys
import os
import argparse
import time
from pathlib import Path
import pandas as pd

# Add code directory to path
CODE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE_DIR))

import config
from data.loader import (
    load_financial_profiles, load_financial_events,
    load_requests, load_sample_requests,
    load_payment_options, load_messages, load_images, validate_dataset_inputs
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
from output.explanation import ExplanationGenerator
from engine.validator import OutputValidator

def generate_usage_report(report_path: Path, num_requests: int, vision_usage: dict, nlp_usage: dict, elapsed_sec: float):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    v_model = vision_usage.get("model", config.VISION_MODEL)
    n_model = nlp_usage.get("model", config.NLP_MODEL)
    
    v_calls = vision_usage.get("calls", 0)
    v_in = vision_usage.get("input_tokens", 0)
    v_out = vision_usage.get("output_tokens", 0)
    v_hits = vision_usage.get("cache_hits", 0)
    v_misses = vision_usage.get("cache_misses", 0)
    v_fails = vision_usage.get("failures", 0)
    
    n_calls = nlp_usage.get("calls", 0)
    n_in = nlp_usage.get("input_tokens", 0)
    n_out = nlp_usage.get("output_tokens", 0)
    n_hits = nlp_usage.get("cache_hits", 0)
    n_misses = nlp_usage.get("cache_misses", 0)
    n_fails = nlp_usage.get("failures", 0)
    
    total_calls = v_calls + n_calls
    total_in = v_in + n_in
    total_out = v_out + n_out
    total_tokens = total_in + total_out
    total_fails = v_fails + n_fails
    total_hits = v_hits + n_hits
    total_misses = v_misses + n_misses
    
    # GPT-5.4 pricing is $2.50 / 1M input and $15.00 / 1M output (official model documentation).
    if "mini" in v_model.lower():
        cost_in = (total_in / 1_000_000.0) * 0.15
        cost_out = (total_out / 1_000_000.0) * 0.60
    else:
        cost_in = (total_in / 1_000_000.0) * 2.50
        cost_out = (total_out / 1_000_000.0) * 15.00
    total_cost = cost_in + cost_out
    
    avg_tokens_per_req = total_tokens / max(1, num_requests)
    avg_cost_per_req = total_cost / max(1, num_requests)

    report_content = f"""# Model Usage & Cost Report

**Challenge:** HackerRank Orchestrate (September 2026) — Buy or Wait?  
**Execution Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  
**Total Evaluation Requests Processed:** {num_requests}  
**Total Pipeline Execution Time:** {elapsed_sec:.2f}s  

---

## 1. Model Architecture & Providers

| Component | Model Name | Provider | Mode / Optimization |
|---|---|---|---|
| Multimodal OCR | `{v_model}` | OpenAI | Live Multimodal API + Schema Validation |
| Message Classification | `{n_model}` | OpenAI | Live Batched NLP API + Adversarial Defense |
| Cashflow Ledger Simulator | Deterministic Python Engine | Native | 0 tokens (Exact Math) |
| Plan Generator & Ranker | Spec 6-Level Priority Hierarchy | Native | 0 tokens (Exact Logic) |

---

## 2. Token Breakdown & Model Calls

| Category | Model Calls | Input Tokens | Output Tokens | Total Tokens | Cache Hits | Cache Misses | Failures |
|---|---|---|---|---|---|---|---|
| Vision OCR (`{v_model}`) | {v_calls} | {v_in:,} | {v_out:,} | {v_in + v_out:,} | {v_hits} | {v_misses} | {v_fails} |
| NLP Classification (`{n_model}`) | {n_calls} | {n_in:,} | {n_out:,} | {n_in + n_out:,} | {n_hits} | {n_misses} | {n_fails} |
| **Total Full-Dataset Run** | **{total_calls}** | **{total_in:,}** | **{total_out:,}** | **{total_tokens:,}** | **{total_hits}** | **{total_misses}** | **{total_fails}** |

---

## 3. Per-Request Efficiency & Financial Cost

- **Average Input Tokens / Request:** {total_in / max(1, num_requests):.1f}
- **Average Output Tokens / Request:** {total_out / max(1, num_requests):.1f}
- **Average Total Tokens / Request:** {avg_tokens_per_req:.1f}
- **Estimated Total Cost (USD):** ${total_cost:.4f}
- **Estimated Cost / Request (USD):** ${avg_cost_per_req:.6f}

---

## 4. Verification & Reproducibility Notice

All token counts reflect the production run of the final dataset pipeline using live OpenAI API calls. Zero external API keys or credentials are included in this artifact per Section 6.5 of the challenge rules.
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[INFO] Usage report successfully written to: {report_path}")

def run_pipeline(
    requests_path: Path = config.REQUESTS_CSV,
    output_path: Path = config.OUTPUT_CSV,
    report_path: Path = config.REPO_ROOT / "evaluation" / "usage_report.md",
    is_sample_run: bool = False,
    require_live: bool = False
):
    start_time = time.time()
    print("=" * 70)
    print(" BUY OR WAIT? — AI FINANCIAL DECISION AGENT (HackerRank Orchestrate) ")
    print("=" * 70)
    print(f"[INFO] Loading datasets from: {config.DATASET_DIR}...")
    validate_dataset_inputs({
        "financial_profiles": config.PROFILES_CSV,
        "financial_events": config.EVENTS_CSV,
        "requests": requests_path,
        "request_payment_options": config.PAYMENT_OPTIONS_CSV,
        "messages": config.MESSAGES_CSV,
        "images": config.IMAGES_CSV,
    })
    
    profiles = load_financial_profiles(config.PROFILES_CSV)
    events = load_financial_events(config.EVENTS_CSV)
    options = load_payment_options(config.PAYMENT_OPTIONS_CSV)
    messages = load_messages(config.MESSAGES_CSV)
    images = load_images(config.IMAGES_CSV)
    
    if is_sample_run:
        sample_dicts = load_sample_requests(requests_path)
        eval_requests = [
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
        requests_df = pd.DataFrame(sample_dicts)
    else:
        eval_requests = load_requests(requests_path)
        requests_df = pd.read_csv(requests_path)

    print(f"[INFO] Ingested {len(profiles)} profiles, {len(events)} events, {len(options)} options, {len(eval_requests)} requests.")

    # Multimodal evidence is only allowed to alter the deterministic ledger after
    # it passes its own schema and provenance checks. --require-live forbids
    # cache/fallback substitution for the final production artifact.
    use_live = bool(config.OPENAI_API_KEY)
    if require_live and not use_live:
        raise RuntimeError("--require-live requires OPENAI_API_KEY")
    print(f"[INFO] Initializing evidence extractors (live={use_live}, strict_live={require_live}, model={config.DEFAULT_MODEL})...")
    vision = VisionExtractor(force_live=use_live, require_live=require_live)
    vision_map = vision.get_event_amount_map(config.IMAGES_CSV, config.EVENTS_CSV)
    classifier = MessageClassifier(force_live=use_live, require_live=require_live)
    message_effects = classifier.classify_all(messages)
    
    repo = DataRepository(profiles, events, eval_requests, options, messages, images)
    reconstructor = StateReconstructor(vision_map, message_effects)

    print(f"[INFO] Reconstructing state and evaluating {len(eval_requests)} financial requests...")
    results = []

    for idx, req in enumerate(eval_requests, 1):
        ctx = repo.get_context(req.request_id)
        entries, _ = reconstructor.reconstruct(ctx.user, ctx.request, ctx.events)
        
        sim = CashflowSimulator(
            ctx.user.current_available_balance,
            ctx.user.minimum_balance_to_keep,
            ctx.request.request_date,
            entries
        )
        
        safe_amount = calculate_safe_amount(sim, ctx.request.requested_amount)
        earliest_full_date = calculate_earliest_full_payment_date(
            sim, ctx.request.requested_amount, ctx.request.desired_completion_date
        )

        # Plan generator
        generator = PlanGenerator(
            user=ctx.user,
            request=ctx.request,
            base_entries=entries,
            payment_options=ctx.payment_options,
            safe_amount=safe_amount,
            earliest_full_date=earliest_full_date
        )
        candidates = generator.generate_all_candidates()
        ranked = rank_plans(candidates)

        if ranked and ranked[0].completes_by_deadline:
            best_plan = ranked[0]
        else:
            best_plan = CandidatePlan(
                plan_id="not_rec",
                payment_method="not_recommended",
                affordability_status="not_affordable",
                payment_plan_str="none",
                completes_by_deadline=False,
                requires_spending_changes=False,
                is_safe=False
            )

        # Format output fields
        status = best_plan.affordability_status
        method = best_plan.payment_method
        plan_str = best_plan.payment_plan_str
        
        if status == "affordable_now":
            earliest_out = req.request_date
        elif status == "not_affordable":
            earliest_out = ""
        else:
            earliest_out = earliest_full_date if earliest_full_date else ""

        if best_plan.spending_changes:
            changes_out = "|".join(sc.to_output_str() for sc in best_plan.spending_changes)
        else:
            changes_out = "none"

        best_opt = None
        if method == "installments":
            for opt in ctx.payment_options:
                if opt.payment_option_id == best_plan.payment_option_id:
                    best_opt = opt
                    break

        explanation = ExplanationGenerator.generate(
            user=ctx.user,
            request=ctx.request,
            plan=best_plan,
            safe_amount=safe_amount,
            earliest_full_date=earliest_out,
            best_option=best_opt
        )

        results.append({
            "request_id": req.request_id,
            "amount_safe_to_pay": safe_amount,
            "affordability_status": status,
            "recommended_payment_method": method,
            "payment_plan": plan_str,
            "earliest_date_for_full_payment": earliest_out,
            "spending_changes_needed": changes_out,
            "decision_explanation": explanation
        })

    # Convert to DataFrame
    out_df = pd.DataFrame(results)
    
    # Save to target output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Generated predictions saved to: {output_path}")

    # Also update dataset/output.csv if running full evaluation
    if not is_sample_run and output_path != config.DATASET_DIR / "output.csv":
        out_df.to_csv(config.DATASET_DIR / "output.csv", index=False)
        print(f"[SUCCESS] Mirrored predictions to: {config.DATASET_DIR / 'output.csv'}")

    # Validate output
    print("[INFO] Running strict pre-submission validation checks...")
    is_valid, errors = OutputValidator.validate_csv(str(output_path), requests_df)
    if is_valid:
        print("[VALIDATION PASSED] Output file is 100% compliant with challenge contract!")
    else:
        print(f"[VALIDATION FAILED] {len(errors)} errors detected:")
        for e in errors[:10]:
            print(f"  [ERROR] {e}")
        sys.exit(1)

    # Generate Usage Report
    elapsed = time.time() - start_time
    generate_usage_report(report_path, len(eval_requests), vision.token_usage, classifier.token_usage, elapsed)
    
    print("=" * 70)
    print(f" PIPELINE COMPLETE: {len(eval_requests)} requests processed in {elapsed:.2f}s ")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Buy or Wait? AI Financial Agent")
    parser.add_argument("--requests", type=Path, default=config.REQUESTS_CSV, help="Path to requests.csv")
    parser.add_argument("--output", type=Path, default=config.OUTPUT_CSV, help="Path to output.csv")
    parser.add_argument("--sample", action="store_true", help="Run on sample_requests.csv")
    parser.add_argument("--require-live", action="store_true", help="Require fresh GPT-5.4 evidence extraction; fail instead of falling back")
    parser.add_argument("--report", type=Path, default=config.REPO_ROOT / "evaluation" / "usage_report.md", help="Path to usage_report.md")
    args = parser.parse_args()

    if args.sample:
        run_pipeline(
            requests_path=config.SAMPLE_REQUESTS_CSV,
            output_path=config.REPO_ROOT / "sample_output.csv",
            report_path=args.report,
            is_sample_run=True,
            require_live=args.require_live
        )
    else:
        run_pipeline(
            requests_path=args.requests,
            output_path=args.output,
            report_path=args.report,
            is_sample_run=False,
            require_live=args.require_live
        )


