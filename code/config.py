"""
Global configuration module for HackerRank Orchestrate (September 2026) - Buy or Wait?
Ensures deterministic runs, secret handling strictly via environment variables (.env),
and centralized path management.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
CODE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CODE_DIR.parent

# Load environment variables strictly from .env
dotenv_path = REPO_ROOT / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)
    if not os.getenv("OPENAI_API_KEY") and os.getenv("\ufeffOPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("\ufeffOPENAI_API_KEY")

# LLM Configurations
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-5.4")
NLP_MODEL = os.getenv("NLP_MODEL", "gpt-5.4")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-5.4")
TEMPERATURE = 0.0
SEED = 42

# Dataset Paths
DATASET_DIR = REPO_ROOT / "dataset"
MEDIA_DIR = DATASET_DIR / "media" / "images"
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Specific File Paths
REQUESTS_CSV = DATASET_DIR / "requests.csv"
SAMPLE_REQUESTS_CSV = DATASET_DIR / "sample_requests.csv"
PROFILES_CSV = DATASET_DIR / "financial_profiles.csv"
EVENTS_CSV = DATASET_DIR / "financial_events.csv"
PAYMENT_OPTIONS_CSV = DATASET_DIR / "request_payment_options.csv"
EXCHANGE_RATES_CSV = DATASET_DIR / "exchange_rates.csv"
MESSAGES_CSV = DATASET_DIR / "messages.csv"
IMAGES_CSV = DATASET_DIR / "images.csv"

# Output Paths
ROOT_OUTPUT_CSV = REPO_ROOT / "output.csv"
OUTPUT_CSV = ROOT_OUTPUT_CSV
DATASET_OUTPUT_CSV = DATASET_DIR / "output.csv"
USAGE_REPORT_MD = REPO_ROOT / "evaluation" / "usage_report.md"

# Safety Invariants
MIN_CONFIDENCE = 0.50
MAX_SPENDING_CHANGES = 3
FORECAST_DAYS = 90
