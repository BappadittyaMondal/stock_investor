# HFOS v5.0 — Paper Trading Certification

## Scope
Verification of the `PaperTradingEngine` lifecycle processing.

## Full Lifecycle Test
1. **Signal Generation:** Alpha Engine generated a 92-score `STRONG_BUY`.
2. **Order Creation:** Paper Trading Engine mapped entry limit price using current mock OHLCV.
3. **Portfolio Allocation:** Verified cash reserve reduced properly, and active positions table updated.
4. **Target Execution:** Mocked the next day's price hitting the +20% target.
5. **Exit & Reconciliation:** Engine recognized the target hit, closed the paper position, released the cash back to the reserve, and logged the realized PnL in the ledger.

## Certification Status
**Status:** PASS
**Lifecycle Failures:** 0
