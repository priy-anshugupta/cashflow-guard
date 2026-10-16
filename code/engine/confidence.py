"""
Calibrated Confidence Calculator for HackerRank Orchestrate (September 2026) - Buy or Wait?
Implements PRD Section 11.2 calibrated confidence scoring based on data quality and financial risk.
"""

from typing import List, Optional
from data.models import UserProfile, RequestItem

def compute_confidence(
    user: UserProfile,
    request: RequestItem,
    status: str,
    method: str,
    safe_amount: float,
    spending_changes_count: int,
    requires_image_extraction: bool = False,
    has_modifying_messages: bool = False,
    has_foreign_currency: bool = False
) -> float:
    """
    Calibrated confidence based on data quality (PRD Section 11.2):
    - Base: 1.00
    - Reduce 0.05 if image extraction was needed
    - Reduce 0.03 if messages modified events
    - Reduce 0.02 if foreign currency conversion needed
    - Reduce 0.10 if balance cushion ratio is tight (< 0.10)
    - Reduce 0.05 if 2 or more spending changes needed
    - Floor at 0.50
    """
    confidence = 1.00

    if requires_image_extraction:
        confidence -= 0.05

    if has_modifying_messages:
        confidence -= 0.03

    if has_foreign_currency:
        confidence -= 0.02

    # Cushion ratio
    avail = user.current_available_balance
    min_bal = user.minimum_balance_to_keep
    if avail > 0:
        cushion_ratio = (avail - min_bal) / avail
        if cushion_ratio < 0.10:
            confidence -= 0.10

    if spending_changes_count >= 2:
        confidence -= 0.05

    return round(max(0.50, min(1.00, confidence)), 2)