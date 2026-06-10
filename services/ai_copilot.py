"""
HFOS v5.0 — AI Research Copilot
Claude-powered portfolio review, research assistant, report generation.
Cost-tracked with daily/monthly INR circuit breakers.
"""
import logging
from datetime import date

from database.db_manager import execute_write, execute_one
from config.settings import (
    GOOGLE_API_KEY, AI_DAILY_LIMIT_INR, AI_MONTHLY_LIMIT_INR
)
from providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AICopilot:
    """
    Claude-based AI Research Copilot.
    - Portfolio review with risk commentary
    - Stock deep-dive research
    - Concall summary parsing
    - Cost circuit-breaker: stops if daily/monthly INR limit exceeded
    """

    SYSTEM_PROMPT = """You are HFOS Research Copilot — a professional equity research
assistant for Indian markets. You help analyze stocks, portfolios, and market conditions.
Always include: NOT SEBI Registered | Private Research | Not Investment Advice.
Be concise, data-driven, and risk-aware. Format outputs in clear sections."""

    def __init__(self):
        if not GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set — AI Copilot disabled")
        self.provider = GeminiProvider()

    # -------------------------------------------------------------------------
    # PUBLIC
    # -------------------------------------------------------------------------
    def portfolio_review(self, portfolio_summary: str) -> str:
        """Generate AI portfolio review with risk commentary."""
        prompt = f"""Review this Indian equity portfolio and provide:
1. Portfolio health assessment (diversification, concentration risk)
2. Top 3 risks to watch
3. Recommended actions (exits, additions, rebalancing)
4. Sector rotation suggestions

Portfolio Data:
{portfolio_summary}

Keep response under 600 words. Be direct and specific."""
        return self._query(prompt, task="portfolio_review")

    def stock_research(self, symbol: str, fundamentals: str,
                       technical_summary: str, news_summary: str) -> str:
        """Generate deep-dive research note for a stock."""
        prompt = f"""Generate a professional research note for {symbol} (NSE/BSE):

FUNDAMENTALS:
{fundamentals}

TECHNICAL SUMMARY:
{technical_summary}

RECENT NEWS:
{news_summary}

Structure: Executive Summary | Investment Thesis | Key Risks | Valuation | Verdict
Max 500 words. End with: Not SEBI Registered | Private Research Only."""
        return self._query(prompt, task="stock_research")

    def parse_concall(self, concall_text: str, company: str) -> str:
        """Extract key insights from concall transcript."""
        prompt = f"""Extract key insights from this {company} earnings call transcript:

{concall_text[:8000]}

Extract:
1. Management guidance (revenue, margins, capex)
2. Key positive developments
3. Key risks/concerns mentioned
4. Analyst Q&A — most important questions and answers
5. Overall management tone (bullish/neutral/cautious)

Be concise — max 400 words."""
        return self._query(prompt, task="concall_parse")

    def ask(self, question: str, context: str = "") -> str:
        """Free-form research question."""
        prompt = f"{context}\n\nQuestion: {question}" if context else question
        return self._query(prompt, task="research_qa")

    # -------------------------------------------------------------------------
    # PRIVATE
    # -------------------------------------------------------------------------
    def _query(self, prompt: str, task: str = "general") -> str:
        """Execute AI query with cost tracking and circuit breaker."""
        if not GOOGLE_API_KEY:
            return "⚠️ AI Copilot unavailable: GOOGLE_API_KEY not configured."

        # Check cost circuit breaker
        if self._budget_exceeded():
            return "⚠️ AI budget limit reached. Copilot paused until reset."

        try:
            res = self.provider.query(prompt, self.SYSTEM_PROMPT)
            self._record_cost(task, res["tokens_in"], res["tokens_out"], res["cost_inr"], res.get("model_name", "gemini"))
            logger.info(f"AI query [{task}]: {res['tokens_in']}in/{res['tokens_out']}out ₹{res['cost_inr']:.4f}")
            return res["text"]

        except Exception as e:
            logger.error(f"AI Copilot error [{task}]: {e}")
            return f"⚠️ AI Copilot error: {e}"

    def _budget_exceeded(self) -> bool:
        """Check daily and monthly spend limits."""
        try:
            today = date.today().isoformat()
            month = date.today().strftime("%Y-%m")

            daily_row = execute_one(
                "SELECT SUM(cost_inr) AS total FROM api_costs WHERE created_at LIKE ?",
                (f"{today}%",)
            )
            monthly_row = execute_one(
                "SELECT SUM(cost_inr) AS total FROM api_costs WHERE created_at LIKE ?",
                (f"{month}%",)
            )
            daily_spend   = daily_row["total"]   or 0.0
            monthly_spend = monthly_row["total"] or 0.0

            if daily_spend >= AI_DAILY_LIMIT_INR:
                logger.warning(f"Daily AI budget exceeded: ₹{daily_spend:.2f} / ₹{AI_DAILY_LIMIT_INR}")
                return True
            if monthly_spend >= AI_MONTHLY_LIMIT_INR:
                logger.warning(f"Monthly AI budget exceeded: ₹{monthly_spend:.2f} / ₹{AI_MONTHLY_LIMIT_INR}")
                return True
            return False
        except Exception:
            return False  # fail open — prefer usability

    def _record_cost(self, task: str, tokens_in: int, tokens_out: int, cost_inr: float, model: str):
        execute_write(
            "INSERT INTO api_costs(model,task,tokens_in,tokens_out,cost_inr) VALUES(?,?,?,?,?)",
            (model, task, tokens_in, tokens_out, round(cost_inr, 6))
        )

    def get_monthly_spend(self) -> float:
        month = date.today().strftime("%Y-%m")
        row = execute_one(
            "SELECT SUM(cost_inr) AS total FROM api_costs WHERE created_at LIKE ?",
            (f"{month}%",)
        )
        return round(row["total"] or 0.0, 4) if row else 0.0
