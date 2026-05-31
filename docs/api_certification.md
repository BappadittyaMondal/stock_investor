# HFOS v5.0 — API Certification

## Execution Details
**Command:** `pytest tests/test_api.py -v`

## Endpoint Verification
| Endpoint | Method | Result | Validated Checks |
|----------|--------|--------|------------------|
| `/api/v1/auth/login` | POST | PASS | Success, Invalid Creds, Rate Limit |
| `/api/v1/stocks/screener` | GET | PASS | Auth Required, Valid Schema |
| `/api/v1/alpha/calculate` | POST | PASS | Auth Required, RBAC Enforced |
| `/api/v1/portfolio/health`| GET | PASS | DB Connection, Validation |

## Authorization & Rate Limits
- Verified JWT interceptor successfully blocks unauthenticated requests with 401 Unauthorized.
- Verified rate limiter applies 100 req/min limit to `/api/v1/` scope.

## Certification Status
**Status:** PASS
**Endpoint Failures:** 0
