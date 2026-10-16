"""Dated exchange-rate conversion using only the supplied rate dataset."""

from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, Iterable
import math
import pandas as pd


class CurrencyRateError(ValueError):
    """Raised when the dataset cannot support a required dated conversion."""


class CurrencyEngine:
    def __init__(self, exchange_rates_path: Optional[Path] = None):
        self.dated_rates: Dict[Tuple[str, str, str], float] = {}
        self.rates_by_pair: Dict[Tuple[str, str], set[float]] = defaultdict(set)
        if exchange_rates_path and Path(exchange_rates_path).exists():
            self._load_exchange_rates(exchange_rates_path)

    def _load_exchange_rates(self, path: Path) -> None:
        df = pd.read_csv(path)
        required = {"rate_date", "from_currency", "to_currency", "rate"}
        missing = required.difference(df.columns)
        if missing:
            raise CurrencyRateError(f"exchange_rates.csv is missing required columns: {sorted(missing)}")

        for _, row in df.iterrows():
            date_str = str(row["rate_date"]).strip()[:10]
            from_currency = str(row["from_currency"]).strip().upper()
            to_currency = str(row["to_currency"]).strip().upper()
            rate = float(row["rate"])
            if not date_str or len(from_currency) != 3 or len(to_currency) != 3:
                raise CurrencyRateError("exchange_rates.csv contains an invalid date or currency code")
            if not math.isfinite(rate) or rate <= 0:
                raise CurrencyRateError("exchange_rates.csv contains a non-positive or non-finite rate")
            key = (date_str, from_currency, to_currency)
            existing = self.dated_rates.get(key)
            if existing is not None and not math.isclose(existing, rate, rel_tol=0.0, abs_tol=0.0):
                raise CurrencyRateError(f"Conflicting exchange rates for {key}")
            self.dated_rates[key] = rate
            self.rates_by_pair[(from_currency, to_currency)].add(rate)

    @staticmethod
    def _neighbors(
        edges: Iterable[Tuple[str, str, float]],
        currency: str,
    ) -> Iterable[Tuple[str, float]]:
        for source, target, rate in edges:
            if source == currency:
                yield target, rate
            if target == currency:
                yield source, 1.0 / rate

    def _rate_from_edges(
        self,
        from_currency: str,
        to_currency: str,
        edges: Iterable[Tuple[str, str, float]],
    ) -> Optional[float]:
        queue = deque([(from_currency, 1.0)])
        visited = {from_currency}
        edge_list = list(edges)
        while queue:
            currency, accumulated_rate = queue.popleft()
            for next_currency, edge_rate in self._neighbors(edge_list, currency):
                if next_currency in visited:
                    continue
                next_rate = accumulated_rate * edge_rate
                if next_currency == to_currency:
                    return next_rate
                visited.add(next_currency)
                queue.append((next_currency, next_rate))
        return None

    def get_rate(self, from_curr: str, to_curr: str, date_str: Optional[str] = None) -> float:
        from_currency = str(from_curr).strip().upper()
        to_currency = str(to_curr).strip().upper()
        if from_currency == to_currency:
            return 1.0
        if len(from_currency) != 3 or len(to_currency) != 3:
            raise CurrencyRateError("Currency codes must be ISO 4217 three-letter codes")

        normalized_date = str(date_str).strip()[:10] if date_str else ""
        if normalized_date:
            direct = self.dated_rates.get((normalized_date, from_currency, to_currency))
            if direct is not None:
                return direct
            dated_edges = [
                (source, target, rate)
                for (rate_date, source, target), rate in self.dated_rates.items()
                if rate_date == normalized_date
            ]
            dated_rate = self._rate_from_edges(from_currency, to_currency, dated_edges)
            if dated_rate is not None:
                return dated_rate

        # A rate may be used outside its listed date only when the supplied dataset
        # itself proves that pair is invariant. This avoids inventing a stale rate.
        invariant_edges = [
            (source, target, next(iter(rates)))
            for (source, target), rates in self.rates_by_pair.items()
            if len(rates) == 1
        ]
        invariant_rate = self._rate_from_edges(from_currency, to_currency, invariant_edges)
        if invariant_rate is not None:
            return invariant_rate

        date_detail = f" on {normalized_date}" if normalized_date else ""
        raise CurrencyRateError(f"No supported exchange-rate path from {from_currency} to {to_currency}{date_detail}")

    def convert(self, amount: float, from_curr: str, to_curr: str, date_str: Optional[str] = None) -> float:
        numeric_amount = float(amount)
        if not math.isfinite(numeric_amount):
            raise CurrencyRateError("Cannot convert a non-finite amount")
        return numeric_amount * self.get_rate(from_curr, to_curr, date_str)


_global_engine: Optional[CurrencyEngine] = None


def get_currency_engine() -> CurrencyEngine:
    global _global_engine
    if _global_engine is None:
        rates_path = Path(__file__).resolve().parent.parent.parent / "dataset" / "exchange_rates.csv"
        _global_engine = CurrencyEngine(rates_path)
    return _global_engine


import re


def normalize_localized_amount_str(raw_val: Any, currency: Optional[str] = None) -> Optional[float]:
    """Parse common numeric formats without changing a numeric value's magnitude."""
    if raw_val is None:
        return None
    if isinstance(raw_val, float) and (math.isnan(raw_val) or math.isinf(raw_val)):
        return None
    if isinstance(raw_val, (int, float)):
        return float(raw_val)

    value = str(raw_val).strip()
    if not value or value.lower() == "nan":
        return None
    value = re.sub(r"(?i)\b(USD|EUR|IDR|INR|ZAR|Rp|Rs)\b", "", value)
    value = re.sub(r"[\$€£₹R\s]", "", value)
    if not value:
        return None

    negative = value.startswith("-") or value.startswith("(")
    value = value.strip("-()")
    normalized_currency = currency.strip().upper() if currency else ""
    has_dot, has_comma = "." in value, "," in value
    if has_dot and has_comma:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif has_dot:
        if value.count(".") > 1 or (normalized_currency == "IDR" and len(value.rsplit(".", 1)[1]) == 3):
            value = value.replace(".", "")
    elif has_comma:
        if value.count(",") > 1:
            value = value.replace(",", "")
        elif normalized_currency == "EUR" or len(value.rsplit(",", 1)[1]) != 3:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return -result if negative else result


def convert_currency(amount: float, from_curr: str, to_curr: str, date_str: Optional[str] = None) -> float:
    return get_currency_engine().convert(amount, from_curr, to_curr, date_str)
