"""
HFOS v5.0 — Alert Service
Telegram primary + Email fallback. Retry logic with DB tracking.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import requests

from database.db_manager import execute_write, execute_query
from config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SMTP_EMAIL, SMTP_PASSWORD, SMTP_HOST, SMTP_PORT,
    MAX_RETRY_ATTEMPTS
)

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_TELEGRAM_LEN = 4096


class AlertService:
    """
    Alert delivery with Telegram primary → Email fallback.
    All alerts are persisted in DB and marked sent/failed.
    """

    def send(self, message: str, priority: str = "MEDIUM",
             alert_type: str = "INFO", stock_id: Optional[int] = None,
             delivery_method: str = "TELEGRAM") -> bool:
        """Send alert and persist to DB. Returns True if delivered."""
        alert_id = self._persist(alert_type, message, priority, stock_id, delivery_method)
        delivered = False

        if delivery_method in ("TELEGRAM", "BOTH"):
            delivered = self._send_telegram(message, priority)
        if delivery_method in ("EMAIL", "BOTH") and not delivered:
            delivered = self._send_email(
                subject=f"[HFOS] {priority}: {alert_type}",
                body=message
            )
        if delivery_method == "LOG" or not delivered:
            logger.info(f"[ALERT][{priority}] {message}")
            delivered = True  # LOG always succeeds

        if delivered and alert_id:
            execute_write(
                "UPDATE alerts SET sent=1, delivered_at=datetime('now') WHERE id=?",
                (alert_id,)
            )
        return delivered

    def send_critical(self, message: str, stock_id: Optional[int] = None):
        """Send CRITICAL alert — attempts both Telegram + Email."""
        self.send(message, "CRITICAL", "CRITICAL_ALERT", stock_id, "BOTH")

    def send_signal(self, symbol: str, signal: str, alpha: float,
                    price: float, stop_loss: float, target: float):
        """Format and send a trading signal alert."""
        emoji = {"STRONG_BUY": "🚀", "BUY": "📈", "ACCUMULATE": "📊",
                 "WATCH": "👁", "REJECT": "❌"}.get(signal, "•")
        msg = (
            f"{emoji} *HFOS SIGNAL: {signal}*\n"
            f"Stock:   `{symbol}`\n"
            f"Alpha:   `{alpha:.1f}/100`\n"
            f"Price:   ₹`{price:,.2f}`\n"
            f"SL:      ₹`{stop_loss:,.2f}` ({((price-stop_loss)/price*100):.1f}%)\n"
            f"Target:  ₹`{target:,.2f}` ({((target-price)/price*100):.1f}%)\n"
            f"R:R      `1:{((target-price)/(price-stop_loss)):.1f}`"
        )
        self.send(msg, "HIGH", "TRADING_SIGNAL")

    def retry_pending(self):
        """Retry unsent alerts (called by scheduler)."""
        rows = execute_query(
            """SELECT id, message, priority, delivery_method, retry_count
               FROM alerts WHERE sent=0 AND retry_count < ?
               ORDER BY priority DESC, created_at ASC LIMIT 20""",
            (MAX_RETRY_ATTEMPTS,)
        )
        for row in rows:
            delivered = self._send_telegram(row["message"], row["priority"])
            if delivered:
                execute_write(
                    "UPDATE alerts SET sent=1, delivered_at=datetime('now') WHERE id=?",
                    (row["id"],)
                )
            else:
                execute_write(
                    "UPDATE alerts SET retry_count=retry_count+1 WHERE id=?",
                    (row["id"],)
                )

    # -------------------------------------------------------------------------
    def _send_telegram(self, message: str, priority: str = "MEDIUM") -> bool:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.debug("Telegram not configured — skipping")
            return False
        try:
            # Truncate to Telegram limit
            text = message[:MAX_TELEGRAM_LEN]
            url  = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
            resp = requests.post(url, json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       text,
                "parse_mode": "Markdown",
            }, timeout=10)
            if resp.status_code == 200:
                logger.info(f"Telegram alert sent [{priority}]")
                return True
            logger.warning(f"Telegram failed: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            logger.warning(f"Telegram send error: {e}")
            return False

    def _send_email(self, subject: str, body: str) -> bool:
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.debug("Email not configured — skipping")
            return False
        try:
            msg = MIMEMultipart()
            msg["From"]    = SMTP_EMAIL
            msg["To"]      = SMTP_EMAIL
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(SMTP_EMAIL, SMTP_EMAIL, msg.as_string())
            logger.info(f"Email alert sent: {subject}")
            return True
        except Exception as e:
            logger.warning(f"Email send error: {e}")
            return False

    def _persist(self, alert_type: str, message: str, priority: str,
                 stock_id: Optional[int], delivery_method: str) -> Optional[int]:
        try:
            return execute_write(
                """INSERT INTO alerts(alert_type,stock_id,message,priority,delivery_method)
                   VALUES(?,?,?,?,?)""",
                (alert_type, stock_id, message[:4096], priority, delivery_method)
            )
        except Exception as e:
            logger.error(f"Alert persist failed: {e}")
            return None
