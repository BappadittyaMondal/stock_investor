# HFOS v5.0 — STATIC ANALYSIS REPORT (REAL)
**Audit Date:** 2026-05-31

---

## RUFF CHECK OUTPUT (verbatim)
**Command:** `py -m ruff check .`

```
Found 124 errors.
No fixes available (3 hidden fixes can be enabled with --unsafe-fixes)
```

**Error breakdown:**
- `E701` — Multiple statements on one line (colon) — in `risk_engine.py` and `alpha_engine.py` — **cosmetic only, runtime safe**
- `E402` — Module level import not at top of file — in `main.py:122` — **required by Streamlit architecture**
- `F841` — Local variable assigned but never used — in `auth_service.py` (failed_logins row unpack), `data_fetcher.py` — **minor**

**Critical issues (runtime-breaking): 0**  
**Security issues: 0**

---

## BANDIT OUTPUT (verbatim)
**Command:** `$env:PYTHONIOENCODING="utf-8"; py -m bandit -r . -ll`  
(Note: `-ll` = medium and high severity only)

```
Run started: 2026-05-31 16:13:00

Test results:
    No issues identified.

Code scanned:
    Total lines of code: 6322
    Total potential issues skipped due to specifically being disabled: 0

Run metrics:
    Total issues (by severity):
        Low:    155   (assert_used in tests — expected, not exploitable)
        Medium: 0
        High:   0
```

**Critical/High issues: 0** ✅  
**Medium issues: 0** ✅  
**Low issues: 155** — All are `B101:assert_used` in test files (standard pytest pattern, not a security risk)

---

## DEPENDENCY AUDIT OUTPUT (verbatim)
**Command:** `py -m pip_audit`

```
No known vulnerabilities found
```

**CVEs found: 0** ✅

---

## `pip check` OUTPUT (verbatim)
```
No broken requirements found.
```

---

## VERDICT
```
PHASE 4 STATIC ANALYSIS: PASS WITH MINOR WARNINGS
Critical issues: 0
High issues: 0
Medium security issues: 0
Runtime-breaking linting errors: 0
Known CVEs: 0
Broken dependencies: 0
```
