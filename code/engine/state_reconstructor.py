"""
Financial State Reconstructor for HackerRank Orchestrate (September 2026) - Buy or Wait?
Reconstructs the true financial position of a user:
1. Replaces blank amounts with vision-extracted amounts.
2. Applies message amendments (salary adjustments, rent increases, payroll date shifts).
3. Isolates adversarial scams, unconfirmed bonuses, and unrealized assets.
4. Detects recurring event streams (monthly, biweekly, weekly) and projects cashflow 90 days forward.
5. Reserves pending debits and confirmed scheduled salaries.
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import math
import copy

from data.models import FinancialEvent, UserProfile, RequestItem
from extraction.currency import convert_currency
from extraction.messages import MessageEffect

@dataclass
class CashFlowEntry:
    date: str  # YYYY-MM-DD
    amount: float  # in user's home currency
    direction: str  # 'credit' or 'debit'
    category: str
    description: str
    event_id: str
    is_flexible: bool = False
    flexibility: str = "fixed"
    minimum_allowed_amount: Optional[float] = None
    is_recurring: bool = False

def parse_date(date_str: str) -> datetime.date:
    return datetime.strptime(str(date_str).strip()[:10], "%Y-%m-%d").date()

def format_date(d: datetime.date) -> str:
    return d.strftime("%Y-%m-%d")

class StateReconstructor:
    def __init__(self, vision_amount_map: Dict[str, float], message_effects: Dict[str, MessageEffect]):
        self.vision_amount_map = vision_amount_map
        self.message_effects = message_effects

    @staticmethod
    def compute_volatility_cushion(amounts: List[float], buffer_factor: float = 0.5) -> float:
        """
        Calculate volatility-adjusted conservative expense projection:
        mu + buffer_factor * sigma, bounded between median and max historical observation.
        """
        if not amounts:
            return 0.0
        clean_amts = sorted([float(x) for x in amounts if x is not None and not math.isnan(x)])
        if not clean_amts:
            return 0.0
        if len(clean_amts) == 1:
            return clean_amts[0]
        
        median_val = clean_amts[len(clean_amts) // 2]
        mean_val = sum(clean_amts) / len(clean_amts)
        variance = sum((x - mean_val) ** 2 for x in clean_amts) / len(clean_amts)
        std_val = math.sqrt(variance)
        
        buffered = median_val + buffer_factor * std_val
        return min(max(clean_amts), max(median_val, round(buffered, 2)))

    def reconstruct(
        self,
        user: UserProfile,
        request: RequestItem,
        raw_events: List[FinancialEvent],
        forecast_days: int = 90
    ) -> Tuple[List[CashFlowEntry], List[FinancialEvent]]:
        """
        Returns:
            (projected_cashflow_entries_90_days, cleaned_historical_events)
        """
        request_date = parse_date(request.request_date)
        end_date = request_date + timedelta(days=forecast_days)
        user_currency = user.home_currency

        # Step 1: Clean and enrich raw events
        cleaned_events = []
        for e in raw_events:
            # Check for blank amount and fill from vision with plausibility envelope
            amt = e.amount
            if (amt is None or math.isnan(amt)) and e.event_id in self.vision_amount_map:
                extracted = self.vision_amount_map[e.event_id]
                # Plausibility Envelope: strictly positive finite number < 1 trillion
                if extracted is not None and not math.isnan(extracted) and 0.0 < extracted < 1e12:
                    amt = extracted
                else:
                    amt = 0.0

            if amt is None or math.isnan(amt):
                amt = 0.0

            # Convert to user home currency if needed
            rate_date = e.settlement_date or e.event_date
            converted_amount = convert_currency(amt, e.currency, user_currency, rate_date)
            converted_minimum = None
            if e.minimum_allowed_amount is not None:
                converted_minimum = convert_currency(e.minimum_allowed_amount, e.currency, user_currency, rate_date)

            cleaned_e = FinancialEvent(
                event_id=e.event_id,
                user_id=e.user_id,
                event_type=e.event_type,
                description=e.description,
                category=e.category,
                direction=e.direction,
                amount=converted_amount,
                currency=user_currency,
                event_date=e.event_date,
                settlement_date=e.settlement_date,
                status=e.status,
                linked_event_id=e.linked_event_id,
                flexibility=e.flexibility,
                minimum_allowed_amount=converted_minimum,
            )
            cleaned_events.append(cleaned_e)

        # Step 2: Apply user-specific messages
        salary_ended = False
        new_salary_amount: Optional[float] = None
        new_salary_date: Optional[str] = None
        temp_salary_amount: Optional[float] = None
        rent_multiplier: float = 1.0
        payroll_shift_date: Optional[str] = None

        for eff in self.message_effects.values():
            if eff.user_id == user.user_id:
                if eff.is_adversarial:
                    continue
                if eff.effect_type == "salary_ended":
                    salary_ended = True
                elif eff.effect_type == "salary_increase":
                    if eff.amount:
                        new_salary_amount = convert_currency(eff.amount, eff.currency or user_currency, user_currency)
                    new_salary_date = eff.effective_date
                elif eff.effect_type == "salary_temporary":
                    if eff.amount:
                        temp_salary_amount = convert_currency(eff.amount, eff.currency or user_currency, user_currency)
                elif eff.effect_type == "rent_increase":
                    if eff.percentage_increase:
                        rent_multiplier = 1.0 + (eff.percentage_increase / 100.0)
                elif eff.effect_type == "payroll_date_shift":
                    # PRD §6.1/§6.3: Message explicitly shifts payroll to a new date
                    payroll_shift_date = eff.effective_date

        # Step 3: Filter events
        # Separate historical from already-scheduled future events
        historical_settled = []
        future_known = []

        for e in cleaned_events:
            # Filter non-cash, cancelled, failed, unrealized
            if e.is_non_cash or e.status in ("cancelled", "failed", "unrealized"):
                continue

            event_dt = parse_date(e.settlement_date or e.event_date)

            # Pending credits must be ignored per rule
            if e.is_credit and e.status == "pending":
                continue

            # Pending debits must be reserved regardless of date (if originated before request date, reserve on request_date)
            if e.is_debit and e.status == "pending":
                if event_dt < request_date:
                    e_copy = copy.copy(e)
                    e_copy.event_date = format_date(request_date)
                    e_copy.settlement_date = format_date(request_date)
                    future_known.append(e_copy)
                else:
                    future_known.append(e)
            elif event_dt >= request_date:
                # Include scheduled debits and confirmed/scheduled credits
                if e.is_debit or (e.is_credit and e.status in ("settled", "scheduled")):
                    future_known.append(e)
            else:
                if e.status == "settled":
                    historical_settled.append(e)

        # Check if employment has ended (Final employer payroll in description)
        for e in historical_settled:
            if e.category == "salary" and "final" in (e.description or "").lower():
                salary_ended = True

        # Check if income is irregular gig platform earnings (not guaranteed future salary)
        is_gig_worker = any(
            e.category == "salary" and any(w in (e.description or "").lower() for w in ['platform', 'marketplace', 'weekly app'])
            for e in historical_settled
        )

        # Step 4: Detect Recurring Patterns from Historical Settled Events
        # For variable categories (groceries, transport, dining), group by (direction, category)
        # For fixed/subscriptions, group by (direction, category, description)
        streams: Dict[Tuple[str, str, str], List[FinancialEvent]] = defaultdict(list)
        for e in historical_settled:
            if e.category in ("groceries", "transport", "dining"):
                key = (e.direction, e.category, e.category)
            else:
                key = (e.direction, e.category, e.description)
            streams[key].append(e)

        projected_entries: List[CashFlowEntry] = []

        # Add known future events first
        for e in future_known:
            edt = parse_date(e.settlement_date or e.event_date)
            if edt <= end_date:
                amt = e.amount or 0.0
                if e.category == "rent" and rent_multiplier != 1.0:
                    amt *= rent_multiplier
                projected_entries.append(CashFlowEntry(
                    date=format_date(edt),
                    amount=amt,
                    direction=e.direction,
                    category=e.category,
                    description=e.description,
                    event_id=e.event_id,
                    is_flexible=(e.flexibility != "fixed"),
                    flexibility=e.flexibility,
                    minimum_allowed_amount=e.minimum_allowed_amount,
                    is_recurring=False
                ))

        # Project future occurrences from scheduled salary (if any)
        for e in future_known:
            if e.category == "salary" and not salary_ended:
                s_dt = parse_date(e.settlement_date or e.event_date)
                s_amt = e.amount or 0.0
                curr_s = s_dt + relativedelta(months=1)
                # Apply payroll date shift if message shifted the payroll day
                pshift_day = None
                if payroll_shift_date:
                    pshift_day = parse_date(payroll_shift_date).day
                while curr_s <= end_date:
                    if pshift_day:
                        try:
                            curr_s = curr_s.replace(day=pshift_day)
                        except ValueError:
                            pass
                    projected_entries.append(CashFlowEntry(
                        date=format_date(curr_s),
                        amount=s_amt,
                        direction="credit",
                        category="salary",
                        description=e.description,
                        event_id=e.event_id,
                        is_flexible=False,
                        flexibility="fixed",
                        is_recurring=True
                    ))
                    curr_s += relativedelta(months=1)

        # Project recurring streams into the forecast window
        for (direction, category, desc), ev_list in streams.items():
            # Exclude one-off, non-recurring categories
            if category in ("shopping", "refund", "windfall", "work_expense", "investment"):
                continue

            # Exclude unconfirmed variable credits (bonuses, commissions, irregular gig payouts)
            desc_lower = desc.lower()
            if direction == "credit" and any(k in desc_lower for k in ["commission", "bonus", "gig", "app earnings", "delivery platform", "lottery", "prize", "unrealized"]):
                continue

            if len(ev_list) < 2:
                # Need at least 2 occurrences to confirm recurrence
                continue

            # Sort by date
            ev_list.sort(key=lambda x: parse_date(x.settlement_date or x.event_date))
            last_ev = ev_list[-1]
            last_dt = parse_date(last_ev.settlement_date or last_ev.event_date)

            # Find most recent flexible event in this stream (if any)
            flex_ev = last_ev
            for ev in reversed(ev_list):
                if ev.flexibility != "fixed":
                    flex_ev = ev
                    break

            # Calculate average interval in days
            deltas = []
            for i in range(1, len(ev_list)):
                d1 = parse_date(ev_list[i-1].settlement_date or ev_list[i-1].event_date)
                d2 = parse_date(ev_list[i].settlement_date or ev_list[i].event_date)
                deltas.append((d2 - d1).days)
            avg_delta = sum(deltas) / len(deltas) if deltas else 30

            # Determine nominal amount (robust median of historical for variable categories)
            amts = [e.amount for e in ev_list if e.amount is not None]
            if category in ("groceries", "transport", "dining", "utilities", "shopping") and amts:
                amts.sort()
                nominal_amount = amts[len(amts) // 2]
            else:
                nominal_amount = last_ev.amount or 0.0

            # Special case for salary
            if category == "salary":
                if salary_ended or (is_gig_worker and not any(fe.category == "salary" for fe in future_known)):
                    # Do not project future recurring salary
                    continue
                # If there was already a scheduled future salary handled above, skip historical projection to avoid duplicates
                if any(fe.category == "salary" for fe in future_known):
                    continue
                if temp_salary_amount is not None:
                    nominal_amount = temp_salary_amount

            # Special case for rent
            if category == "rent" and rent_multiplier != 1.0:
                nominal_amount *= rent_multiplier

            # Generate future occurrences between request_date and end_date
            if 25 <= avg_delta <= 35:
                # Monthly on a specific day
                curr_dt = last_dt
                # Apply payroll date shift for salary if message explicitly moved it
                shift_day = None
                if category == "salary" and payroll_shift_date:
                    shift_day = parse_date(payroll_shift_date).day
                while True:
                    curr_dt = curr_dt + relativedelta(months=1)
                    # Override day-of-month if payroll date was shifted by message
                    if shift_day and category == "salary":
                        try:
                            curr_dt = curr_dt.replace(day=shift_day)
                        except ValueError:
                            pass  # e.g. Feb 30 -> keep as-is
                    if curr_dt > end_date:
                        break
                    if curr_dt >= request_date:
                        occ_amount = nominal_amount
                        if category == "salary" and new_salary_amount and new_salary_date:
                            if curr_dt >= parse_date(new_salary_date):
                                occ_amount = new_salary_amount

                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=occ_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))
            elif 4 <= avg_delta <= 6:
                # Every 5 days
                curr_dt = last_dt
                while True:
                    curr_dt = curr_dt + timedelta(days=5)
                    if curr_dt > end_date:
                        break
                    if curr_dt > request_date:
                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=nominal_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))
            elif 6.1 <= avg_delta <= 8.5:
                # Weekly (every 7 days)
                curr_dt = last_dt
                while True:
                    curr_dt = curr_dt + timedelta(days=7)
                    if curr_dt > end_date:
                        break
                    if curr_dt > request_date:
                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=nominal_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))
            elif 8.6 <= avg_delta <= 12:
                # Every 10 days
                curr_dt = last_dt
                while True:
                    curr_dt = curr_dt + timedelta(days=10)
                    if curr_dt > end_date:
                        break
                    if curr_dt > request_date:
                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=nominal_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))
            elif 12.1 <= avg_delta <= 17:
                # Bi-weekly (every 14 days)
                curr_dt = last_dt
                while True:
                    curr_dt = curr_dt + timedelta(days=14)
                    if curr_dt > end_date:
                        break
                    if curr_dt > request_date:
                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=nominal_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))
            elif 18 <= avg_delta <= 24:
                # Every 21 days
                curr_dt = last_dt
                while True:
                    curr_dt = curr_dt + timedelta(days=21)
                    if curr_dt > end_date:
                        break
                    if curr_dt > request_date:
                        projected_entries.append(CashFlowEntry(
                            date=format_date(curr_dt),
                            amount=nominal_amount,
                            direction=direction,
                            category=category,
                            description=desc,
                            event_id=flex_ev.event_id,
                            is_flexible=(flex_ev.flexibility != "fixed"),
                            flexibility=flex_ev.flexibility,
                            minimum_allowed_amount=flex_ev.minimum_allowed_amount,
                            is_recurring=True
                        ))

        # Sort projected entries chronologically
        projected_entries.sort(key=lambda x: parse_date(x.date))
        return projected_entries, cleaned_events






