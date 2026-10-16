"""
Domain models for HackerRank Orchestrate (September 2026) - Buy or Wait?
Typed representations of users, events, requests, options, messages, and output predictions.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class UserProfile:
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: List[str] = field(default_factory=list)
    expense_categories_to_protect: List[str] = field(default_factory=list)
    expense_categories_user_is_willing_to_reduce: List[str] = field(default_factory=list)
    expense_categories_user_is_willing_to_stop: List[str] = field(default_factory=list)
    payment_methods_user_will_consider: List[str] = field(default_factory=list)
    max_installment_months: Optional[float] = None

    def considers_method(self, method: str) -> bool:
        """Check if user considers this payment method."""
        return method in self.payment_methods_user_will_consider

    def can_stop_category(self, category: str) -> bool:
        return category in self.expense_categories_user_is_willing_to_stop

    def can_reduce_category(self, category: str) -> bool:
        return category in self.expense_categories_user_is_willing_to_reduce

    def is_protected_category(self, category: str) -> bool:
        return category in self.expense_categories_to_protect


@dataclass
class FinancialEvent:
    event_id: str
    user_id: str
    event_type: str  # expense, income, subscription, debt_payment, refund, etc.
    description: str
    category: str
    direction: str  # debit, credit, non_cash
    amount: Optional[float]  # Can be None if extracted from image
    currency: str
    event_date: str  # YYYY-MM-DD
    settlement_date: Optional[str]  # YYYY-MM-DD
    status: str  # settled, pending, scheduled, cancelled, failed, unrealized
    linked_event_id: Optional[str] = None
    flexibility: str = "fixed"  # fixed, stoppable, reducible, reducible_or_stoppable
    minimum_allowed_amount: Optional[float] = None

    @property
    def is_stoppable(self) -> bool:
        return self.flexibility in ("stoppable", "reducible_or_stoppable")

    @property
    def is_reducible(self) -> bool:
        return self.flexibility in ("reducible", "reducible_or_stoppable")

    @property
    def is_credit(self) -> bool:
        return self.direction == "credit"

    @property
    def is_debit(self) -> bool:
        return self.direction == "debit"

    @property
    def is_non_cash(self) -> bool:
        return self.direction == "non_cash"


@dataclass
class RequestItem:
    request_id: str
    user_id: str
    request_date: str  # YYYY-MM-DD
    request_type: str
    requested_amount: float
    desired_completion_date: str  # YYYY-MM-DD
    allows_partial_payment: bool
    request_text: str


@dataclass
class PaymentOption:
    payment_option_id: str
    request_id: str
    payment_method: str  # full_payment, installments
    payment_amount: float
    number_of_payments: int
    first_payment_date: str  # YYYY-MM-DD
    payment_frequency_days: Optional[float] = None
    financing_fee: float = 0.0
    total_payable_amount: float = 0.0


@dataclass
class MessageItem:
    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    sent_at: str
    source_type: str
    message_text: str


@dataclass
class ImageItem:
    image_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]

    @property
    def file_path(self) -> str:
        return f"dataset/media/images/{self.image_id}.png"


@dataclass
class OutputPrediction:
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str  # affordable_now, affordable_with_plan, affordable_later, not_affordable
    recommended_payment_method: str  # full_payment, partial_payment, installments, wait, not_recommended
    payment_plan: str  # YYYY-MM-DD:amount|... or none
    earliest_date_for_full_payment: str  # YYYY-MM-DD or empty string
    spending_changes_needed: str  # stop:<id>|reduce_to:<id>:<amt> or none
    decision_explanation: str

    def to_csv_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": self.amount_safe_to_pay,
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }
