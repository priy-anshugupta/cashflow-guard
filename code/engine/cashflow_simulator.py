"""
Cashflow Simulator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Simulates the day-by-day cash balance across the 90-day forecast period.
Tracks minimum balance cushions, evaluates hypothetical payments, and applies spending changes.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import copy

from engine.state_reconstructor import CashFlowEntry, parse_date, format_date

@dataclass
class SimulationResult:
    is_safe: bool
    min_cushion: float
    min_cushion_date: str
    min_balance_observed: float
    daily_balances: Dict[str, float] = field(default_factory=dict)
    breach_dates: List[str] = field(default_factory=list)

class CashflowSimulator:
    def __init__(
        self,
        initial_balance: float,
        minimum_balance_to_keep: float,
        request_date: str,
        base_entries: List[CashFlowEntry],
        forecast_days: int = 90
    ):
        self.initial_balance = initial_balance
        self.minimum_balance_to_keep = minimum_balance_to_keep
        self.request_date = request_date
        self.start_dt = parse_date(request_date)
        self.end_dt = self.start_dt + timedelta(days=forecast_days)
        self.forecast_days = forecast_days
        self.base_entries = base_entries

    def simulate(
        self,
        candidate_payments: Optional[List[Tuple[str, float]]] = None,
        spending_changes: Optional[List[Tuple[str, str, Optional[float]]]] = None
    ) -> SimulationResult:
        """
        Simulate daily balance over forecast_days.
        
        Args:
            candidate_payments: List of (date_str, amount) to deduct.
            spending_changes: List of (action_type, event_id, new_amount) where action_type is 'stop' or 'reduce_to'.
        
        Returns:
            SimulationResult with safety check, cushion, and trajectory.
        """
        # Build maps for spending changes
        stopped_events: Set[str] = set()
        reduced_events: Dict[str, float] = {}
        if spending_changes:
            for item in spending_changes:
                action = item[0]
                ev_id = item[1]
                if action == "stop":
                    stopped_events.add(ev_id)
                elif action == "reduce_to":
                    reduced_events[ev_id] = item[2]

        # Separate daily credits and debits for conservative intra-day timing
        # Conservative settlement rule: all debits settle before any credits on the same calendar day
        daily_credits: Dict[str, float] = {}
        daily_debits: Dict[str, float] = {}
        
        # Populate all dates in forecast window with 0.0
        curr = self.start_dt
        while curr <= self.end_dt:
            d_str = format_date(curr)
            daily_credits[d_str] = 0.0
            daily_debits[d_str] = 0.0
            curr += timedelta(days=1)

        # Apply projected cashflow entries
        for entry in self.base_entries:
            entry_dt = parse_date(entry.date)
            if entry_dt < self.start_dt or entry_dt > self.end_dt:
                continue

            entry_date_str = format_date(entry_dt)
            amt = entry.amount

            # Apply spending changes
            if entry.event_id in stopped_events:
                continue
            elif entry.event_id in reduced_events:
                amt = reduced_events[entry.event_id]

            if entry.direction == "credit":
                daily_credits[entry_date_str] = daily_credits.get(entry_date_str, 0.0) + amt
            else:
                daily_debits[entry_date_str] = daily_debits.get(entry_date_str, 0.0) + amt

        # Apply candidate payments (all candidate payments are debits)
        if candidate_payments:
            for p_date, p_amt in candidate_payments:
                p_dt = parse_date(p_date)
                if self.start_dt <= p_dt <= self.end_dt:
                    p_date_str = format_date(p_dt)
                    daily_debits[p_date_str] = daily_debits.get(p_date_str, 0.0) + p_amt

        # Roll the balance forward day by day with intra-day debit-first ordering
        current_bal = self.initial_balance
        daily_balances: Dict[str, float] = {}
        min_cushion = float("inf")
        min_cushion_date = format_date(self.start_dt)
        min_bal_observed = float("inf")
        breach_dates: List[str] = []

        curr = self.start_dt
        while curr <= self.end_dt:
            d_str = format_date(curr)
            debits = daily_debits.get(d_str, 0.0)
            credits = daily_credits.get(d_str, 0.0)

            # Intra-day debit-first conservative settlement:
            # Check trough after all debits process but before credits arrive
            intra_day_min = current_bal - debits
            if intra_day_min < (self.minimum_balance_to_keep - 1e-4):
                breach_dates.append(d_str)

            cushion = intra_day_min - self.minimum_balance_to_keep
            if cushion < min_cushion:
                min_cushion = cushion
                min_cushion_date = d_str
                min_bal_observed = intra_day_min

            # Settle credits after debits
            current_bal = intra_day_min + credits
            daily_balances[d_str] = current_bal

            curr += timedelta(days=1)

        is_safe = len(breach_dates) == 0
        return SimulationResult(
            is_safe=is_safe,
            min_cushion=min_cushion,
            min_cushion_date=min_cushion_date,
            min_balance_observed=min_bal_observed,
            daily_balances=daily_balances,
            breach_dates=breach_dates
        )
