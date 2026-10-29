# Pre-Indian-market restoration

Completed a targeted rollback on 29 October 2026. The recoverable baseline is Git commit `cee11a9` (`Add AI Trading project files`). This is not a blanket reset to that commit: the later learning and local AI Coach work is intentionally retained.

## Restored

- Previous Markets terminal, US stock watchlist, AAPL default, USD labels, candlestick/line/area chart controls, indicators and paper-order interface.
- Previous Twelve Data/Alpaca market-data adapter and configuration. Existing provider credentials were not replaced or printed.
- Original authenticated paper preview, submission and portfolio routes. The Indian integration's read-only restriction is gone.
- Previous Replay/Backtest symbol and monetary labels, retaining their lesson-exercise parameters and AI Coach integrations.

The restored fallback chart is explicitly labelled as demo when its source is simulated. Demo candles are not mixed with provider quote updates. Navbar/ticker labels no longer claim a live connection without evidence. Existing chart timestamp normalization is preserved. A first-buy bug found during verification was fixed by initializing the new position's mapped defaults before computing its cost.

## Removed from active application code

Upstox/NSE/BSE controls, broker router and worker, Indian account services/models, streaming schema, dedicated dependencies, migration file, setup helper, Indian-specific tests, documentation and preview artifacts were removed. No active Indian-market routes remain. The original market-data stream route is restored.

## Preserved

Local Ollama/Qwen coaching, private chat history, approved trading-only courses, progress, quizzes, bookmarks, notes, replay stepping, backtest stop/target exercises, SQLite-compatible symbol grouping, authentication, concurrent token refresh, and the longer local-model proxy timeout remain in place.

The database was not reset, replaced or migrated backward. All 31 existing tables remain, with no record-count decreases after restoration and browser checks. The four unused broker tables remain physically intact. No currencies or balances were converted. Ignored backend secrets, including the inactive encryption key needed to recover archived broker records, were preserved. Removing local code does not revoke any token at a broker; revoke tokens separately if required. No broker revocation request or real order was sent.

A SQLite backup, pre-rollback patch, archived Indian-integration files and database preservation check are stored locally under `.recovery/`, whose contents are Git-ignored. Treat its database backup as private.

## Verification

- 53 backend tests passed, including a new fixture-based buy/sell, duplicate submission and account-ownership check for the restored paper-order endpoints.
- Frontend TypeScript, scoped ESLint, token-refresh regression test and optimized production build passed.
- Markets, Dashboard, Training, Replay, Backtest, Journal and Settings returned HTTP 200.
- Browser: restored AAPL watchlist, candlestick rendering, line-chart switch and visible SMA overlay verified. Returned candles/quotes were labelled by the existing Twelve Data adapter. No claim is made about exchange latency or subscription entitlements.
- Lesson player and saved AI Coach conversation were checked separately. New model inference was not required for this rollback.
- Paper-order regression tests use explicit quote fixtures and a disposable in-memory database; no real user trades were created by those tests.

This restores the earlier code selectively while keeping later unrelated work. It is not a claim of byte-for-byte equivalence to a separate pre-India snapshot, which was not committed. Live market availability still depends on the existing provider configuration and permissions. Demo charts remain labelled simulation.
