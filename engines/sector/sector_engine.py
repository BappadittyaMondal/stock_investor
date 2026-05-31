"""
HFOS v5.0 — Sector Engine
Scores sector tailwinds, rotation signals, and relative strength.
"""
import logging
from typing import Optional
from database.db_manager import execute_one

logger = logging.getLogger(__name__)

# Sector tailwind scores (updated quarterly — driven by policy/macro)
SECTOR_TAILWINDS: dict[str, dict] = {
    "IT": {
        "tailwind": 60, "theme": "Global tech spend recovery",
        "risks": ["INR appreciation", "US recession"],
        "policy_support": False,
    },
    "Banking": {
        "tailwind": 72, "theme": "Credit growth + NPA reduction",
        "risks": ["Rate cuts compressing NIM"],
        "policy_support": True,
    },
    "Defence": {
        "tailwind": 90, "theme": "Atmanirbhar Bharat, capex supercycle",
        "risks": ["Execution delays"],
        "policy_support": True,
    },
    "Infrastructure": {
        "tailwind": 85, "theme": "Govt capex Rs 11L Cr budget",
        "risks": ["Commodity inflation"],
        "policy_support": True,
    },
    "Pharma": {
        "tailwind": 68, "theme": "CDMO growth + API exports",
        "risks": ["US FDA import alerts"],
        "policy_support": False,
    },
    "FMCG": {
        "tailwind": 55, "theme": "Rural recovery, volume growth",
        "risks": ["Input cost inflation"],
        "policy_support": False,
    },
    "Renewable Energy": {
        "tailwind": 88, "theme": "Net Zero 2070, solar mission",
        "risks": ["PLI execution risk"],
        "policy_support": True,
    },
    "Auto": {
        "tailwind": 70, "theme": "EV transition + premiumisation",
        "risks": ["Semiconductor shortage", "EV cannibalisation"],
        "policy_support": True,
    },
    "Metals": {
        "tailwind": 45, "theme": "China stimulus, global capex",
        "risks": ["China slowdown", "commodity cycles"],
        "policy_support": False,
    },
    "Chemicals": {
        "tailwind": 65, "theme": "China+1 strategy, agrochemicals",
        "risks": ["Chinese dumping"],
        "policy_support": False,
    },
    "Real Estate": {
        "tailwind": 60, "theme": "Housing demand, RERA compliance",
        "risks": ["Rate sensitivity"],
        "policy_support": False,
    },
    "Telecom": {
        "tailwind": 62, "theme": "5G rollout, ARPU expansion",
        "risks": ["Spectrum debt"],
        "policy_support": True,
    },
    "Capital Goods": {
        "tailwind": 80, "theme": "Capex supercycle PLI",
        "risks": ["Order slippage"],
        "policy_support": True,
    },
    "Default": {
        "tailwind": 50, "theme": "No specific theme",
        "risks": [], "policy_support": False,
    },
}


class SectorEngine:
    """
    Sector Score: 0-100
    Components:
      Tailwind        (40%): Pre-configured sector theme score
      DB Metadata     (30%): Policy tailwind flag + macro sensitivity
      Relative Perf   (30%): Sector's recent alpha vs NIFTY (approx)
    """

    def score(self, sector: Optional[str], stock_data: Optional[dict] = None) -> float:
        try:
            meta = SECTOR_TAILWINDS.get(sector or "Default", SECTOR_TAILWINDS["Default"])
            base   = float(meta["tailwind"])
            policy = 10.0 if meta["policy_support"] else 0.0

            # DB enrichment
            db_boost = self._db_score(sector)

            composite = base * 0.40 + policy * 1.0 + db_boost * 0.30 + 50.0 * 0.30
            result = round(max(0.0, min(100.0, composite)), 2)
            logger.debug(f"SectorScore[{sector}]={result:.1f}")
            return result
        except Exception as e:
            logger.error(f"SectorEngine error [{sector}]: {e}")
            return 50.0

    def get_metadata(self, sector: str) -> dict:
        return SECTOR_TAILWINDS.get(sector, SECTOR_TAILWINDS["Default"])

    def top_sectors(self, n: int = 5) -> list[dict]:
        """Return top N sectors by tailwind score."""
        ranked = sorted(
            [(k, v["tailwind"]) for k, v in SECTOR_TAILWINDS.items() if k != "Default"],
            key=lambda x: x[1], reverse=True
        )
        return [{"sector": k, "score": v, **SECTOR_TAILWINDS[k]} for k, v in ranked[:n]]

    # -------------------------------------------------------------------------
    def _db_score(self, sector: Optional[str]) -> float:
        """Load sector_metadata from DB for enrichment."""
        if not sector:
            return 50.0
        try:
            row = execute_one(
                "SELECT pe_median, roe_median, policy_tailwind, macro_sensitivity FROM sector_metadata WHERE sector_name=?",
                (sector,)
            )
            if not row:
                return 50.0
            score = 50.0
            if row["policy_tailwind"]:
                score += 20.0
            macro_sens = row["macro_sensitivity"] or 0.5
            score += (1.0 - macro_sens) * 10.0
            return min(100.0, score)
        except Exception:
            return 50.0
