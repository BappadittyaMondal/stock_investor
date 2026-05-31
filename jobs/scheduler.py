"""
HFOS v5.0 — APScheduler Job Definitions
Scheduled tasks: market scans, data refresh, alerts, DB maintenance.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron         import CronTrigger

from config.settings import (
    PRE_MARKET_SCAN_TIME, POST_MARKET_SCAN_TIME, WEEKEND_RESEARCH_TIME
)

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Job Functions
# ---------------------------------------------------------------------------
def job_pre_market_scan():
    """08:30 IST — Pre-market watchlist refresh."""
    try:
        logger.info("=== PRE-MARKET SCAN START ===")
        from services.scanner_service import ScannerService
        scanner = ScannerService()
        results = scanner.scan_universe(limit=50)  # Top 50 by market cap
        logger.info(f"Pre-market scan: {len(results)} stocks scored")
    except Exception as e:
        logger.error(f"Pre-market scan failed: {e}")


def job_post_market_scan():
    """16:00 IST — Full universe scan + signal generation."""
    try:
        logger.info("=== POST-MARKET SCAN START ===")
        from services.scanner_service import ScannerService
        scanner = ScannerService()
        results = scanner.scan_universe()
        buy_signals = [r for r in results if r["signal"] in ("STRONG_BUY", "BUY")]
        logger.info(f"Post-market: {len(results)} scored, {len(buy_signals)} buy signals")
    except Exception as e:
        logger.error(f"Post-market scan failed: {e}")


def job_alert_retry():
    """Every 30 min — Retry failed alert deliveries."""
    try:
        from services.alert_service import AlertService
        AlertService().retry_pending()
    except Exception as e:
        logger.error(f"Alert retry failed: {e}")


def job_data_freshness_check():
    """Every hour — Check data source health and alert if stale."""
    try:
        from database.db_manager import execute_query
        from services.alert_service import AlertService
        alerts = AlertService()
        stale = execute_query(
            "SELECT source, status, consecutive_failures FROM data_freshness WHERE status != 'GREEN'"
        )
        for s in stale:
            if s["consecutive_failures"] >= 3:
                alerts.send_critical(
                    f"⚠️ Data source [{s['source']}] has failed {s['consecutive_failures']} times consecutively."
                )
                logger.warning(f"Stale source: {s['source']} failures={s['consecutive_failures']}")
    except Exception as e:
        logger.error(f"Freshness check failed: {e}")


def job_db_maintenance():
    """Daily midnight — Clean old tokens, trim news, vacuum."""
    try:
        from database.db_manager import get_connection
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM token_blacklist WHERE expires_at < datetime('now')")
            conn.execute(
                "DELETE FROM news_items WHERE created_at < datetime('now', '-90 days')"
            )
            conn.execute(
                "DELETE FROM ohlcv_cache WHERE date < date('now', '-2 years')"
            )
        conn.execute("VACUUM")
        logger.info("DB maintenance complete")
    except Exception as e:
        logger.error(f"DB maintenance failed: {e}")


def job_paper_trade_close():
    """16:30 IST weekdays — Evaluate and close matured paper trades."""
    try:
        logger.info("=== PAPER TRADE CLOSE EVALUATION ===")
        from engines.paper_trading.paper_trading_engine import PaperTradingEngine
        summary = PaperTradingEngine().close_trades()
        logger.info(
            f"Paper trades: closed={summary['closed']} wins={summary['wins']} "
            f"losses={summary['losses']} stopped={summary['stopped']} "
            f"still_open={summary['still_open']}"
        )
    except Exception as e:
        logger.error(f"Paper trade close failed: {e}")


def job_weekend_research():
    """Saturday 10:00 — Weekly portfolio review."""
    try:
        logger.info("=== WEEKEND RESEARCH START ===")
        from services.portfolio_service import PortfolioService
        from services.ai_copilot import AICopilot

        ps     = PortfolioService()
        ai     = AICopilot()
        positions = ps.get_active_positions()
        if not positions:
            logger.info("No active positions — skipping weekend review")
            return

        pf_summary = "\n".join(
            f"- {p['symbol']} ({p['sector']}): qty={p['quantity']} avg=₹{p['avg_cost']:.2f}"
            for p in positions
        )
        review = ai.portfolio_review(pf_summary)
        from services.alert_service import AlertService
        AlertService().send(
            f"📊 *Weekly Portfolio Review*\n\n{review[:3000]}",
            priority="MEDIUM", alert_type="WEEKLY_REVIEW"
        )
        logger.info("Weekend research complete")
    except Exception as e:
        logger.error(f"Weekend research failed: {e}")


# ---------------------------------------------------------------------------
# Scheduler Manager
# ---------------------------------------------------------------------------
def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Pre-market scan — weekdays 08:30 IST
    h_pre, m_pre = PRE_MARKET_SCAN_TIME.split(":")
    scheduler.add_job(
        job_pre_market_scan, CronTrigger(
            day_of_week="mon-fri", hour=int(h_pre), minute=int(m_pre),
            timezone="Asia/Kolkata"
        ), id="pre_market_scan", replace_existing=True
    )

    # Post-market scan — weekdays 16:00 IST
    h_post, m_post = POST_MARKET_SCAN_TIME.split(":")
    scheduler.add_job(
        job_post_market_scan, CronTrigger(
            day_of_week="mon-fri", hour=int(h_post), minute=int(m_post),
            timezone="Asia/Kolkata"
        ), id="post_market_scan", replace_existing=True
    )

    # Alert retry — every 30 minutes
    scheduler.add_job(
        job_alert_retry, "interval", minutes=30,
        id="alert_retry", replace_existing=True
    )

    # Freshness check — every hour
    scheduler.add_job(
        job_data_freshness_check, "interval", hours=1,
        id="freshness_check", replace_existing=True
    )

    # DB maintenance — daily midnight
    scheduler.add_job(
        job_db_maintenance, CronTrigger(hour=0, minute=0),
        id="db_maintenance", replace_existing=True
    )

    # Paper trade close — weekdays 16:30 IST
    scheduler.add_job(
        job_paper_trade_close, CronTrigger(
            day_of_week="mon-fri", hour=16, minute=30,
            timezone="Asia/Kolkata"
        ), id="paper_trade_close", replace_existing=True
    )

    # Weekend research — Saturday 10:00 IST
    h_wk, m_wk = WEEKEND_RESEARCH_TIME.split(":")
    scheduler.add_job(
        job_weekend_research, CronTrigger(
            day_of_week="sat", hour=int(h_wk), minute=int(m_wk),
            timezone="Asia/Kolkata"
        ), id="weekend_research", replace_existing=True
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")
    return scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
