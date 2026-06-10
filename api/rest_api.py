"""
HFOS v5.0 — Internal REST API
Lightweight endpoints for programmatic access and webhook integration.
Wraps service layer with JSON responses and JWT auth.
"""
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional
import urllib.parse

from services.auth_service import JWTManager
from services.scanner_service import ScannerService
from services.portfolio_service import PortfolioService
from services.alert_service import AlertService
from database.db_manager import execute_query

logger = logging.getLogger(__name__)
MAX_BODY_BYTES = 1_000_000


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _json_response(handler: "HFOSHandler", status: int, body: dict):
    payload = json.dumps(body, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _verify_jwt(handler: "HFOSHandler") -> Optional[dict]:
    auth = handler.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        return JWTManager().verify_token(token)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Request Handler
# ─────────────────────────────────────────────────────────────────────────────
class HFOSHandler(BaseHTTPRequestHandler):
    """
    Lightweight HTTP API handler.
    All endpoints require Bearer JWT in Authorization header.
    """
    log_message = lambda self, *a: None  # suppress default access log

    ROUTES_GET = {
        "/api/v1/health":    "_health",
        "/api/v1/signals":   "_signals",
        "/api/v1/portfolio": "_portfolio",
        "/api/v1/watchlist": "_watchlist",
        "/api/v1/alerts":    "_alerts",
    }
    ROUTES_POST = {
        "/api/v1/scan":      "_scan",
        "/api/v1/alert":     "_send_alert",
    }

    # ── GET dispatcher ────────────────────────────────────────────────────────
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/v1/health":
            _json_response(self, 200, {"status": "ok", "version": "5.0"})
            return

        user = _verify_jwt(self)
        if not user:
            _json_response(self, 401, {"error": "Unauthorized"})
            return

        handler_name = self.ROUTES_GET.get(path)
        if handler_name:
            try:
                getattr(self, handler_name)(user)
            except Exception as e:
                logger.error(f"API GET {path} error: {e}")
                _json_response(self, 500, {"error": str(e)})
        else:
            _json_response(self, 404, {"error": "Not found"})

    # ── POST dispatcher ───────────────────────────────────────────────────────
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        user = _verify_jwt(self)
        if not user:
            _json_response(self, 401, {"error": "Unauthorized"})
            return

        content_len = int(self.headers.get("Content-Length", 0))
        if content_len > MAX_BODY_BYTES:
            _json_response(self, 413, {"error": "Request body too large"})
            return
        body_raw    = self.rfile.read(content_len) if content_len else b"{}"
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            _json_response(self, 400, {"error": "Invalid JSON body"})
            return

        handler_name = self.ROUTES_POST.get(path)
        if handler_name:
            try:
                getattr(self, handler_name)(user, body)
            except Exception as e:
                logger.error(f"API POST {path} error: {e}")
                _json_response(self, 500, {"error": str(e)})
        else:
            _json_response(self, 404, {"error": "Not found"})

    # ── Endpoint implementations ──────────────────────────────────────────────
    def _health(self, user):
        _json_response(self, 200, {"status": "ok", "version": "5.0"})

    def _signals(self, user):
        """GET /api/v1/signals — Top buy signals from last 24h."""
        rows = execute_query(
            """SELECT s.symbol, s.sector, sc.alpha_score, sc.signal,
                      sc.confidence, sc.scored_at
               FROM scores sc JOIN stocks s ON sc.stock_id=s.id
               WHERE sc.signal IN ('STRONG_BUY','BUY')
               AND sc.scored_at >= datetime('now','-1 day')
               ORDER BY sc.alpha_score DESC LIMIT 20"""
        )
        _json_response(self, 200, {"signals": [dict(r) for r in rows]})

    def _portfolio(self, user):
        """GET /api/v1/portfolio — Active positions."""
        ps = PortfolioService()
        positions = ps.get_active_positions()
        exposure  = ps.get_sector_exposure()
        _json_response(self, 200, {
            "positions":        positions,
            "sector_exposure":  exposure,
            "position_count":   len(positions),
        })

    def _watchlist(self, user):
        """GET /api/v1/watchlist — All watchlist entries by tier."""
        from repositories.watchlist_repository import WatchlistRepository
        all_lists = WatchlistRepository().get_all()
        _json_response(self, 200, {"watchlists": all_lists})

    def _alerts(self, user):
        """GET /api/v1/alerts — Unsent alerts."""
        rows = execute_query(
            "SELECT * FROM alerts WHERE sent=0 ORDER BY priority DESC, created_at ASC LIMIT 50"
        )
        _json_response(self, 200, {"alerts": [dict(r) for r in rows]})

    def _scan(self, user, body: dict):
        """POST /api/v1/scan — Trigger scan for a single symbol or all."""
        symbol = body.get("symbol")
        scanner = ScannerService()
        if symbol:
            result = scanner.scan_single(symbol.upper())
            if not result:
                _json_response(self, 404, {"error": f"Symbol {symbol} not found or no data"})
                return
            _json_response(self, 200, {"result": result})
        else:
            limit   = int(body.get("limit", 50))
            results = scanner.scan_universe(limit=limit)
            _json_response(self, 200, {
                "scanned": len(results),
                "buy_signals": [r for r in results if r["signal"] in ("STRONG_BUY","BUY")][:10]
            })

    def _send_alert(self, user, body: dict):
        """POST /api/v1/alert — Send a manual alert."""
        message  = body.get("message", "")
        priority = body.get("priority", "MEDIUM")
        if not message:
            _json_response(self, 400, {"error": "message is required"})
            return
        svc = AlertService()
        sent = svc.send(message, priority=priority, alert_type="API_MANUAL",
                        delivery_method="TELEGRAM")
        _json_response(self, 200, {"sent": sent})


# ─────────────────────────────────────────────────────────────────────────────
# Server lifecycle
# ─────────────────────────────────────────────────────────────────────────────
_server: Optional[HTTPServer] = None


def start_api_server(host: str = "127.0.0.1", port: int = 8502) -> HTTPServer:
    """Start the HFOS REST API in a daemon thread. Returns server instance."""
    global _server
    if _server:
        return _server
    _server = HTTPServer((host, port), HFOSHandler)
    t = Thread(target=_server.serve_forever, name="hfos-api", daemon=True)
    t.start()
    logger.info(f"HFOS REST API listening on http://{host}:{port}")
    return _server


def stop_api_server():
    global _server
    if _server:
        _server.shutdown()
        _server = None
        logger.info("HFOS REST API stopped")
