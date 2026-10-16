"""Enumerate only PRD-permitted spending changes and validate them in the simulator."""

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, List, Optional, Tuple

from data.models import UserProfile
from engine.state_reconstructor import CashFlowEntry


@dataclass(frozen=True)
class SpendingChange:
    action: str
    event_id: str
    saved_amount: float
    new_amount: Optional[float] = None
    category: str = ""
    description: str = ""

    def to_output_str(self) -> str:
        if self.action == "stop":
            return f"stop:{self.event_id}"
        if self.new_amount is None:
            raise ValueError("reduce_to requires a validated minimum amount")
        amount = f"{self.new_amount:.2f}".rstrip("0").rstrip(".")
        return f"reduce_to:{self.event_id}:{amount}"


class SpendingChangesOptimizer:
    MAX_CHANGES = 3

    @staticmethod
    def _event_candidates(user: UserProfile, entries: Iterable[CashFlowEntry]) -> List[SpendingChange]:
        by_event = {}
        for entry in entries:
            if entry.direction != "debit" or not entry.is_recurring or entry.flexibility == "fixed":
                continue
            record = by_event.setdefault(entry.event_id, {"entry": entry, "amount": 0.0, "count": 0, "floor": entry.minimum_allowed_amount})
            record["amount"] += float(entry.amount or 0.0)
            record["count"] += 1
            if entry.minimum_allowed_amount is not None:
                record["floor"] = float(entry.minimum_allowed_amount)

        candidates: List[SpendingChange] = []
        for event_id, record in by_event.items():
            entry = record["entry"]
            total_amount = record["amount"]
            if entry.flexibility in {"stoppable", "reducible_or_stoppable"} and user.can_stop_category(entry.category):
                candidates.append(SpendingChange("stop", event_id, total_amount, category=entry.category, description=entry.description))
            minimum = record["floor"]
            if (
                entry.flexibility in {"reducible", "reducible_or_stoppable"}
                and user.can_reduce_category(entry.category)
                and minimum is not None
            ):
                savings = total_amount - float(minimum) * record["count"]
                if savings > 0:
                    candidates.append(SpendingChange("reduce_to", event_id, savings, float(minimum), entry.category, entry.description))
        return candidates

    @classmethod
    def candidate_combinations(cls, user: UserProfile, entries: Iterable[CashFlowEntry]) -> List[List[SpendingChange]]:
        candidates = cls._event_candidates(user, entries)
        combinations_out: List[List[SpendingChange]] = []
        for count in range(1, min(cls.MAX_CHANGES, len(candidates)) + 1):
            for combo in combinations(candidates, count):
                if len({change.event_id for change in combo}) == count:
                    combinations_out.append(list(combo))
        return sorted(
            combinations_out,
            key=lambda combo: (len(combo), sum(change.saved_amount for change in combo), tuple(change.to_output_str() for change in combo)),
        )

    @classmethod
    def find_changes_to_unlock(
        cls,
        user: UserProfile,
        base_entries: List[CashFlowEntry],
        shortfall: float,
    ) -> List[SpendingChange]:
        """Backward-compatible selector; simulation remains the source of truth for safety."""
        if shortfall <= 0:
            return []
        for combo in cls.candidate_combinations(user, base_entries):
            if sum(change.saved_amount for change in combo) >= shortfall:
                return combo
        return []

