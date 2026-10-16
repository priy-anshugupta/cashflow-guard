"""
Earliest Date Calculator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Determines earliest_date_for_full_payment: the first date when the full requested_amount
is safe to pay in a single payment WITHOUT spending changes.
Returns YYYY-MM-DD or empty string "" if not safe within the forecast period.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from engine.cashflow_simulator import CashflowSimulator
from engine.state_reconstructor import parse_date, format_date

def calculate_earliest_full_payment_date(
    simulator: CashflowSimulator,
    requested_amount: float,
    desired_completion_date: Optional[str] = None
) -> str:
    """
    Find the earliest date d in [request_date, request_date + forecast_days]
    where paying requested_amount in full on date d maintains balance >= minimum_balance_to_keep
    without spending changes.
    """
    base_res = simulator.simulate()
    daily_balances = base_res.daily_balances
    min_bal_keep = simulator.minimum_balance_to_keep
    
    # Sort dates chronologically
    sorted_dates = sorted(daily_balances.keys(), key=lambda x: parse_date(x))
    if not sorted_dates:
        return ""

    cushions = [daily_balances[d] - min_bal_keep for d in sorted_dates]
    n = len(sorted_dates)

    # Compute suffix minimums of cushion
    suffix_min = [0.0] * n
    curr_min = float("inf")
    for i in range(n - 1, -1, -1):
        if cushions[i] < curr_min:
            curr_min = cushions[i]
        suffix_min[i] = curr_min

    # Prefix minimum of cushion (must not breach before payment date)
    prefix_ok = True
    for i in range(n):
        # Check if balance before payment dipped below minimum
        if i > 0 and cushions[i - 1] < -1e-4:
            prefix_ok = False
        
        if not prefix_ok:
            # Cannot pay on or after a date where prior balance was already breached
            break

        # Suffix check: either all the way to the end, or through completion window
        if suffix_min[i] >= (requested_amount - 1e-4):
            return sorted_dates[i]

        if desired_completion_date:
            check_until = max(sorted_dates[i], desired_completion_date)
            window_ok = True
            for j in range(i, n):
                if sorted_dates[j] > check_until:
                    break
                if cushions[j] < (requested_amount - 1e-4):
                    window_ok = False
                    break
            if window_ok:
                return sorted_dates[i]

    return ""
