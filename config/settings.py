"""
HFOS v5.0 — Centralized Configuration
All settings loaded from environment variables. No hardcoded secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent


def _require_env(key: str, min_len: int = 1) -> str:
    """Raise immediately if a required env var is missing or too short."""
    val = os.environ.get(key, "")
    if len(val) < min_len:
        raise EnvironmentError(
            f"Required env var '{key}' is missing or too short (min {min_len} chars). "
            f"See .env.example for guidance."
        )
    return val


# ---------------------------------------------------------------------------
# Database & Supabase
# ---------------------------------------------------------------------------
DB_PATH: str = os.environ.get("DB_PATH", str(BASE_DIR / "hfos.db"))

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

# ---------------------------------------------------------------------------
# JWT / Auth
# ---------------------------------------------------------------------------
JWT_SECRET: str = os.environ.get("HFOS_JWT_SECRET", "")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
MAX_FAILED_LOGINS: int = int(os.environ.get("MAX_FAILED_LOGINS", "5"))
LOCKOUT_MINUTES: int = int(os.environ.get("LOCKOUT_MINUTES", "30"))
PASSWORD_MIN_LENGTH: int = 12
PBKDF2_ITERATIONS: int = 260_000

# ---------------------------------------------------------------------------
# AI / Anthropic
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
AI_DAILY_LIMIT_INR: float = float(os.environ.get("DAILY_AI_LIMIT_INR", "500"))
AI_MONTHLY_LIMIT_INR: float = float(os.environ.get("MONTHLY_AI_LIMIT_INR", "5000"))
CLAUDE_INR_PER_1K_IN: float = float(os.environ.get("CLAUDE_INR_PER_1K_IN", "0.25"))
CLAUDE_INR_PER_1K_OUT: float = float(os.environ.get("CLAUDE_INR_PER_1K_OUT", "1.25"))

# ---------------------------------------------------------------------------
# Telegram Alerts
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Email Fallback
# ---------------------------------------------------------------------------
SMTP_EMAIL: str = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))

# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------
SCREENER_BASE_URL: str = "https://www.screener.in/company/{symbol}/consolidated/"
PIB_RSS_URL: str = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
RBI_RSS_URL: str = "https://www.rbi.org.in/scripts/RSS.aspx"
SEBI_RSS_URL: str = "https://www.sebi.gov.in/sebi_data/rss/spcrs.xml"
DATA_STALENESS_HOURS: int = int(os.environ.get("DATA_STALENESS_HOURS", "24"))
MAX_RETRY_ATTEMPTS: int = int(os.environ.get("MAX_RETRY_ATTEMPTS", "3"))
RETRY_BACKOFF_FACTOR: float = float(os.environ.get("RETRY_BACKOFF_FACTOR", "2.0"))
REQUEST_TIMEOUT_SECS: int = int(os.environ.get("REQUEST_TIMEOUT_SECS", "30"))

# ---------------------------------------------------------------------------
# Alpha Engine
# ---------------------------------------------------------------------------
MIN_ALPHA_SCORE: float = float(os.environ.get("MIN_ALPHA_SCORE", "75.0"))
MAX_SECTOR_EXPOSURE_PCT: float = float(os.environ.get("MAX_SECTOR_EXPOSURE_PCT", "25.0"))
MAX_POSITION_SIZE_PCT: float = float(os.environ.get("MAX_POSITION_SIZE_PCT", "10.0"))
MIN_AVG_DAILY_VOLUME: int = int(os.environ.get("MIN_AVG_DAILY_VOLUME", "500000"))
MAX_PLEDGE_PCT: float = float(os.environ.get("MAX_PLEDGE_PCT", "40.0"))
MIN_MARKET_CAP_CR: float = float(os.environ.get("MIN_MARKET_CAP_CR", "200.0"))

# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
MAX_PORTFOLIO_POSITIONS: int = int(os.environ.get("MAX_PORTFOLIO_POSITIONS", "20"))
DEFAULT_STOP_LOSS_PCT: float = float(os.environ.get("DEFAULT_STOP_LOSS_PCT", "8.0"))
DEFAULT_TARGET_MULTIPLIER: float = float(os.environ.get("DEFAULT_TARGET_MULTIPLIER", "2.5"))
CAPITAL_INR: float = float(os.environ.get("CAPITAL_INR", "100000"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
LOG_DIR: Path = BASE_DIR / "logs"
LOG_ROTATION: str = os.environ.get("LOG_ROTATION", "10 MB")
LOG_RETENTION: str = os.environ.get("LOG_RETENTION", "30 days")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
MARKET_OPEN_TIME: str = "09:15"
MARKET_CLOSE_TIME: str = "15:30"
PRE_MARKET_SCAN_TIME: str = "08:30"
POST_MARKET_SCAN_TIME: str = "16:00"
WEEKEND_RESEARCH_TIME: str = "10:00"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_critical_settings() -> list[str]:
    """Returns list of warnings for non-critical missing settings."""
    warnings = []
    if not JWT_SECRET or len(JWT_SECRET) < 32:
        warnings.append("HFOS_JWT_SECRET not set — auth module disabled")
    if not ANTHROPIC_API_KEY:
        warnings.append("ANTHROPIC_API_KEY not set — AI Copilot disabled")
    if not TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_BOT_TOKEN not set — Telegram alerts disabled")
    return warnings
