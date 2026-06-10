"""
HFOS v5.0 — Security: JWT + Password + RBAC + Account Lockout
OWASP-hardened authentication service.
"""
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt as pyjwt
from functools import wraps

from database.db_manager import execute_one, execute_write
from config.settings import (
    JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS,
    MAX_FAILED_LOGINS, LOCKOUT_MINUTES, PBKDF2_ITERATIONS
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RBAC permission map
# ---------------------------------------------------------------------------
PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "ADMIN": {
        "stocks":      ["read", "write", "delete"],
        "portfolio":   ["read", "write", "delete"],
        "users":       ["read", "write", "delete"],
        "settings":    ["read", "write"],
        "audit":       ["read"],
        "calibration": ["read", "write", "approve"],
        "alerts":      ["read", "write"],
    },
    "PORTFOLIO_MANAGER": {
        "stocks":      ["read", "write"],
        "portfolio":   ["read", "write"],
        "users":       [],
        "settings":    ["read"],
        "audit":       [],
        "calibration": ["read"],
        "alerts":      ["read", "write"],
    },
    "RESEARCHER": {
        "stocks":      ["read", "write"],
        "portfolio":   ["read"],
        "users":       [],
        "settings":    [],
        "audit":       [],
        "calibration": ["read"],
        "alerts":      ["read"],
    },
    "VIEWER": {
        "stocks":      ["read"],
        "portfolio":   ["read"],
        "users":       [],
        "settings":    [],
        "audit":       [],
        "calibration": [],
        "alerts":      [],
    },
}


# ---------------------------------------------------------------------------
# JWT Manager
# ---------------------------------------------------------------------------
class JWTManager:
    def __init__(self):
        if not JWT_SECRET or len(JWT_SECRET) < 32:
            raise RuntimeError(
                "HFOS_JWT_SECRET must be set and >= 32 chars. "
                "Generate: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

    def create_token(self, user_id: int, role: str) -> str:
        jti = secrets.token_hex(16)
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "role":    role,
            "exp":     now + timedelta(hours=JWT_EXPIRY_HOURS),
            "iat":     now,
            "jti":     jti,
        }
        return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except pyjwt.ExpiredSignatureError:
            raise ValueError("Token expired — please log in again.")
        except pyjwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")
        if self._is_blacklisted(payload["jti"]):
            raise ValueError("Token has been revoked.")
        return payload

    def revoke_token(self, token: str):
        try:
            payload = pyjwt.decode(
                token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            execute_write(
                "INSERT OR IGNORE INTO token_blacklist(jti,expires_at) VALUES(?,?)",
                (payload["jti"], exp.isoformat())
            )
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")

    def _is_blacklisted(self, jti: str) -> bool:
        try:
            row = execute_one(
                "SELECT 1 FROM token_blacklist WHERE jti=? AND expires_at > datetime('now')",
                (jti,)
            )
            return row is not None
        except Exception as e:
            logger.error(f"Token blacklist lookup failed: {e}")
            return True  # fail closed for security


# ---------------------------------------------------------------------------
# Password Service
# ---------------------------------------------------------------------------
class PasswordService:
    """PBKDF2-HMAC-SHA256, 260k iterations, per-user salt."""

    def hash_password(self, password: str) -> str:
        self._validate_strength(password)
        salt = secrets.token_hex(16)
        h    = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
        )
        return f"{salt}:{h.hex()}"

    def verify_password(self, password: str, stored: str) -> bool:
        try:
            salt, hash_hex = stored.split(":", 1)
            h = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
            )
            return secrets.compare_digest(h.hex(), hash_hex)
        except Exception:
            return False

    @staticmethod
    def _validate_strength(password: str):
        errors = []
        if len(password) < 12:
            errors.append("Must be at least 12 characters")
        if not any(c.isupper() for c in password):
            errors.append("Must contain at least one uppercase letter")
        if not any(c.isdigit() for c in password):
            errors.append("Must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=" for c in password):
            errors.append("Must contain at least one special character")
        if errors:
            raise ValueError("Password too weak: " + "; ".join(errors))


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------
class AuthService:
    """High-level auth: login, logout, lockout, audit."""

    def __init__(self):
        self.jwt   = JWTManager()
        self.pwd   = PasswordService()

    def login(self, username: str, password: str, ip: str = "") -> str:
        """Validate credentials and return JWT. Raises ValueError on failure."""
        # Input sanitization
        username = username.strip()[:100]

        row = execute_one(
            """SELECT id, password_hash, role, is_active, failed_logins, locked_until
               FROM users WHERE username=? COLLATE NOCASE""",
            (username,)
        )
        if not row:
            raise ValueError("Invalid credentials.")  # don't reveal existence

        uid, pwd_hash, role, is_active, failed, locked_until = (
            row["id"], row["password_hash"], row["role"],
            row["is_active"], row["failed_logins"], row["locked_until"]
        )

        if not is_active:
            raise ValueError("Account disabled. Contact admin.")

        if locked_until:
            lock_dt = datetime.fromisoformat(locked_until)
            if lock_dt > datetime.now(timezone.utc):
                raise ValueError(f"Account locked until {locked_until}. Try later.")

        if not self.pwd.verify_password(password, pwd_hash):
            self._record_failed_login(uid)
            raise ValueError("Invalid credentials.")

        self._reset_failed_logins(uid)
        self._audit(uid, "LOGIN", ip_address=ip)
        token = self.jwt.create_token(uid, role)
        logger.info(f"Login success: user_id={uid} role={role} ip={ip}")
        return token

    def logout(self, token: str, user_id: int, ip: str = ""):
        self.jwt.revoke_token(token)
        self._audit(user_id, "LOGOUT", ip_address=ip)

    def create_user(self, username: str, email: str, password: str,
                    role: str = "VIEWER", created_by: Optional[int] = None) -> int:
        """Create new user. Returns new user_id."""
        role = role.upper().strip()
        if role not in PERMISSIONS:
            raise ValueError(f"Invalid role: {role}")
        pwd_hash = self.pwd.hash_password(password)
        uid = execute_write(
            """INSERT INTO users(username,email,password_hash,role)
               VALUES(?,?,?,?)""",
            (username.strip(), email.strip().lower(), pwd_hash, role)
        )
        self._audit(created_by, "CREATE_USER",
                    detail=f"username={username} role={role}")
        return uid

    def has_permission(self, role: str, resource: str, action: str) -> bool:
        allowed = PERMISSIONS.get(role, {}).get(resource, [])
        return action in allowed

    # -------------------------------------------------------------------------
    def _record_failed_login(self, user_id: int):
        execute_write(
            "UPDATE users SET failed_logins=failed_logins+1 WHERE id=?", (user_id,)
        )
        row = execute_one("SELECT failed_logins FROM users WHERE id=?", (user_id,))
        if row and row["failed_logins"] >= MAX_FAILED_LOGINS:
            locked = (
                datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            ).isoformat()
            execute_write(
                "UPDATE users SET locked_until=? WHERE id=?", (locked, user_id)
            )
            logger.warning(f"User {user_id} locked out until {locked}")

    def _reset_failed_logins(self, user_id: int):
        execute_write(
            "UPDATE users SET failed_logins=0, locked_until=NULL, last_login=datetime('now') WHERE id=?",
            (user_id,)
        )

    def _audit(self, user_id: Optional[int], action: str,
               resource: str = "", detail: str = "", ip_address: str = ""):
        execute_write(
            "INSERT INTO audit_log(user_id,action,resource,detail,ip_address) VALUES(?,?,?,?,?)",
            (user_id, action, resource, detail, ip_address)
        )


# ---------------------------------------------------------------------------
# Streamlit session helper
# ---------------------------------------------------------------------------
def get_current_user() -> Optional[dict]:
    """Retrieve verified user from Streamlit session state."""
    try:
        import streamlit as st
        token = st.session_state.get("hfos_token")
        if not token:
            return None
        mgr = JWTManager()
        return mgr.verify_token(token)
    except Exception:
        return None


def require_role(*roles: str):
    """Decorator that checks current user role in Streamlit pages."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            import streamlit as st
            user = get_current_user()
            if not user:
                st.error("Please log in to access this page.")
                st.stop()
            if user["role"] not in roles:
                st.error(f"Access denied. Required role: {' or '.join(roles)}")
                st.stop()
            return fn(*args, **kwargs)
        return wrapper
    return decorator
