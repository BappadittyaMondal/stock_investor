"""
HFOS v5.0 — Supabase Client integration
Provides the foundational connectivity to Supabase.
Currently unused by core engines (which rely on SQLite), but ready for phased adoption.
"""
import logging
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client | None:
    """Initialize and return the Supabase client if configured."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase credentials not configured in environment.")
        return None
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None
