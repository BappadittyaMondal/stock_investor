# Security Validation Report

## Bandit
- Command: `python -m bandit -r . -q`
- Result: no medium or high findings in the final run.
- Remaining findings: `155` low-severity `B101:assert_used` findings, all in test files.

## Fix Applied
- Removed the hardcoded JWT secret from `scripts/security_validation.py`.

## pip-audit
- Command: `python -m pip_audit`
- Result: blocked by host network permissions while trying to reach PyPI.
- Exact error: `HTTPSConnectionPool(host='pypi.org', port=443): Max retries exceeded ... [WinError 10013]`

