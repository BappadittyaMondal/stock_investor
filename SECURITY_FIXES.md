# HFOS v5.0 SECURITY FIXES

## 1. Traceback Isolation
- **Issue**: Unhandled Python exceptions were dumping source code and internal system paths to end users.
- **Fix**: Wrapped all 17 Streamlit page `render()` functions inside a global `try...except` block. Standard users receive a generic failure warning. Users with the `ADMIN` role receive an expandable traceback component for debugging.

## 2. Unauthenticated Data Leakage
- **Issue**: Critical configuration missing warnings (like `HFOS_JWT_SECRET`) were visible in the sidebar prior to login.
- **Fix**: Delayed the rendering of boot warnings until successful JWT authentication.

## 3. Strict RBAC Application
- **Issue**: System-critical pages lacked strict role enforcement.
- **Fix**: Applied `@require_role("ADMIN")` decorator to `Settings`, `Data Center`, `Operations Center`, and `Calibration`.

## 4. XSS Sanitization
- **Issue**: Previous `unsafe_allow_html` implementations rendered user inputs without escaping.
- **Fix**: Input notes are now routed through `html.escape` prior to rendering.
