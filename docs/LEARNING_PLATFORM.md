# AITrade: trading-only learning platform

The Training page contains only stock trading, AI-assisted trading, historical replay, strategy development, risk management and backtesting. General programming courses are excluded, including the earlier Python prerequisite.

## Architecture and scope

The native LMS reuses Next.js, FastAPI, SQLAlchemy, JWT authentication and the existing database. No additional LMS service, database, dependency or environment variable is introduced. Moodle was evaluated previously; its separate hosting and user synchronization are unnecessary for this application.

The initial catalog has 14 trading courses across the ten approved categories. The API enforces the category allowlist for the catalog, course details, enrollment, lessons, saved lessons and completed lessons. An arbitrary published course outside that allowlist cannot be opened through a guessed URL.

The former `python-foundations` course is unpublished, not deleted. Its enrollment, progress, bookmarks and quiz records remain intact. Seeding never recreates it. Existing trading course and lecture IDs and authored text remain unchanged. The stop-loss course now has three modules; risk-reward has two. The database originally had one module each, so missing modules were added. Completion records are retained; percentages reflect the additional lessons in the expanded curriculum.

## Course content and sources

AITrade supplies original reading lessons, quizzes and trading exercises, with no pretend video player. New course text is CC BY 4.0; existing lessons retain repository terms. This is an introductory trading curriculum, not a provider-issued certificate or a complete professional qualification.

Official external resources were checked for availability on 28 October 2026:

- QuantConnect machine-learning concepts: https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/key-concepts
- QuantConnect research guide: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide
- QuantConnect algorithm documentation: https://www.quantconnect.com/docs/v2/writing-algorithms
- Backtrader quickstart: https://www.backtrader.com/docu/quickstart/quickstart/

These are attributed external reading links, not republished articles, embedded paid courses, or assertions of permission to redistribute provider material. Each resource stores its provider, original URL and an explicit external-reading usage statement. Software being open source does not establish a license for all provider educational content. No scraping, video download, external course API credentials or fabricated media URLs are used.

## Interactive practice

A lesson's practice panel selects a stored historical symbol and timeframe. It shows the stored date range and opens the existing Replay or Backtest workspace with dataset/date fields populated, a simulation notice and a return-to-lesson link. It can import a permitted historical CSV/JSON file through the existing ingestion service, report validation failures and duplicates, and refresh the dataset selector. If no dataset exists or loading fails, the panel reports that state rather than inventing data. Training runs send `stored_only=true`: neither Replay nor Backtest may fall back to provider/demo candles when the selected stored range is empty. Existing non-training module behavior remains unchanged. Monte Carlo is hidden in training mode because its existing path does not enforce stored-only data.

Replay uses its existing candle chart, execution simulator, order ticket, speed/pause/resume controls and summary. A new `step` command advances exactly one candle while staying paused. Market, stop and limit tickets support simulated entry and exit practice; they do not route brokerage orders. Stop and target orders are individual tickets, not automatically linked OCO brackets. Learners record their plan before advancing, then compare decisions with the exercise objectives and save the review in lesson notes.

Backtest uses the existing SMA crossover strategy and execution engine. The short/long SMA periods configure entry/exit signals; share quantity configures position size. Optional stop-loss/take-profit percentages are evaluated at the known bar close and generate an exit at the next bar's open with the engine's execution costs. They are explicitly not intrabar protective orders. Zero disables an optional exit. Parameter values are validated; short must be less than long. Last-five-run comparisons use actual engine return, win rate, profit factor, drawdown and trade count, held in the current workspace. Backtest runs continue to persist through the existing backend service.

AI lessons describe prediction evaluation but do not claim that the SMA strategy is an AI model or that this application trains one. AI Coach receives the selected lesson's notes through the existing service. The coach now uses self-hosted Ollama/Qwen with private conversations and no paid API key. See `docs/AI_COACH.md` for setup and validation. Certificates are not displayed.

## Modified implementation

- `backend/app/services/learning_catalog.py`: trading-only categories, idempotent migration, original lessons, module additions, source attribution and practice modes.
- `backend/app/routers/curriculum.py`: allowlist enforcement and existing authenticated LMS endpoints.
- `backend/app/core/db_init.py`: startup seed and clean connection disposal for standalone initialization.
- `backend/app/routers/data.py`: portable dataset aggregation for both SQLite and PostgreSQL, replacing PostgreSQL-only `array_agg`.
- `backend/app/services/replay_service.py`, `backend/app/schemas/replay.py`: one-candle step.
- `backend/app/engine/strategies/sma_crossover.py`: optional close-based risk exits and parameter validation.
- `backend/app/services/backtest_service.py`, `backend/app/routers/backtest.py`, `backend/app/routers/replay.py`, and simulation schemas: stored-only training requests, preventing silent demo fallback.
- `frontend/src/components/LearningCatalog.tsx`, `frontend/src/lib/learning.ts`, `frontend/src/app/training/learning.css`: specialized sections and approved categories.
- `frontend/src/components/TradingExercise.tsx`, `TrainingExerciseBanner.tsx`: dataset selection, objectives, external reading and return navigation.
- `frontend/src/lib/api.ts`: multipart dataset upload through the existing authenticated request/refresh helper.
- `frontend/src/app/training/[courseId]/learn/[lessonId]/page.tsx`: practice panel alongside existing notes, progress, quizzes and coach.
- `frontend/src/app/replay/page.tsx`, `frontend/src/app/backtest/page.tsx`: exercise prefill, simulation context, step control, risk settings and version comparisons.
- `backend/tests/test_learning.py`, `backend/tests/test_trading_training.py`: persistence, retirement, filtering, dataset portability, simulation step and next-bar risk exits.

The initial LMS files remain: `models/learning.py`, course-details route, typed request helper, video component for permitted future trading videos, and the six additive tables in `backend/migrations/001_learning.sql`. Existing Dashboard, Markets, Journal and Settings features are retained.

## Setup and migrations

No new schema change is needed for this correction. The existing additive LMS tables are `course_info`, `lesson_info`, `enrollments`, `lecture_progress`, `bookmarks` and `quiz_results`, with ownership keys, foreign keys and indexes. The initial PostgreSQL schema migration is `backend/migrations/001_learning.sql`; SQLite uses the same SQLAlchemy definitions. Enrollment completion is derived from lesson completion. This app does not use Supabase or Firebase; private data access is enforced by authenticated FastAPI queries.

From `backend`, using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m app.core.db_init
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Initialization also runs automatically at startup. It applies the category migration, retires the general course, adds missing trading material and preserves learning records. Do not replace or delete the existing database. Existing `DATABASE_URL`, API proxy and optional AI/market-provider settings remain unchanged.

From `frontend`:

```powershell
npm run dev
```

## Validation

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest -q
# frontend
.\node_modules\.bin\tsc.cmd --noEmit
.\node_modules\.bin\eslint.cmd src/components/LearningCatalog.tsx src/components/TradingExercise.tsx src/components/TrainingExerciseBanner.tsx src/app/training src/app/backtest/page.tsx src/app/replay/page.tsx src/lib/learning.ts
npm run build
```

Backend tests use disposable SQLite databases. They cover approved categories, unrelated-course exclusion, preserved legacy records, idempotent seeding, three/two-module curricula, cross-user privacy, completion/resume, bookmarks, quizzes, coach context, dataset listing, exactly-one-candle replay stepping and next-open execution of close-based exits. PostgreSQL execution and live AI model responses are not exercised locally. This setup creates no new users beyond the dedicated browser QA account from the initial implementation.

Current backend result: **40 tests passed**. The upload/engine integration test imports an explicitly synthetic TEST fixture into an isolated in-memory database, checks duplicate handling, executes the real backtest engine and asserts that a missing training dataset never calls the provider fallback. This fixture is not seeded into the application or represented as historical market performance.

Browser checks confirmed fourteen trading-only courses, zero results for a Python search, specialized section filters, retained original lesson completion and the empty-dataset state with external reading links. The local development database has no stored historical candles; import permitted real history before running course exercises. No historical return claims are made from the empty local database.
