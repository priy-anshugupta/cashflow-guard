"""
Safe Amount Calculator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Determines amount_safe_to_pay on request_date before optional spending changes.
0 <= amount_safe_to_pay <= requested_amount.
"""

from engine.cashflow_simulator import CashflowSimulator
from engine.state_reconstructor import parse_date

def calculate_safe_amount(
    simulator: CashflowSimulator,
    requested_amount: float
) -> float:
    """
    Calculate the maximum amount the user can safely pay on request_date
    before optional spending changes, such that the 90-day balance never
    falls below minimum_balance_to_keep.
    """
    base_res = simulator.simulate()
    if base_res.min_cushion <= 0:
        return 0.0

    safe_amt = min(requested_amount, base_res.min_cushion)
    return round(max(0.0, safe_amt), 2)
