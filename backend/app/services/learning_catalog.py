"""Curated content, no scraping or third-party API credentials."""

import re

from sqlalchemy import select

from app.models.curriculum import Course, Lesson, Module
from app.models.learning import CourseInfo, LessonInfo

CATEGORIES = [
    "AI Trading Fundamentals",
    "Technical Analysis for Trading",
    "Risk Management and Position Sizing",
    "Trading Strategy Development",
    "Trading Replay and Simulation",
    "AI Trading Strategy Backtesting",
    "Quantitative and Algorithmic Trading",
    "Trading Psychology and Behavioral Analytics",
    "Portfolio and Market Risk Analysis",
    "AI Model Evaluation for Trading",
]
LEGACY_CATEGORIES = {
    "Beginner Trading": CATEGORIES[3],
    "Technical Analysis": CATEGORIES[1],
    "Candlestick Patterns": CATEGORIES[1],
    "Risk Management": CATEGORIES[2],
    "Algorithmic Trading": CATEGORIES[3],
    "Trading Psychology": CATEGORIES[7],
    "Backtesting": CATEGORIES[5],
}
RESOURCES = {
    "ai-fundamentals": (
        "QuantConnect",
        "https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/key-concepts",
    ),
    "model-validation": (
        "QuantConnect",
        "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/research-guide",
    ),
    "backtesting": ("Backtrader", "https://www.backtrader.com/docu/quickstart/quickstart/"),
    "quant-trading": ("QuantConnect", "https://www.quantconnect.com/docs/v2/writing-algorithms"),
}


def validate_media(data):
    video = data.get("video_id")
    if video and not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        raise ValueError("Only a YouTube video ID is accepted")
    return data


async def seed_learning(db):
    # Retire general programming without deleting enrollments, bookmarks or progress.
    retired = await db.get(Course, "python-foundations")
    if retired:
        retired.is_published = False
    for info in (await db.scalars(select(CourseInfo))).all():
        data = dict(info.metadata_json)
        if data.get("category") in LEGACY_CATEGORIES:
            data["category"] = LEGACY_CATEGORIES[data["category"]]
            info.metadata_json = data
    # Only known original trading courses receive default metadata.
    for course in (await db.scalars(select(Course))).all():
        if course.id in {"c1", "c2"} and not await db.get(CourseInfo, course.id):
            db.add(
                CourseInfo(
                    course_id=course.id,
                    metadata_json={
                        "category": CATEGORIES[2],
                        "provider": "AITrade",
                        "instructor": "AITrade curriculum",
                        "license": "AITrade original material — repository terms apply",
                        "source_url": "",
                        "language": "English",
                        "subtitles": "Not applicable (reading)",
                        "objectives": [
                            "Plan exits before entering a trade",
                            "Calculate risk before using the replay workspace",
                        ],
                        "prerequisites": "Basic familiarity with orders and prices",
                    },
                )
            )
    additions = [
        (
            "market-basics",
            "Trading Foundations",
            "Beginner Trading",
            "Identify order types and the cost of execution.",
            (
                "A market order prioritizes execution, but does not guarantee a price. A "
                "limit order controls price, but may never fill. Bid-ask spreads and "
                "commissions reduce returns. Practice comparing both order types in the "
                "Replay workspace before taking risk."
            ),
            "Which order controls the execution price?",
            ["Market order", "Limit order"],
            1,
        ),
        (
            "technical-basics",
            "Support, Resistance & Trends",
            "Technical Analysis",
            "Read market structure without treating patterns as guarantees.",
            (
                "A trend describes a sequence of swings. Higher highs and higher lows "
                "describe an uptrend. Support and resistance are areas where price "
                "previously attracted activity, not guaranteed turning points. Write down an"
                " invalidation level before testing a setup."
            ),
            "Does historical support guarantee a bounce?",
            ["Yes", "No"],
            1,
        ),
        (
            "candles",
            "Reading Candlesticks",
            "Candlestick Patterns",
            "Understand open, high, low and close.",
            (
                "A candle summarizes an interval: open, high, low and close. Its body spans "
                "open to close; wicks show the extremes. A long wick may show rejection, but"
                " needs context. Compare the same session on different timeframes in Replay."
            ),
            "What does the candle body span?",
            ["High to low", "Open to close"],
            1,
        ),
        (
            "psychology",
            "A Disciplined Trading Routine",
            "Trading Psychology",
            "Build a repeatable process and review decisions.",
            (
                "After a loss, pause and compare the trade with your written rules. "
                "Increasing size merely to recover a loss changes your risk without "
                "improving your evidence. Record your emotional state and the reason for "
                "each decision in the Journal. Review adherence separately from profit."
            ),
            "What is useful after a loss?",
            ["Immediately double position size", "Review adherence to your written rules"],
            1,
        ),
        (
            "algorithms",
            "From Rule to Trading Algorithm",
            "Algorithmic Trading",
            "Translate a trading idea into testable rules.",
            (
                "An algorithm needs explicit entry, exit and sizing rules. Use only "
                "information available at decision time. A signal calculated from today's "
                "closing price cannot trade at that same close without a realistic execution"
                " assumption. Include fees and slippage in every experiment."
            ),
            "Which input causes look-ahead bias?",
            ["A future closing price", "Yesterday's closing price"],
            0,
        ),
        (
            "backtesting",
            "An Honest Backtest",
            "Backtesting",
            "Separate research from evaluation.",
            (
                "Reserve an unseen time period for evaluation. Repeatedly choosing "
                "parameters using that period turns it into training data. Compare against a"
                " simple benchmark, include transaction costs, inspect drawdown and test "
                "across different regimes. Past simulated returns do not establish future "
                "performance."
            ),
            "When should you use the held-out evaluation period?",
            ["For every parameter choice", "After selecting rules using training data"],
            1,
        ),
    ]
    additions += [
        (
            "ai-fundamentals",
            "AI-Assisted Trading: From Prediction to Decision",
            CATEGORIES[0],
            "Evaluate model signals within a trading workflow with explicit risk limits.",
            "A prediction is an estimate, not an order. Define the forecast horizon, the timestamp at which inputs become available, and the decision rule separately. For example, a next-session direction forecast can be compared with a no-model baseline before it controls any simulated position.\n\nRecord the signal, intended entry, invalidation and size in your journal before revealing future candles. Reject a signal when risk limits fail, even when model confidence is high. Compare net returns after costs and drawdown; accuracy alone does not establish a useful trading strategy. AITrade's SMA exercise is a transparent rule-based baseline, not an AI model.",
            "Does high prediction accuracy establish a profitable trading strategy?",
            ["Yes", "No, costs and risk still matter"],
            1,
        ),
        (
            "replay-training",
            "Candle-by-Candle Trading Replay",
            CATEGORIES[4],
            "Practice entries, protective exits and decision review on historical candles.",
            "Choose a stored stock dataset and hide future price movement. Pause before the next candle, write an entry rule and an invalidation price, and calculate position size. A hypothetical $100 risk budget with a $2 stop distance allows 50 shares before costs.\n\nAdvance one candle at a time. Use simulated market, stop or limit orders in Replay; these do not route to a broker. Record why you entered and compare the actual simulated fill with the planned price. Reveal later candles only after recording the decision. Assess rule adherence separately from P&L. A single successful replay does not validate a strategy.",
            "When should you record a replay decision?",
            ["Before revealing future candles", "After seeing the outcome"],
            0,
        ),
        (
            "position-sizing",
            "Position Sizing and Drawdown Control",
            CATEGORIES[2],
            "Translate a defined loss budget and stop distance into a stock position.",
            "Position size equals the loss budget divided by the entry-to-stop distance. With $10,000 equity, a hypothetical 0.5% risk budget is $50. An entry of $100 and stop of $98 gives 25 shares before costs. Also cap notional exposure: a stop can gap and does not guarantee the planned loss.\n\nIn Replay, compare a fixed share count with the risk-based share count. Record the intended exit before entering. After several simulated trades, inspect peak-to-trough drawdown and decide whether your risk limits were followed. Do not increase risk solely to recover losses.",
            "With a $50 budget and $2 stop distance, what is the pre-cost size?",
            ["25 shares", "100 shares"],
            0,
        ),
        (
            "quant-trading",
            "Quantitative Trading Signals and Baselines",
            CATEGORIES[6],
            "Test a measurable stock signal against a simple baseline.",
            "State a hypothesis before selecting parameters: for example, a moving-average crossover might capture persistent trends. Specify the lookback periods, signal timestamp, entry delay and exit rule. Run the same historical window and execution assumptions for each comparison.\n\nCompare changes in trade count, drawdown and net return. Many parameter trials create selection bias; record every experiment rather than reporting only the winner. A rule-based baseline helps assess whether a later AI model adds value. Serially correlated market observations cannot be treated as independent shuffled examples.",
            "What should remain consistent when comparing two strategy versions?",
            ["Dataset and execution assumptions", "Only the winning trades"],
            0,
        ),
        (
            "portfolio-risk",
            "Portfolio Exposure and Market Risk",
            CATEGORIES[8],
            "Evaluate concentration, correlated positions and portfolio drawdown.",
            "Two stock positions can share the same underlying market or sector risk. Counting tickers is not enough to establish diversification. Track each position's notional value as a fraction of portfolio equity and consider how simultaneous adverse moves affect total loss.\n\nUse the existing risk overview to inspect exposure and limits. In your journal, stress a hypothetical 5% simultaneous drop in correlated holdings, include a gap beyond planned stops, and compare that loss with your drawdown tolerance. This is a scenario exercise, not a forecast. Review concentration before adding another similarly exposed trade.",
            "Do different ticker symbols guarantee diversification?",
            ["Yes", "No"],
            1,
        ),
        (
            "model-validation",
            "Evaluating AI Trading Models Without Leakage",
            CATEGORIES[9],
            "Use chronological validation, walk-forward tests and realistic trading costs.",
            "Split stock observations chronologically into training, validation and held-out evaluation periods. Compute each feature only from information available at the signal timestamp. Fit preprocessing on training data only; ensure that a forward return label does not overlap across a split boundary.\n\nSelect model settings using training and validation periods, then evaluate once on the held-out period. For walk-forward testing, train on past data and move the evaluation window forward. Compare a model with a simple trading baseline after execution costs, and report drawdown and trade count as well as prediction metrics. AITrade's existing Backtest engine evaluates strategy rules; it does not train a machine-learning model.",
            "Which evaluation is appropriate for a trading model?",
            ["Chronological out-of-sample testing", "Tuning on future evaluation returns"],
            0,
        ),
    ]
    additions = [
        (key, title, LEGACY_CATEGORIES.get(category, category), *rest)
        for key, title, category, *rest in additions
    ]
    for key, title, category, description, notes, question, options, answer in additions:
        if await db.get(Course, key):
            continue
        db.add(
            Course(
                id=key,
                title=title,
                description=description,
                difficulty="beginner",
                order_index=10 + CATEGORIES.index(category),
            )
        )
        await db.flush()
        db.add(Module(id=f"{key}-module", course_id=key, title="Core concepts", order_index=1))
        await db.flush()
        db.add(
            Lesson(
                id=f"{key}-lesson",
                module_id=f"{key}-module",
                title=title,
                content_markdown=notes,
                order_index=1,
            )
        )
        await db.flush()
        db.add(
            CourseInfo(
                course_id=key,
                metadata_json={
                    "category": category,
                    "provider": "AITrade",
                    "instructor": "AITrade curriculum",
                    "license": "CC BY 4.0 (new lesson text)",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_url": "",
                    "language": "English",
                    "subtitles": "Not applicable (reading)",
                    "objectives": [
                        description,
                        "Apply the concept in the existing practice workspace",
                    ],
                    "prerequisites": "None",
                },
            )
        )
        db.add(
            LessonInfo(
                lesson_id=f"{key}-lesson",
                metadata_json={
                    "duration_seconds": 180,
                    "kind": "reading",
                    "quiz": [{"question": question, "options": options, "answer": answer}],
                    "takeaways": [description],
                },
            )
        )
    await db.flush()
    for lesson in (await db.scalars(select(Lesson))).all():
        if not await db.get(LessonInfo, lesson.id):
            db.add(
                LessonInfo(
                    lesson_id=lesson.id,
                    metadata_json={
                        "kind": "reading",
                        "duration_seconds": 300,
                        "takeaways": ["Define risk and invalidation before entering a trade"],
                        "quiz": [
                            {
                                "question": "What should you define before entering a trade?",
                                "options": ["An exit and risk plan", "A guaranteed profit"],
                                "answer": 0,
                            }
                        ],
                    },
                )
            )
    # Keep original IDs/content; supply the missing authored modules idempotently.
    extra_modules = [
        (
            "c1",
            "c1-trailing",
            "Trailing Stops in Replay",
            "Protecting a Simulated Trend",
            "A trailing stop follows favorable price movement without moving away to accept a larger loss. In Replay, write the update rule before advancing a candle. Compare a fixed stop with a trailing level and journal why each exit happened.",
        ),
        (
            "c1",
            "c1-volatility",
            "Volatility and Stop Placement",
            "Stop Distance and Position Size",
            "A wider stop increases loss per share at a fixed position size. Reduce share count when stop distance grows if the loss budget is unchanged. Gaps and slippage can exceed the intended stop loss. Compare both sizes in a historical replay.",
        ),
        (
            "c2",
            "c2-validation",
            "Validating Reward-to-Risk Setups",
            "Expectancy After Trading Costs",
            "A 2:1 reward-to-risk target is not a guarantee of profitability. Expected outcome depends on win rate, realized wins and losses, fees and slippage. Test a written entry/exit rule with the existing Backtest engine and compare its actual metrics with the target ratio.",
        ),
    ]
    for course_id, module_id, title, lesson_title, notes in extra_modules:
        if await db.get(Course, course_id) and not await db.get(Module, module_id):
            db.add(
                Module(
                    id=module_id,
                    course_id=course_id,
                    title=title,
                    order_index=2 if module_id != "c1-volatility" else 3,
                )
            )
            await db.flush()
            db.add(
                Lesson(
                    id=module_id + "-lesson",
                    module_id=module_id,
                    title=lesson_title,
                    content_markdown=notes,
                    order_index=1,
                )
            )
    await db.flush()
    for info in (await db.scalars(select(CourseInfo))).all():
        if info.course_id == "python-foundations":
            continue
        data = dict(info.metadata_json)
        category = data.get("category")
        if category not in CATEGORIES:
            continue
        mode = (
            "backtest"
            if category in {CATEGORIES[3], CATEGORIES[5], CATEGORIES[6], CATEGORIES[9]}
            or info.course_id == "c2"
            else "replay"
        )
        data["practice_mode"] = mode
        if info.course_id in RESOURCES:
            provider, url = RESOURCES[info.course_id]
            data["resources"] = [
                {
                    "provider": provider,
                    "url": url,
                    "title": "Official trading reference",
                    "usage": "External reading only; provider terms apply. No redistribution license asserted.",
                }
            ]
            data["source_url"] = url
        info.metadata_json = data
    for lesson in (await db.scalars(select(Lesson))).all():
        if not await db.get(LessonInfo, lesson.id):
            db.add(
                LessonInfo(
                    lesson_id=lesson.id,
                    metadata_json={
                        "kind": "reading",
                        "duration_seconds": 180,
                        "takeaways": ["Record risk rules before testing the trade"],
                        "quiz": [
                            {
                                "question": "Should simulated results be treated as guaranteed future profits?",
                                "options": ["Yes", "No"],
                                "answer": 1,
                            }
                        ],
                    },
                )
            )
    await db.commit()
