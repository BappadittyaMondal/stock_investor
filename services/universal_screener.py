"""
HFOS v5.0 - Service entrypoint for the universal screener.

This keeps the public service path aligned with the mandate while reusing the
existing engine implementation.
"""
from engines.screener.universal_screener import FilterResult, UniversalScreener

__all__ = ["FilterResult", "UniversalScreener"]

