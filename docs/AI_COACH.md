# Local open-weight AI Coach

AITrade uses Ollama's backend HTTP API and Qwen3 4B by default. Anthropic and paid-provider keys are not used. There are no canned fallback answers: inference failures return clear retryable errors.

## Model and hardware

The inspected machine has 32 GB RAM and an NVIDIA RTX 4050 Laptop GPU with 6 GB VRAM. The selected quantized `qwen3:4b-thinking` model is about 2.5 GB. Ollama detected this GPU through its Vulkan backend. GPU memory use also includes the context and inference buffers, so memory use exceeds the weights' file size. The model and server URL remain configurable.

The generic `qwen3:4b` tag currently resolves to Qwen3-4B-Thinking-2507, a thinking-only model. The explicit `qwen3:4b-thinking` tag avoids implying it is the Instruct variant. The backend reads model capabilities, enables the supported thinking mode, allows a 2,048-token generation budget, and returns only the final `message.content`. The model's separate reasoning field is never returned or persisted. Defensive marker filtering also rejects unfinished drafting output. Instruct-only alternatives use a smaller non-thinking generation budget when their capabilities say thinking is unsupported.

[Qwen3 4B's Ollama model card](https://ollama.com/library/qwen3:4b-thinking) lists Apache License 2.0 for the model. This permits commercial use subject to the license obligations. We describe the model as open-weight, without making a blanket claim about OSI approval of model weights. Other model tags require their own license review. A smaller supported alternative is [`qwen3:1.7b`](https://ollama.com/library/qwen3:1.7b).

## Install and run

Install Ollama from the [official Windows download](https://ollama.com/download/windows). It installs under the current user and normally starts its local server automatically. For a portable installation, the official Windows archive and instructions are on the [Windows documentation page](https://docs.ollama.com/windows).

Standard installation:

```powershell
ollama pull qwen3:4b-thinking
ollama list
# If the local server is not already running:
ollama serve
```

For this workspace, a portable Ollama 0.40.12 runtime was installed outside the repository at `%LOCALAPPDATA%\AITrade\ollama`. Its executable's Authenticode signature was verified as valid, signed by Ollama Inc. Model weights are stored in `%LOCALAPPDATA%\AITrade\models`. This runtime uses the official CPU/Vulkan libraries, so it does not require the much larger CUDA archive components. No executable or model weights are committed to Git.

To restart that portable runtime and pull/resume the configured model:

```powershell
pwsh -File E:\AI_Trading\scripts\Start-AICoach.ps1
```

The helper also supports an Ollama installation on PATH. The model pull verifies the content digests before installation. Download time depends on connectivity; a partially downloaded model cannot answer chat requests yet.

Backend settings, in `backend/.env` or the server environment:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b-thinking
OLLAMA_TIMEOUT_SECONDS=180
COACH_REQUESTS_PER_MINUTE=6
```

Defaults already match these values. Keep the existing `DATABASE_URL`, authentication secrets and market-data settings. No `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is needed.

Start the application using the existing environments:

```powershell
cd E:\AI_Trading\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.core.db_init
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# A second terminal:
cd E:\AI_Trading\frontend
npm install
npm run dev
```

The SQLite driver already used by local development/tests is now declared in requirements. HTTPX and React Markdown were already dependencies; no model SDK or new frontend dependency is required.

The browser calls the application API (`/api/ai-coach/chat` through the existing Next.js proxy). It never calls the inference server directly. Ollama remains bound to loopback, without opening a LAN/public inference port. For a containerized backend, configure a privately reachable `OLLAMA_BASE_URL`; Compose examples use `host.docker.internal`. Connectivity from a container depends on the host/network configuration. Do not publish the inference port to solve connectivity or place inference credentials in frontend variables.

## API and data access

FastAPI routes, without the frontend proxy prefix:

- `POST /ai-coach/chat`: `message`, optional `conversationId`, `courseId`, `lessonId` and bounded `simulationContext`.
- `GET /ai-coach/conversations?lesson_id=...`: this user's latest 30 conversation titles in the lesson; without a lesson, general conversations.
- `GET /ai-coach/conversations/{id}`: up to 100 recent visible messages, oldest first.
- `DELETE /ai-coach/conversations/{id}`: clear that user's selected conversation and its messages.

All routes require the existing JWT. Looking up or clearing another user's conversation returns 404. Lesson questions require enrollment and a published, approved trading course. Course, module and lecture titles plus authorized notes are loaded on the server, not trusted from the browser. A lesson ID that does not belong to the supplied course is rejected. Old/retired lessons cannot be accessed through a saved conversation.

Conversations and messages use the existing SQLAlchemy database in `ai_conversations` and `ai_messages`, with foreign keys and indexes. Startup creates the additive tables idempotently. For reviewed PostgreSQL deployments, apply `backend/migrations/002_ai_coach.sql` after the existing user/curriculum schema. SQLite uses the same model definitions. Supabase RLS does not apply to this architecture; access is enforced by authenticated FastAPI queries.

Only successful turns are saved. No write lock is held while the model generates. User/assistant messages are stored separately. Simulation reference data is stored as a private `reference` message, excluded from visible chat messages and role history. Follow-ups reuse that reference from the conversation rather than silently switching it to a different backtest run. Clearing a conversation removes this reference too.

## Context and behavior

- Training's existing AI Coach button opens the shared chat. The lesson coach uses the same component with server-authorized lesson context.
- Backtest's results include an expandable coach with the run's actual displayed configuration, return, win rate, profit factor, drawdown and trade count. Opening a new run starts a fresh conversation rather than automatically adopting another run's chat. Selecting an older saved chat retains that chat's original context.
- Replay's summary includes conversational coaching using the actual displayed summary metrics and scenario settings. The existing paper-trade review endpoint still retrieves the authenticated user's recorded fills/journal/risk evidence; it now uses the same local inference service.
- Browser-supplied simulation metrics are explicitly labeled as client-supplied, not independently verified. The coach cannot claim to have executed that simulation, fetch private results, train a model, retrieve live prices, run generated code/SQL or place orders. There are no model action tools.
- The system prompt restricts the coach to trading, risk, lessons, simulation, backtesting and model evaluation, with brief redirection for unrelated topics. As with any language model, prompt compliance and factual accuracy are not guaranteed; answers remain educational and require review.
- Markdown handles headings, lists, code and explanations. Formulas use readable plain text/inline code, avoiding unrendered LaTeX. User and assistant text is never executed as HTML or code.

## Chat controls and errors

The interface supports private conversation selection, New Chat, Clear Conversation, Enter to send, Shift+Enter for newlines, loading state, automatic scroll, suggested lesson questions, Copy Response, retry and editing a failed question. Clipboard fallback supports the existing HTTP LAN development UI as well as secure-context clipboard access.

Responses use normal JSON rather than partial token streaming. Stop Generation aborts the browser request; the backend detects disconnect and cancels its upstream inference task. A stopped/failed turn is not inserted into the database. A very late cancellation can race a completed response, so reloading the conversation is authoritative.

The backend checks `/api/tags` before generation and reports a missing model separately from an unavailable server. Timeouts return 504; invalid/failed model responses return 502; an unavailable server/model returns 503. Internal exception text and inference credentials/addresses are not returned. Errors never become fabricated assistant messages or generic tips. A length-limited answer carries an explicit continuation notice.

Questions are limited to 4,000 characters. Contextual simulation data is bounded to 8,000 characters with finite scalar values. The server sends at most ten recent messages within a 10,000-character history budget, bounded lesson/reference context, and a configured inference timeout. One generation per user and one model generation at a time protect the local GPU. The default rate is six model requests per minute per user.

Rate/busy limits are process-local and appropriate to the current single-process development server. Multiple production workers/replicas require shared limits at a gateway or Redis; this implementation does not claim cluster-wide enforcement. There is no open proxy, user-selected model URL or automatic model pull on a chat request.

## Verification

```powershell
cd E:\AI_Trading\backend
.\.venv\Scripts\python.exe -m pytest -q

cd E:\AI_Trading\frontend
.\node_modules\.bin\tsc.cmd --noEmit
.\node_modules\.bin\eslint.cmd src/components/CoachChat.tsx src/app/training src/app/backtest/page.tsx src/app/replay/page.tsx src/lib/api.ts
npm run build
```

Automated tests cover normal chat protocol, persisted follow-ups, lesson access/context, simulation references, another user's conversation, whitespace/oversized messages, rate limiting, clear, cancellation, unavailable servers, missing models, timeouts and malformed/empty inference responses. Mock transport responses test protocol/failure behavior; they are not evidence of real local model inference. Local inference and browser verification are reported separately below. PostgreSQL migration execution is not exercised by the SQLite test suite.

Run the live-model verification separately:

```powershell
cd E:\AI_Trading\backend
.\.venv\Scripts\python.exe verify_coach_live.py
```

This uses real Ollama inference with a disposable in-memory application database, never mocked answers and never a production user's conversation. It checks a normal trading question, a persisted follow-up calculation and an enrolled lesson question. Generated final answers are saved to `docs/coach-live-verification.json` for inspection. Private drafting output is not included.


## Verified results — 29 October 2026

- Backend: 52 tests passed, including private ownership, authorized lesson context, persistence, clear, cancellation, rate limiting and inference failures.
- Frontend: token-refresh regression test passed; scoped ESLint, TypeScript and optimized production build passed. Concurrent expired requests share one refresh and retain multipart bodies.
- Real Ollama inference: normal trading question, persisted follow-up, lesson question and unrelated-topic redirection. Inspect `coach-live-verification.json`; the first three measured requests took approximately 21–65 seconds on this machine. These timings are observations, not a latency guarantee.
- Browser: a real enrolled lesson answer rendered Markdown bullets; Enter submitted; Stop cancelled an unfinished turn; Retry produced the correct 100 / 5 = 20 whole shares calculation; Copy displayed its success notice. Reload restored the successful private conversation.
- Training, Replay, Backtest and Dashboard routes returned HTTP 200. Existing simulation and learning regression tests passed. PostgreSQL migration execution was not tested against a running PostgreSQL server.

Next.js API rewrites explicitly allow 210 seconds because its default 30-second proxy timeout can interrupt local generation. The browser chat timeout is also 210 seconds and the inference timeout defaults to 180 seconds. History loading and inference remain separate operations.

The small local model can still make factual or arithmetic mistakes, add unrequested examples, or ignore formatting preferences. Successful inference does not establish answer accuracy; users must verify explanations, calculations and simulation interpretations. The coach has no order-placement or code-execution tools.

### Main implementation files

- `backend/app/services/coach_service.py`: local inference, capability handling, final-answer filtering and limits.
- `backend/app/routers/ai_coach.py`, `backend/app/models/ai_chat.py`, `backend/migrations/002_ai_coach.sql`: authenticated private conversations and bounded lesson/simulation references.
- `frontend/src/components/CoachChat.tsx` and `coach-chat.css`: reusable persistent chat interface used in Training, lesson players, Replay and Backtest.
- `frontend/src/lib/api.ts`, `frontend/next.config.ts`: cancellation, long inference timeouts and concurrent token-refresh handling.
- `scripts/Start-AICoach.ps1`: restart the local runtime after reboot. Start the existing backend and frontend separately.


## Local server startup recovery

If the coach reports that it cannot reach the local model server, start the existing runtime with `pwsh -File E:\AI_Trading\scripts\Start-AICoach.ps1`, then use Retry last question. The helper checks installed models first and does not contact the model registry when the configured model is already installed.

This Windows workspace now sets `OLLAMA_AUTO_START=true` in its ignored backend `.env`. On backend startup, it checks the local HTTP loopback endpoint and starts an already installed Ollama if needed, including the portable model directory. It does not install software, pull models, expose a network listener or start a remote server. The default remains false for other deployments. Startup logs go to `backend/logs/ollama-startup.log`. The runtime is shared and remains available when the backend exits. If you deliberately stop Ollama while the backend is running, run the helper again or restart the backend.


Recovery verified on 29 October 2026: Ollama had no listener on port 11434 while the application was running. Starting the existing portable runtime restored the connection without reinstalling the model. A real authenticated Training-page question returned a Qwen reply and was saved to conversation history. All 56 backend tests passed, including opt-in/loopback startup, reusing an existing server and portable model-directory selection. The startup probe also succeeded against the actual running Ollama. Auto-start configuration applies on the next backend restart; the current runtime was started by the helper.
