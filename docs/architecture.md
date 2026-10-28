# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Training │  │  Replay  │  │ Backtest │  │ Dashboard  │  │
│  │   UI     │  │   UI     │  │   UI     │  │    UI      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │              │               │        │
│       └──────────────┴──────────────┴───────────────┘        │
│                          REST + WebSocket                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────┐
│                    Backend (FastAPI)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  AI Coach    │  │   Replay     │  │   Backtest        │  │
│  │  Service     │  │   Engine     │  │   Engine          │  │
│  │  (Claude)    │  │  (WebSocket) │  │  (Event-driven)   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │              │
│         │          ┌──────┴────────────────────┘              │
│         │          │                                         │
│         │    ┌─────┴──────────┐                              │
│         │    │  Execution     │   ← Shared module            │
│         │    │  Simulator     │                              │
│         │    └─────┬──────────┘                              │
│         │          │                                         │
│  ┌──────┴──────────┴─────────────────────────────────────┐   │
│  │              Market Data Layer                        │   │
│  │   (Ingestion adapters, candle queries, validation)    │   │
│  └───────────────────────┬───────────────────────────────┘   │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴─────┐    ┌──────┴──────┐   ┌──────┴──────┐
    │ TimescaleDB │  │  PostgreSQL │   │    Redis    │
    │ (OHLCV     │  │  (Users,    │   │  (Cache,    │
    │  candles)  │  │   sessions) │   │   pub/sub)  │
    └────────────┘  └─────────────┘   └─────────────┘
         ↑ Same container (TimescaleDB IS PostgreSQL)
```

## Key Design Decisions

### 1. Shared Execution Simulator
The order fill simulation logic (slippage, commissions, fill prices) is
extracted into a single `ExecutionSimulator` module used by both the
Backtest Engine and the Replay Engine. This ensures consistent behavior
between backtesting and practice trading.

### 2. Event-Driven Backtest Engine
The backtest engine processes candles bar-by-bar (not vectorized) to
support realistic order simulation including limit/stop orders that
trigger intra-bar.

### 3. Single TimescaleDB Instance
TimescaleDB is a PostgreSQL extension, so we use one database instance
for both time-series market data (hypertables) and relational data
(users, sessions, results).

### 4. Pluggable Data Adapters
The data ingestion layer uses an abstract adapter pattern so new data
vendors (Polygon.io, Alpha Vantage, etc.) can be added by implementing
a single interface.

## Module Dependencies

```
Phase 0: Scaffolding (no deps)
Phase 1: Market Data Layer (no deps)
Phase 2: Backtest Engine → Phase 1 (reads candles)
Phase 3: Backtest API → Phase 2 (wraps engine)
Phase 4: Replay Engine → Phase 1 + Phase 2 (shared execution)
Phase 5: AI Coach → Phase 3 + Phase 4 (analyzes results)
Phase 6-8: Frontend → Phase 3-5 (consumes APIs)
Phase 9: Auth → All modules (cross-cutting)
Phase 10: CI/CD → All modules (testing + deployment)
```
