"""Run a synthetic cash-flow example without credentials or dataset access."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from engine.cashflow_simulator import CashflowSimulator
from engine.safe_amount import calculate_safe_amount
from engine.state_reconstructor import CashFlowEntry


def main():
    entries = [
        CashFlowEntry(
            date="2026-09-05", amount=1200.0, direction="debit",
            category="rent", description="Synthetic rent", event_id="demo_rent",
        ),
        CashFlowEntry(
            date="2026-09-10", amount=2000.0, direction="credit",
            category="salary", description="Synthetic confirmed salary", event_id="demo_salary",
        ),
    ]
    simulator = CashflowSimulator(3000.0, 1000.0, "2026-09-01", entries)
    requested = 1500.0
    safe = calculate_safe_amount(simulator, requested)
    full_payment = simulator.simulate(candidate_payments=[("2026-09-01", requested)])
    print(f"Requested: {requested:.2f}")
    print(f"Safe to pay today: {safe:.2f}")
    print(f"Full payment today preserves reserve: {full_payment.is_safe}")
    print(f"Lowest balance after full payment: {full_payment.min_balance_observed:.2f}")


if __name__ == "__main__":
    main()
