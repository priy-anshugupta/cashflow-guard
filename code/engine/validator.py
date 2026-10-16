"""
Comprehensive Output Validator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Ensures 100% compliance with AGENTS.md Section 6 and problem_statement.md.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
from datetime import datetime

REQUIRED_COLUMNS = [
    "request_id",
    "amount_safe_to_pay",
    "affordability_status",
    "recommended_payment_method",
    "payment_plan",
    "earliest_date_for_full_payment",
    "spending_changes_needed",
    "decision_explanation"
]

VALID_STATUSES = {"affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"}
VALID_METHODS = {"full_payment", "partial_payment", "installments", "wait", "not_recommended"}

class OutputValidator:
    @staticmethod
    def validate_csv(csv_path: str, expected_requests_df: pd.DataFrame) -> Tuple[bool, List[str]]:
        errors = []
        try:
            df = pd.read_csv(csv_path, keep_default_na=False)
        except Exception as e:
            return False, [f"Failed to read CSV: {e}"]

        # 1. Check columns
        if list(df.columns) != REQUIRED_COLUMNS:
            errors.append(f"Columns mismatch. Expected {REQUIRED_COLUMNS}, got {list(df.columns)}")

        # 2. Check row count
        if len(df) != len(expected_requests_df):
            errors.append(f"Row count mismatch. Expected {len(expected_requests_df)}, got {len(df)}")

        # 3. Row-by-row validation
        req_map = {r["request_id"]: r for _, r in expected_requests_df.iterrows()}

        for idx, row in df.iterrows():
            rid = row["request_id"]
            if rid not in req_map:
                errors.append(f"Row {idx}: unknown request_id '{rid}'")
                continue

            req = req_map[rid]
            req_amt = float(req["requested_amount"])
            req_date = str(req["request_date"])
            deadline = str(req.get("desired_completion_date", ""))

            # Safe amount
            try:
                safe_amt = float(row["amount_safe_to_pay"])
                if safe_amt < -1e-4 or safe_amt > (req_amt + 1e-4):
                    errors.append(f"[{rid}] amount_safe_to_pay {safe_amt} not in [0, {req_amt}]")
            except ValueError:
                errors.append(f"[{rid}] invalid amount_safe_to_pay: '{row['amount_safe_to_pay']}'")

            # Status and Method
            status = row["affordability_status"]
            method = row["recommended_payment_method"]
            if status not in VALID_STATUSES:
                errors.append(f"[{rid}] invalid affordability_status: '{status}'")
            if method not in VALID_METHODS:
                errors.append(f"[{rid}] invalid recommended_payment_method: '{method}'")

            # earliest_date_for_full_payment
            earliest = str(row["earliest_date_for_full_payment"]).strip()
            if status == "affordable_now":
                if earliest != req_date:
                    errors.append(f"[{rid}] affordable_now must have earliest_date == request_date ({req_date}), got '{earliest}'")
            elif status == "not_affordable":
                if earliest != "":
                    errors.append(f"[{rid}] not_affordable must have empty earliest_date, got '{earliest}'")
            elif earliest:
                try:
                    datetime.strptime(earliest, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"[{rid}] invalid date format for earliest_date: '{earliest}'")

            # Payment plan
            plan = str(row["payment_plan"]).strip()
            if method == "not_recommended":
                if plan != "none":
                    errors.append(f"[{rid}] not_recommended must have payment_plan == 'none', got '{plan}'")
            else:
                if plan == "none":
                    errors.append(f"[{rid}] {method} cannot have payment_plan == 'none'")
                else:
                    parts = plan.split("|")
                    total_plan_amt = 0.0
                    for p in parts:
                        sub = p.split(":")
                        if len(sub) != 2:
                            errors.append(f"[{rid}] invalid payment entry format: '{p}'")
                        else:
                            try:
                                datetime.strptime(sub[0], "%Y-%m-%d")
                                total_plan_amt += float(sub[1])
                            except ValueError:
                                errors.append(f"[{rid}] invalid date/amount in entry: '{p}'")

                    # Partial payment checks
                    if method == "partial_payment":
                        if len(parts) != 2:
                            errors.append(f"[{rid}] partial_payment must have exactly 2 payments, got {len(parts)}")
                        if status != "affordable_with_plan":
                            errors.append(f"[{rid}] partial_payment must have status 'affordable_with_plan', got '{status}'")
                        if abs(total_plan_amt - req_amt) > 0.05:
                            errors.append(f"[{rid}] partial payments sum {total_plan_amt} != requested {req_amt}")

            # Spending changes
            chg = str(row["spending_changes_needed"]).strip()
            if chg != "none":
                actions = chg.split("|")
                if len(actions) > 3:
                    errors.append(f"[{rid}] maximum 3 spending changes allowed, got {len(actions)}")
                seen_events = set()
                for a in actions:
                    parts = a.split(":")
                    if parts[0] not in ("stop", "reduce_to"):
                        errors.append(f"[{rid}] invalid spending change action '{parts[0]}'")
                    if len(parts) >= 2:
                        ev_id = parts[1]
                        if ev_id in seen_events:
                            errors.append(f"[{rid}] duplicate event_id in spending changes: '{ev_id}'")
                        seen_events.add(ev_id)
                    if parts[0] == "reduce_to" and len(parts) != 3:
                        errors.append(f"[{rid}] reduce_to must be reduce_to:<event_id>:<amt>, got '{a}'")

            # Explanation
            exp = str(row["decision_explanation"]).strip()
            if not exp:
                errors.append(f"[{rid}] empty decision_explanation")

        return (len(errors) == 0), errors