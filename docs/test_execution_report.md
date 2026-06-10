# Test Execution Report

## Pytest Run
- Command: `python -m pytest -q`
- Result: `116 passed`

## Coverage Run
- Command: `python -m pytest --cov=app --cov=api --cov=services --cov=engines --cov=database --cov-report=term-missing`
- Result: `116 passed`
- Overall coverage: `20%`

## Outcome
- No failing tests remained after the live run.
- The verified core pipeline tests, repository tests, auth tests, risk tests, screener tests, validator tests, and smoke E2E tests all passed.

