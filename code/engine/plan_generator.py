"""
Plan Generator and Ranker for HackerRank Orchestrate (September 2026) - Buy or Wait?
Generates candidate payment plans across full_payment, installments, partial_payment, wait, and not_recommended.
Ranks eligible safe plans using the exact 6-level hierarchy from the problem statement:
1. Complete the full request by desired_completion_date.
2. Require no spending changes.
3. Minimize the total amount paid.
4. Start payment earlier.
5. Use fewer payments.
6. Use the lowest payment_option_id as the final tie-breaker.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from data.models import UserProfile, RequestItem, PaymentOption
from engine.state_reconstructor import CashFlowEntry, parse_date, format_date
from engine.cashflow_simulator import CashflowSimulator
from engine.spending_changes import SpendingChange, SpendingChangesOptimizer

@dataclass
class CandidatePlan:
    plan_id: str
    payment_method: str  # "full_payment", "partial_payment", "installments", "wait", "not_recommended"
    affordability_status: str  # "affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"
    payment_plan_str: str  # "YYYY-MM-DD:amount|..." or "none"
    payments: List[Tuple[str, float]] = field(default_factory=list)
    spending_changes: List[SpendingChange] = field(default_factory=list)
    completes_by_deadline: bool = True
    requires_spending_changes: bool = False
    total_amount_paid: float = 0.0
    first_payment_date: str = ""
    last_payment_date: str = ""
    number_of_payments: int = 1
    payment_option_id: str = "zzz"  # For tie-breaking
    is_safe: bool = False

def rank_plans(plans: List[CandidatePlan]) -> List[CandidatePlan]:
    """
    Sort candidate plans by the 6-level spec priority:
    1. Completes by desired_completion_date (True before False)
    2. Requires no spending changes (False before True)
    3. Minimize total amount paid (ascending)
    4. Start payment earlier (first_payment_date ascending)
    5. Use fewer payments (number_of_payments ascending)
    6. Lowest payment_option_id (ascending string)
    """
    def sort_key(p: CandidatePlan):
        return (
            not p.completes_by_deadline,
            p.requires_spending_changes,
            round(p.total_amount_paid, 2),
            p.first_payment_date,
            p.number_of_payments,
            p.payment_option_id
        )

    return sorted(plans, key=sort_key)

class PlanGenerator:
    def __init__(
        self,
        user: UserProfile,
        request: RequestItem,
        base_entries: List[CashFlowEntry],
        payment_options: List[PaymentOption],
        safe_amount: float,
        earliest_full_date: str
    ):
        self.user = user
        self.request = request
        self.base_entries = base_entries
        self.payment_options = payment_options
        self.safe_amount = safe_amount
        self.earliest_full_date = earliest_full_date
        self.deadline_dt = parse_date(request.desired_completion_date)
        self.request_dt = parse_date(request.request_date)

    def _first_safe_spending_changes(self, payments: List[Tuple[str, float]]) -> List[SpendingChange]:
        simulator = CashflowSimulator(
            self.user.current_available_balance,
            self.user.minimum_balance_to_keep,
            self.request.request_date,
            self.base_entries,
        )
        for changes in SpendingChangesOptimizer.candidate_combinations(self.user, self.base_entries):
            encoded = [(change.action, change.event_id, change.new_amount) for change in changes]
            if simulator.simulate(candidate_payments=payments, spending_changes=encoded).is_safe:
                return changes
        return []
    def generate_all_candidates(self) -> List[CandidatePlan]:
        candidates: List[CandidatePlan] = []
        user_methods = set(self.user.payment_methods_user_will_consider)

        # ----------------------------------------------------
        # 1. full_payment
        # ----------------------------------------------------
        if "full_payment" in user_methods:
            # Check 1A: Safe today without spending changes
            if abs(self.safe_amount - self.request.requested_amount) < 1e-4:
                candidates.append(CandidatePlan(
                    plan_id="fp_today_clean",
                    payment_method="full_payment",
                    affordability_status="affordable_now",
                    payment_plan_str=f"{self.request.request_date}:{self._fmt_amt(self.request.requested_amount)}",
                    payments=[(self.request.request_date, self.request.requested_amount)],
                    completes_by_deadline=(self.request_dt <= self.deadline_dt),
                    requires_spending_changes=False,
                    total_amount_paid=self.request.requested_amount,
                    first_payment_date=self.request.request_date,
                    last_payment_date=self.request.request_date,
                    number_of_payments=1,
                    payment_option_id="full_0",
                    is_safe=True
                ))
            else:
                payments = [(self.request.request_date, self.request.requested_amount)]
                changes = self._first_safe_spending_changes(payments)
                if changes and self.request_dt <= self.deadline_dt:
                    candidates.append(CandidatePlan(
                        plan_id="fp_today_with_changes",
                        payment_method="full_payment",
                        affordability_status="affordable_with_plan",
                        payment_plan_str=f"{self.request.request_date}:{self._fmt_amt(self.request.requested_amount)}",
                        payments=payments,
                        spending_changes=changes,
                        completes_by_deadline=True,
                        requires_spending_changes=True,
                        total_amount_paid=self.request.requested_amount,
                        first_payment_date=self.request.request_date,
                        last_payment_date=self.request.request_date,
                        number_of_payments=1,
                        payment_option_id="full_changes",
                        is_safe=True,
                    ))

        # ----------------------------------------------------
        # 2. installments
        # ----------------------------------------------------
        if "installments" in user_methods:
            for opt in self.payment_options:
                if opt.payment_method != "installments":
                    continue

                # Check max_installment_months constraint
                if self.user.max_installment_months is not None:
                    # Estimate months from payments and frequency
                    freq = opt.payment_frequency_days or 30.0
                    duration_days = freq * (opt.number_of_payments - 1)
                    duration_months = duration_days / 30.0
                    if duration_months > (self.user.max_installment_months + 0.1):
                        continue

                # Generate installment schedule
                inst_payments = self._build_installment_schedule(opt)
                if not inst_payments:
                    continue

                last_pmt_dt = parse_date(inst_payments[-1][0])
                completes_deadline = (last_pmt_dt <= self.deadline_dt)

                # Test in simulator without spending changes
                sim = CashflowSimulator(
                    self.user.current_available_balance,
                    self.user.minimum_balance_to_keep,
                    self.request.request_date,
                    self.base_entries
                )
                res = sim.simulate(candidate_payments=inst_payments)

                plan_str = "|".join(f"{d}:{self._fmt_amt(a)}" for d, a in inst_payments)
                changes = [] if res.is_safe else self._first_safe_spending_changes(inst_payments)
                if res.is_safe or changes:
                    candidates.append(CandidatePlan(
                        plan_id=f"inst_{opt.payment_option_id}",
                        payment_method="installments",
                        affordability_status="affordable_with_plan",
                        payment_plan_str=plan_str,
                        payments=inst_payments,
                        spending_changes=changes,
                        completes_by_deadline=completes_deadline,
                        requires_spending_changes=bool(changes),
                        total_amount_paid=opt.total_payable_amount,
                        first_payment_date=inst_payments[0][0],
                        last_payment_date=inst_payments[-1][0],
                        number_of_payments=opt.number_of_payments,
                        payment_option_id=opt.payment_option_id,
                        is_safe=True
                    ))

        # ----------------------------------------------------
        # 3. partial_payment
        # ----------------------------------------------------
        if (self.request.allows_partial_payment and 
            "partial_payment" in user_methods and
            0 < self.safe_amount < self.request.requested_amount and
            self.earliest_full_date):
            
            p2_dt = parse_date(self.earliest_full_date)
            p1_amt = self.safe_amount
            p2_amt = round(self.request.requested_amount - p1_amt, 2)
            partial_payments = [
                (self.request.request_date, p1_amt),
                (self.earliest_full_date, p2_amt)
            ]
            completes_deadline = (p2_dt <= self.deadline_dt)

            sim = CashflowSimulator(
                self.user.current_available_balance,
                self.user.minimum_balance_to_keep,
                self.request.request_date,
                self.base_entries
            )
            res = sim.simulate(candidate_payments=partial_payments)
            if res.is_safe and completes_deadline:
                plan_str = f"{self.request.request_date}:{self._fmt_amt(p1_amt)}|{self.earliest_full_date}:{self._fmt_amt(p2_amt)}"
                candidates.append(CandidatePlan(
                    plan_id="partial_clean",
                    payment_method="partial_payment",
                    affordability_status="affordable_with_plan",
                    payment_plan_str=plan_str,
                    payments=partial_payments,
                    completes_by_deadline=completes_deadline,
                    requires_spending_changes=False,
                    total_amount_paid=self.request.requested_amount,
                    first_payment_date=self.request.request_date,
                    last_payment_date=self.earliest_full_date,
                    number_of_payments=2,
                    payment_option_id="partial_0",
                    is_safe=True
                ))

        # ----------------------------------------------------
        # 4. wait (single future full payment)
        # ----------------------------------------------------
        if "full_payment" in user_methods and self.earliest_full_date:
            p_dt = parse_date(self.earliest_full_date)
            if p_dt > self.request_dt:  # Only if in the future
                candidates.append(CandidatePlan(
                    plan_id="wait_future_full",
                    payment_method="wait",
                    affordability_status="affordable_later",
                    payment_plan_str=f"{self.earliest_full_date}:{self._fmt_amt(self.request.requested_amount)}",
                    payments=[(self.earliest_full_date, self.request.requested_amount)],
                    completes_by_deadline=(p_dt <= self.deadline_dt),
                    requires_spending_changes=False,
                    total_amount_paid=self.request.requested_amount,
                    first_payment_date=self.earliest_full_date,
                    last_payment_date=self.earliest_full_date,
                    number_of_payments=1,
                    payment_option_id="wait_0",
                    is_safe=True
                ))

        return candidates

    def _build_installment_schedule(self, opt: PaymentOption) -> List[Tuple[str, float]]:
        payments = []
        curr_dt = parse_date(opt.first_payment_date)
        freq = int(opt.payment_frequency_days or 30)
        each_amt = opt.payment_amount

        for i in range(opt.number_of_payments):
            payments.append((format_date(curr_dt), each_amt))
            curr_dt += timedelta(days=freq)

        return payments

    @staticmethod
    def _fmt_amt(val: float) -> str:
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"



