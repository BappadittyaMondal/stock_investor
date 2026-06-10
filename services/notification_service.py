"""HFOS v5.0 — Notification Service"""
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.signal_buffer = []
        
    def queue_signal(self, symbol: str, signal: str):
        """Bundles multiple signals to prevent mobile notification spam."""
        self.signal_buffer.append(f"{symbol}: {signal}")
        
    def flush_signals(self):
        """Dispatches bundled signals via Web Push/Telegram."""
        if len(self.signal_buffer) > 3:
            msg = f"Multiple Signals Generated ({len(self.signal_buffer)} stocks). Check Dashboard."
        elif self.signal_buffer:
            msg = " | ".join(self.signal_buffer)
        else:
            return
            
        self._dispatch("P3", "Trade Signals", msg)
        self.signal_buffer.clear()
        
    def send_alert(self, priority: str, title: str, message: str):
        """Immediate dispatch for critical alerts."""
        self._dispatch(priority, title, message)
        
    def _dispatch(self, priority: str, title: str, message: str):
        logger.info(f"[PUSH NOTIFICATION] {priority} - {title}: {message}")
