"""
Data loading module for HackerRank Orchestrate (September 2026) - Buy or Wait?
Loads and parses all CSV datasets into strongly typed domain dataclasses.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import math

from data.models import (
    UserProfile, FinancialEvent, RequestItem, 
    PaymentOption, MessageItem, ImageItem, OutputPrediction
)
from extraction.currency import normalize_localized_amount_str
import re

def sanitize_untrusted_text(val: Any) -> str:
    """
    Universal taint analysis & sanitization for text ingested from CSVs:
    1. Strips null bytes and non-printable control characters.
    2. Neutralizes XML/tag delimiter breakouts (e.g. </untrusted_message>, <system>, <instruction>).
    3. Escapes raw '<' and '>' to safe HTML entities so it can never be treated as prompt markup.
    """
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    
    # Strip null bytes and control characters (preserve normal \t and \n)
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    
    # Neutralize injection tag breakouts
    s = re.sub(r"</?(?:system|assistant|user|untrusted[a-z_]*|context|instructions?|prompt)[^>]*>", "[NEUTRALIZED_TAG]", s, flags=re.IGNORECASE)
    
    # Escape tag delimiters if present
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    return s

def _clean_str(val: Any) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()

def _clean_optional_str(val: Any) -> Optional[str]:
    s = _clean_str(val)
    return s if s else None

def _clean_float(val: Any, currency: Optional[str] = None) -> Optional[float]:
    if pd.isna(val):
        return None
    try:
        return normalize_localized_amount_str(val, currency)
    except (ValueError, TypeError):
        return None

def _clean_pipe_list(val: Any) -> List[str]:
    s = _clean_str(val)
    if not s:
        return []
    return [item.strip() for item in s.split("|") if item.strip()]

def load_financial_profiles(path: Path) -> Dict[str, UserProfile]:
    """Load financial_profiles.csv keyed by user_id."""
    df = pd.read_csv(path)
    profiles = {}
    for _, row in df.iterrows():
        user_id = _clean_str(row["user_id"])
        max_inst = _clean_float(row.get("max_installment_months"))
        p = UserProfile(
            user_id=user_id,
            home_currency=_clean_str(row["home_currency"]),
            current_available_balance=_clean_float(row["current_available_balance"]) or 0.0,
            minimum_balance_to_keep=_clean_float(row["minimum_balance_to_keep"]) or 0.0,
            financial_priorities=_clean_pipe_list(row.get("financial_priorities")),
            expense_categories_to_protect=_clean_pipe_list(row.get("expense_categories_to_protect")),
            expense_categories_user_is_willing_to_reduce=_clean_pipe_list(row.get("expense_categories_user_is_willing_to_reduce")),
            expense_categories_user_is_willing_to_stop=_clean_pipe_list(row.get("expense_categories_user_is_willing_to_stop")),
            payment_methods_user_will_consider=_clean_pipe_list(row.get("payment_methods_user_will_consider")),
            max_installment_months=max_inst,
        )
        profiles[user_id] = p
    return profiles

def load_financial_events(path: Path) -> List[FinancialEvent]:
    """Load financial_events.csv."""
    df = pd.read_csv(path)
    events = []
    for _, row in df.iterrows():
        e = FinancialEvent(
            event_id=_clean_str(row["event_id"]),
            user_id=_clean_str(row["user_id"]),
            event_type=_clean_str(row["event_type"]),
            description=sanitize_untrusted_text(row.get("description", "")),
            category=_clean_str(row.get("category", "")),
            direction=_clean_str(row.get("direction", "debit")),
            amount=_clean_float(row.get("amount")),
            currency=_clean_str(row.get("currency", "")),
            event_date=_clean_str(row["event_date"]),
            settlement_date=_clean_optional_str(row.get("settlement_date")),
            status=_clean_str(row.get("status", "settled")),
            linked_event_id=_clean_optional_str(row.get("linked_event_id")),
            flexibility=_clean_str(row.get("flexibility", "fixed")),
            minimum_allowed_amount=_clean_float(row.get("minimum_allowed_amount")),
        )
        events.append(e)
    return events

def load_requests(path: Path) -> List[RequestItem]:
    """Load requests.csv."""
    df = pd.read_csv(path)
    requests = []
    for _, row in df.iterrows():
        allows_part = bool(row.get("allows_partial_payment", False))
        if isinstance(row.get("allows_partial_payment"), str):
            allows_part = row["allows_partial_payment"].strip().lower() in ("true", "1", "yes")
        
        req = RequestItem(
            request_id=_clean_str(row["request_id"]),
            user_id=_clean_str(row["user_id"]),
            request_date=_clean_str(row["request_date"]),
            request_type=_clean_str(row.get("request_type", "")),
            requested_amount=_clean_float(row["requested_amount"]) or 0.0,
            desired_completion_date=_clean_str(row["desired_completion_date"]),
            allows_partial_payment=allows_part,
            request_text=sanitize_untrusted_text(row.get("request_text", "")),
        )
        requests.append(req)
    return requests

def load_sample_requests(path: Path) -> List[Dict[str, Any]]:
    """Load sample_requests.csv with both inputs and expected ground truth outputs."""
    df = pd.read_csv(path)
    samples = []
    for _, row in df.iterrows():
        d = row.to_dict()
        samples.append(d)
    return samples

def load_payment_options(path: Path) -> List[PaymentOption]:
    """Load request_payment_options.csv."""
    df = pd.read_csv(path)
    options = []
    for _, row in df.iterrows():
        num_pmts = int(row.get("number_of_payments", 1))
        opt = PaymentOption(
            payment_option_id=_clean_str(row["payment_option_id"]),
            request_id=_clean_str(row["request_id"]),
            payment_method=_clean_str(row.get("payment_method", "full_payment")),
            payment_amount=_clean_float(row.get("payment_amount")) or 0.0,
            number_of_payments=num_pmts,
            first_payment_date=_clean_str(row["first_payment_date"]),
            payment_frequency_days=_clean_float(row.get("payment_frequency_days")),
            financing_fee=_clean_float(row.get("financing_fee")) or 0.0,
            total_payable_amount=_clean_float(row.get("total_payable_amount")) or 0.0,
        )
        options.append(opt)
    return options

def load_messages(path: Path) -> List[MessageItem]:
    """Load messages.csv."""
    df = pd.read_csv(path)
    messages = []
    for _, row in df.iterrows():
        m = MessageItem(
            message_id=_clean_str(row["message_id"]),
            user_id=_clean_str(row["user_id"]),
            request_id=_clean_optional_str(row.get("request_id")),
            related_event_id=_clean_optional_str(row.get("related_event_id")),
            sent_at=_clean_str(row.get("sent_at", "")),
            source_type=_clean_str(row.get("source_type", "")),
            message_text=sanitize_untrusted_text(row.get("message_text", "")),
        )
        messages.append(m)
    return messages

def load_images(path: Path) -> List[ImageItem]:
    """Load images.csv."""
    df = pd.read_csv(path)
    images = []
    for _, row in df.iterrows():
        img = ImageItem(
            image_id=_clean_str(row["image_id"]),
            user_id=_clean_str(row["user_id"]),
            request_id=_clean_optional_str(row.get("request_id")),
            related_event_id=_clean_optional_str(row.get("related_event_id")),
        )
        images.append(img)
    return images
DATASET_REQUIRED_COLUMNS = {
    "financial_profiles": {"user_id", "home_currency", "current_available_balance", "minimum_balance_to_keep", "financial_priorities", "expense_categories_to_protect", "expense_categories_user_is_willing_to_reduce", "expense_categories_user_is_willing_to_stop", "payment_methods_user_will_consider", "max_installment_months"},
    "financial_events": {"event_id", "user_id", "event_type", "description", "category", "direction", "amount", "currency", "event_date", "settlement_date", "status", "linked_event_id", "flexibility", "minimum_allowed_amount"},
    "requests": {"request_id", "user_id", "request_date", "request_type", "requested_amount", "desired_completion_date", "allows_partial_payment", "request_text"},
    "request_payment_options": {"payment_option_id", "request_id", "payment_method", "payment_amount", "number_of_payments", "first_payment_date", "payment_frequency_days", "financing_fee", "total_payable_amount"},
    "messages": {"message_id", "user_id", "request_id", "related_event_id", "sent_at", "source_type", "message_text"},
    "images": {"image_id", "user_id", "request_id", "related_event_id"},
}


class DatasetSchemaError(ValueError):
    """Raised before inference when a participant-facing CSV violates its contract."""


def validate_dataset_inputs(paths: Dict[str, Path]) -> None:
    """Validate required schemas and identifiers before any evidence or financial inference."""
    frames: Dict[str, pd.DataFrame] = {}
    for name, required_columns in DATASET_REQUIRED_COLUMNS.items():
        path = paths[name]
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            raise DatasetSchemaError(f"Cannot read {name}.csv: {exc}") from exc
        missing = required_columns.difference(frame.columns)
        if missing:
            raise DatasetSchemaError(f"{name}.csv is missing required columns: {sorted(missing)}")
        frames[name] = frame

    for name, identifier in (("financial_profiles", "user_id"), ("financial_events", "event_id"), ("requests", "request_id"), ("request_payment_options", "payment_option_id"), ("messages", "message_id"), ("images", "image_id")):
        series = frames[name][identifier]
        if series.isna().any() or series.astype(str).str.strip().eq("").any() or series.duplicated().any():
            raise DatasetSchemaError(f"{name}.csv has missing or duplicate {identifier} values")

    profiles = frames["financial_profiles"]
    for column in ("current_available_balance", "minimum_balance_to_keep"):
        values = pd.to_numeric(profiles[column], errors="coerce")
        if values.isna().any() or ~pd.Series(values >= 0).all():
            raise DatasetSchemaError(f"financial_profiles.csv has invalid {column} values")

    requests = frames["requests"]
    requested = pd.to_numeric(requests["requested_amount"], errors="coerce")
    if requested.isna().any() or ~pd.Series(requested >= 0).all():
        raise DatasetSchemaError("requests.csv has invalid requested_amount values")
    for column in ("request_date", "desired_completion_date"):
        if pd.to_datetime(requests[column], format="%Y-%m-%d", errors="coerce").isna().any():
            raise DatasetSchemaError(f"requests.csv has invalid {column} values")

    events = frames["financial_events"]
    if not events["direction"].isin({"debit", "credit", "non_cash"}).all():
        raise DatasetSchemaError("financial_events.csv has an unsupported direction")
    if not events["status"].isin({"settled", "pending", "scheduled", "cancelled", "failed", "unrealized"}).all():
        raise DatasetSchemaError("financial_events.csv has an unsupported status")
    image_event_ids = set(frames["images"]["related_event_id"].dropna().astype(str))
    blank_event_amounts = events["amount"].isna()
    if not set(events.loc[blank_event_amounts, "event_id"].astype(str)).issubset(image_event_ids):
        raise DatasetSchemaError("A blank event amount is missing its required linked image evidence")

    options = frames["request_payment_options"]
    known_request_ids = set(requests["request_id"].astype(str))
    for filename in ("requests.csv", "sample_requests.csv"):
        sibling_path = paths["requests"].parent / filename
        if sibling_path.exists() and sibling_path != paths["requests"]:
            sibling_requests = pd.read_csv(sibling_path)
            if "request_id" not in sibling_requests.columns:
                raise DatasetSchemaError(f"{filename} is missing request_id")
            known_request_ids.update(sibling_requests["request_id"].dropna().astype(str))
    if not options["request_id"].astype(str).isin(known_request_ids).all():
        raise DatasetSchemaError("request_payment_options.csv references an unknown request")
    payment_counts = pd.to_numeric(options["number_of_payments"], errors="coerce")
    payment_amounts = pd.to_numeric(options["payment_amount"], errors="coerce")
    if payment_counts.isna().any() or (payment_counts < 1).any() or payment_amounts.isna().any() or (payment_amounts <= 0).any():
        raise DatasetSchemaError("request_payment_options.csv has invalid payment counts or amounts")




