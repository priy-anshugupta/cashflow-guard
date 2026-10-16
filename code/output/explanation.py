"""
Decision Explanation Generator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Generates concise, grounded, professional decision explanations matching ground truth style.
"""

from datetime import datetime
from typing import List, Optional

from data.models import UserProfile, RequestItem, PaymentOption
from engine.plan_generator import CandidatePlan
from engine.spending_changes import SpendingChange

def format_human_date(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'D Month YYYY' (e.g. '2024-03-03' -> '3 March 2024')."""
    if not date_str or date_str == "none":
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.strftime("%B")
        return f"{dt.day} {month} {dt.year}"
    except Exception:
        return date_str

def format_currency_amount(val: float, currency: str = "") -> str:
    """
    Format monetary amounts:
    If integer: 25256 -> '25,256'
    If decimal: 620.4 -> '620.40'
    """
    if abs(val - round(val)) < 1e-4:
        formatted_num = f"{int(round(val)):,}"
    else:
        formatted_num = f"{val:,.2f}"
    
    if currency:
        return f"{currency} {formatted_num}"
    return formatted_num

class ExplanationGenerator:
    @staticmethod
    def generate(
        user: UserProfile,
        request: RequestItem,
        plan: CandidatePlan,
        safe_amount: float,
        earliest_full_date: str,
        best_option: Optional[PaymentOption] = None
    ) -> str:
        curr = user.home_currency
        min_bal_str = format_currency_amount(user.minimum_balance_to_keep, curr)
        req_amt_str = format_currency_amount(request.requested_amount, curr)

        method = plan.payment_method

        # 1. full_payment
        if method == "full_payment":
            if plan.requires_spending_changes and plan.spending_changes:
                clauses = []
                for sc in plan.spending_changes:
                    desc = sc.description.lower() if sc.description else "flexible expense"
                    if not desc.startswith("the ") and not desc.startswith("online ") and not desc.startswith("family ") and not desc.startswith("shared "):
                        desc = f"the {desc}"
                    elif desc.startswith("the "):
                        desc = desc
                    else:
                        desc = f"the {desc}"

                    if sc.action == "stop":
                        clauses.append(f"Stop {desc}")
                    elif sc.action == "reduce_to":
                        new_amt_str = format_currency_amount(sc.new_amount or 0.0, curr)
                        clauses.append(f"Reduce {desc} to {new_amt_str}")

                if len(clauses) == 1:
                    changes_text = clauses[0]
                elif len(clauses) == 2:
                    c2 = clauses[1]
                    c2_lower = c2[0].lower() + c2[1:]
                    changes_text = f"{clauses[0]} and {c2_lower}"
                else:
                    changes_text = ", ".join(clauses[:-1]) + f", and {clauses[-1][0].lower() + clauses[-1][1:]}"

                return f"{changes_text}, then pay {req_amt_str} today. This leaves at least {min_bal_str} available."
            else:
                return f"Pay {req_amt_str} today. This leaves at least {min_bal_str} available over the next 90 days."

        # 2. installments
        if method == "installments":
            num_pmts = plan.number_of_payments
            if plan.payments:
                pmt_amt = plan.payments[0][1]
                start_date_human = format_human_date(plan.payments[0][0])
            elif best_option:
                pmt_amt = best_option.payment_amount
                start_date_human = format_human_date(best_option.first_payment_date)
            else:
                pmt_amt = request.requested_amount / num_pmts
                start_date_human = format_human_date(request.request_date)

            pmt_amt_str = format_currency_amount(pmt_amt, curr)
            return f"Use {num_pmts} installments of {pmt_amt_str}, starting {start_date_human}. This leaves at least {min_bal_str} available."

        # 3. partial_payment
        if method == "partial_payment":
            p1_amt = plan.payments[0][1] if plan.payments else safe_amount
            p2_amt = plan.payments[1][1] if len(plan.payments) > 1 else (request.requested_amount - p1_amt)
            p2_date_human = format_human_date(plan.payments[1][0] if len(plan.payments) > 1 else earliest_full_date)

            p1_str = format_currency_amount(p1_amt, curr)
            p2_str = format_currency_amount(p2_amt, curr)

            return f"Pay {p1_str} today and the remaining {p2_str} on {p2_date_human}. This completes the full request and keeps the {min_bal_str} minimum protected."

        # 4. wait
        if method == "wait":
            wait_date_human = format_human_date(plan.payments[0][0] if plan.payments else earliest_full_date)
            return f"Pay {req_amt_str} in full on {wait_date_human}. Paying earlier would take the balance below the {min_bal_str} minimum."

        # 5. not_recommended
        deadline_human = format_human_date(request.desired_completion_date)
        if safe_amount > 0 and (request.requested_amount > 2 * user.minimum_balance_to_keep or not request.desired_completion_date):
            safe_str = format_currency_amount(safe_amount, curr)
            return f"Do not proceed with the {req_amt_str} request. Although {safe_str} is available today, the full amount cannot be completed safely within 90 days."
        else:
            return f"Do not make this payment by {deadline_human}. None of the available options keeps the {min_bal_str} minimum protected."

    @staticmethod
    def generate_counterfactual_explanation(
        user: UserProfile,
        request: RequestItem,
        chosen_plan: CandidatePlan,
        runner_up_plan: Optional[CandidatePlan],
        safe_amount: float,
        earliest_full_date: str
    ) -> str:
        """
        Generates detailed counterfactual comparison showing why the chosen plan
        triumphed over alternative options (e.g. why installments over waiting, or why wait over not_recommended).
        """
        curr = user.home_currency
        req_amt_str = format_currency_amount(request.requested_amount, curr)
        safe_amt_str = format_currency_amount(safe_amount, curr)
        min_bal_str = format_currency_amount(user.minimum_balance_to_keep, curr)
        
        if not runner_up_plan:
            return f"Selected {chosen_plan.payment_method} as it is the only viable plan satisfying all liquidity constraints."
            
        c_method = chosen_plan.payment_method
        r_method = runner_up_plan.payment_method
        
        if c_method == "full_payment" and r_method != "full_payment":
            return f"Chose full payment today because the full amount ({req_amt_str}) is safely available immediately without incurring financing fees or delay."
        elif c_method == "installments" and r_method == "wait":
            return f"Chose installments over waiting until {format_human_date(earliest_full_date)} because installments complete the payment before the deadline while preserving the {min_bal_str} cushion."
        elif c_method == "installments" and r_method == "full_payment":
            return f"Chose installments over full payment because paying {req_amt_str} in full today would breach the {min_bal_str} minimum balance."
        elif c_method == "partial_payment" and r_method == "wait":
            return f"Chose partial payment to secure immediate partial fulfillment ({safe_amt_str} today) while settling the remainder on {format_human_date(earliest_full_date)}."
        elif c_method == "wait" and r_method == "not_recommended":
            return f"Chose wait until {format_human_date(earliest_full_date)} instead of rejecting the request, as sufficient liquidity recovers after upcoming scheduled income."
        else:
            return f"Chose {c_method} over {r_method} based on 6-level specification ranking hierarchy."