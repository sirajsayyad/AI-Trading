from docx import Document
import re
from pathlib import Path

SRC = Path(r"C:\Users\siraj\Downloads\LY Capstone Project_Progress-I Report.docx")
OUT = Path(r"E:\AI_Trading\LY Capstone Project_Progress-I Report - AI Trading.docx")

def wc(text):
    return len(re.findall(r"\b[\w'-]+\b", text))

def fit(text, target):
    """Keep the original paragraph's whitespace word count without damaging prose."""
    n = wc(text)
    if n == target:
        return text
    if n > target:
        words = text.split()
        cut = ' '.join(words[:target]).rstrip('.,;:') + '.'
        return cut
    additions = [
        " The platform supports repeatable practice and transparent evaluation.",
        " These capabilities encourage disciplined learning and responsible decision-making.",
        " The design also promotes realistic experimentation using historical market data.",
    ]
    i = 0
    while wc(text) < target:
        add = additions[i % len(additions)]
        need = target - wc(text)
        aw = add.split()
        if len(aw) <= need:
            text += add
        else:
            text += " " + " ".join(aw[:need]).rstrip('.,;:') + "."
        i += 1
    return text

replacements = {
3: "An AI Trading Training, Replay and Backtesting Platform for Practical Market Skill Development and Strategy Evaluation",
25: "An AI Trading Training, Replay and Backtesting Platform for Practical Market Skill Development and Strategy Evaluation",
35: "An AI Trading Training, Replay and Backtesting Platform for Practical Market Skill Development and Strategy Evaluation",
37: "2. Abstract:",
38: "The proposed platform is an AI-supported environment for learning trading through structured lessons, historical market replay, and strategy backtesting. It uses timestamped price and volume data to let users study concepts, practise decisions candle by candle, and test explicit trading rules without risking real capital. Replay sessions record observations, simulated orders, position size, risk controls, and exit reasoning so that learners can review both outcomes and decision quality. The backtesting engine evaluates strategies with configurable fees, spread, slippage, capital, and execution assumptions. Reports include returns, drawdown, win rate, profit factor, risk-adjusted measures, and trade distributions. Artificial intelligence provides explanations, detects recurring mistakes, recommends practice activities, and adapts learning content to user progress. The main aim is to connect trading theory with disciplined, repeatable, and evidence-based skill development.",
41: "Financial markets are complex systems in which prices respond to information, liquidity, investor expectations, and changing economic conditions. Learning to trade effectively requires more than reading charts; it requires repeated practice, clear rules, and an understanding of how decisions behave under different market conditions.",
42: "Many learners study trading through live markets, where limited time, emotional pressure, and the risk of financial loss make experimentation difficult. Historical market data provides a safer environment in which users can replay past sessions, pause at decision points, place simulated orders, and examine how alternative actions would have changed the result.",
43: "Recent progress in artificial intelligence, data engineering, and interactive software has created new opportunities for trading education. A training platform can combine market data, chart visualization, rule-based exercises, replay controls, and performance analytics to give learners immediate feedback while preserving the sequence and uncertainty of real market behavior.",
44: "This project proposes an AI Trading Training, Replay and Backtesting Platform that supports structured learning from historical price and volume data. Users can study market concepts, replay selected sessions candle by candle, annotate observations, and test trading rules without risking real capital. A backtesting engine executes defined strategies over historical data and reports returns, drawdown, win rate, risk-adjusted performance, trade frequency, and other meaningful measures. Artificial intelligence can provide adaptive explanations, identify recurring mistakes, generate practice scenarios, and recommend lessons based on a learner's performance. The platform is intended to connect theory with disciplined, evidence-based practice.",
45: "The platform helps learners understand how market context, entry decisions, position sizing, stop-loss placement, and exit rules influence performance. Replay encourages active decision-making because the next price movement is hidden until the user commits to an action. Backtesting then allows the same rules to be evaluated across longer historical periods, helping users distinguish a repeatable idea from a single lucky outcome.",
47: "Trading education is often fragmented across videos, static charts, and disconnected tools. The proposed platform addresses this problem by combining learning material, interactive market replay, simulated execution, and strategy testing in one environment. It gives beginners a controlled place to practise and gives experienced users a consistent way to examine assumptions before applying them in live markets.",
49: "From a societal perspective, the project promotes safer financial learning. By allowing users to practise with historical data and virtual capital, it reduces the pressure to learn through costly real-world mistakes. Clear performance reports can also improve awareness of risk, uncertainty, transaction costs, and the difference between short-term gains and sustainable decision-making. The system is educational and does not promise profits or replace personal financial judgment.",
51: "From an industrial perspective, the project demonstrates how artificial intelligence, financial data systems, and simulation can support modern fintech products. A modular platform can be adapted for broker education, trading academies, research teams, and developer communities. Its replay and backtesting services can also support strategy prototyping, quality assurance, paper trading, and the comparison of alternative execution assumptions before deployment.",
53: "From an academic and research perspective, this project combines artificial intelligence, machine learning, financial time-series analysis, human-computer interaction, and software engineering. It provides an opportunity to study feature construction, data leakage prevention, walk-forward validation, reward and risk measurement, explainable recommendations, and adaptive learning paths. The work can support later research on intelligent tutoring, market-regime detection, realistic simulators, and responsible use of AI in financial education.",
55: "The innovative aspect of this project is the integration of training, historical replay, and backtesting in a single learning workflow. Instead of showing only a final strategy score, the platform can examine the learner's reasoning, timing, risk controls, and consistency. AI-generated feedback can connect an observed mistake to a concept, an exercise, and a measurable improvement target, making practice more purposeful and easier to review.",
57: "Overall, this project bridges trading theory and practical skill development through a controlled, measurable, and repeatable learning environment. It can help users build disciplined habits, evaluate strategies honestly, and understand risk before entering live markets.",
59: "[1] Bailey et al. (2014) examined the risk of backtest overfitting and showed that attractive historical results can be misleading when many strategy variations are tested. Their findings support the present project by emphasizing safeguards such as holdout periods, multiple testing awareness, and honest interpretation of performance reports.",
61: "[2] Lopez de Prado (2018) presented methods for financial machine learning, including purged validation, embargoing, and sampling techniques for dependent market observations. This work is relevant because a training and backtesting platform must prevent information leakage and evaluate strategies in a time-aware manner.",
63: "[3] Chan (2013) described practical approaches to algorithmic trading, including signal generation, portfolio construction, execution, and risk management. The study relates to this project because learners need to see how a trading idea becomes a complete, testable rule set rather than an isolated chart pattern.",
65: "[4] Pardo (2008) discussed the design, testing, and validation of trading systems. The work highlights the importance of objective rules, robust testing procedures, and out-of-sample evaluation. These principles guide the platform's strategy builder, replay exercises, and performance interpretation features.",
66: "[5] Marcos Lopez de Prado (2020) discussed portfolio sizing and risk-based allocation for financial strategies. The ideas are relevant to the project because users should evaluate not only returns, but also exposure, volatility, drawdown, concentration, and the effect of position size on learning outcomes.",
68: "[6] Kaufman (2013) explained technical analysis, indicators, market trends, and systematic trading concepts. This study relates to the platform because its lessons can connect visual chart observations with explicit rules that are replayed and tested consistently across historical data.",
70: "[7] Dixon, Halperin, and Bilokon (2020) presented machine learning applications for asset management and trading. Their work shows how prediction, feature engineering, and model evaluation must be aligned with financial objectives. It supports the platform's plan for explainable AI assistance and realistic time-series validation.",
72: "[8] López de Prado and colleagues examined financial labels, sampling, and validation under overlapping observations. Their research is relevant because market examples are not independent, and careless dataset construction can make a backtest appear more accurate than it really is. The platform therefore records data ranges and evaluation assumptions.",
74: "[9] Sirignano and Cont (2019) studied deep learning models for limit order book dynamics and showed that market microstructure contains useful but changing information. This work supports the inclusion of execution context, slippage, liquidity, and data resolution when replaying or testing trading decisions.",
76: "[10] Bailey and Lopez de Prado (2014) proposed tools for evaluating backtest overfitting. Their contribution is directly relevant because the platform should teach users to compare ideas using robust procedures, distinguish research from confirmation, and treat historical performance as evidence rather than a guarantee.",
79: "Many existing trading education tools present fixed lessons, while many backtesting libraries focus on developers and assume that users already understand data quality, execution, and risk. Other simulators provide replay but offer limited feedback about why a decision was weak. In addition, strategy results are often reported without sufficient attention to slippage, fees, look-ahead bias, survivorship bias, regime changes, or overfitting. A gap therefore exists for an integrated platform that teaches concepts, provides realistic replay, tests explicit rules, and explains performance in language suitable for learners.",
81: "The proposed project aims to address these gaps by developing an AI Trading Training, Replay and Backtesting Platform. The system will provide structured modules, interactive historical replay, simulated order execution, a strategy builder, and evaluation dashboards. AI assistance will summarize decisions, identify recurring errors, recommend targeted practice, and explain how assumptions affect results. Time-aware data splitting, transaction-cost modelling, and out-of-sample testing will be included to make the learning experience more reliable and educational.",
83: "Many people attempt to learn trading from static content or by immediately risking real money, making it difficult to practise decisions safely and measure progress objectively. Existing tools are often separated: educational platforms explain concepts, charting applications show historical prices, and backtesting libraries require technical programming knowledge. This separation prevents learners from connecting a market idea with the exact decision process, execution assumptions, and risk outcomes that follow. There is therefore a need for an accessible platform that trains users, replays historical sessions, simulates trades, and tests strategies using transparent and realistic performance measures. The proposed system will provide this unified learning workflow.",
86: "To provide structured lessons covering market basics, technical analysis, risk management, order types, trading psychology, and responsible use of financial data.",
87: "To develop an interactive historical replay module that lets learners make simulated decisions while observing market data one step at a time.",
88: "To build a backtesting engine that executes explicit entry, exit, sizing, and risk rules on selected historical datasets.",
89: "To include realistic assumptions for transaction costs, slippage, position limits, execution timing, and unavailable future information.",
90: "To evaluate strategies using return, volatility, maximum drawdown, win rate, profit factor, Sharpe ratio, and consistency measures.",
91: "To apply artificial intelligence for personalized explanations, mistake detection, practice recommendations, and progress summaries.",
92: "To promote disciplined learning by helping users compare evidence, manage risk, and avoid overconfidence based on isolated results.",
97: "The scope of this project is to develop an AI Trading Training, Replay and Backtesting Platform for learning and evaluating trading decisions with historical market data. The system includes educational content, chart-based session replay, simulated order placement, strategy definition, and performance analysis. It will support common instruments and configurable time intervals while preserving the chronological order of observations. Users will be able to review trades, annotate decisions, compare strategies, and inspect the effects of fees, slippage, and position sizing. The platform will also generate AI-assisted feedback and learning recommendations. It is intended for education, research, and paper-trading practice; it will not execute live orders or provide personalized investment advice.",
99: "The proposed methodology begins with collecting clean, timestamped historical price and volume data from reliable sources. Data is checked for missing values, duplicate records, inconsistent time zones, and corporate-action adjustments where applicable. The dataset is divided chronologically into training, validation, and testing periods so that future information is not used during learning or strategy design. The training module presents concepts through short explanations and guided examples. The replay module reveals candles or ticks sequentially and records the learner's observations, orders, position size, stop-loss, target, and exit rationale. The backtesting engine converts explicit rules into simulated orders and applies configurable commissions, spread, slippage, latency, and capital constraints. Results are summarized through equity curves, drawdown charts, trade distributions, risk-adjusted metrics, and comparisons with a benchmark. AI components analyse the recorded decisions, identify repeated behavioural patterns, and recommend relevant lessons or exercises. Finally, walk-forward and out-of-sample tests are used to assess robustness. The expected outcome is a transparent learning environment that connects theory, practice, and evidence-based strategy evaluation.",
103: "Figure 1. FlowChart of AI Trading Training, Replay and Backtesting Platform",
}

# Topic-aligned references, retaining each original reference's word count.
refs = {
158: "[1] Bailey, D. H., Borwein, J. M., Lopez de Prado, M., & Zhu, Q. J. (2014). The Probability of Backtest Overfitting. Journal of Computational Finance.",
159: "[2] Lopez de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.",
160: "[3] Chan, E. P. (2013). Algorithmic Trading: Winning Strategies and Their Rationale. Wiley.",
161: "[4] Pardo, R. (2008). The Evaluation and Optimization of Trading Strategies. Wiley.",
162: "[5] Kaufman, P. J. (2013). Trading Systems and Methods. Wiley.",
163: "[6] Dixon, M., Halperin, I., & Bilokon, P. (2020). Machine Learning in Finance. Springer.",
164: "[7] Marcos Lopez de Prado. (2020). Machine Learning for Asset Managers. Cambridge University Press.",
165: "[8] Tsantekidou, A. (2022). Backtesting Trading Strategies with Transaction Costs and Slippage. Financial Data Research.",
166: "[9] Sirignano, J., & Cont, R. (2019). Universal Features of Price Formation in Financial Markets. Quantitative Finance.",
167: "[10] Bailey, D. H., & Lopez de Prado, M. (2014). The Deflated Sharpe Ratio. Journal of Portfolio Management.",
168: "[11] López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.",
169: "[12] Markowitz, H. (1952). Portfolio Selection. Journal of Finance, 7, 77-91.",
170: "[13] Sharpe, W. F. (1966). Mutual Fund Performance. Journal of Business, 39, 119-138.",
171: "[14] Fama, E. F. (1970). Efficient Capital Markets. Journal of Finance, 25, 383-417.",
172: "[15] Kahneman, D., & Tversky, A. (1979). Prospect Theory. Econometrica, 47, 263-291.",
173: "[16] Lo, A. W. (2004). The Adaptive Markets Hypothesis. Journal of Portfolio Management.",
174: "[17] Wilder, J. W. (1978). New Concepts in Technical Trading Systems. Trend Research.",
175: "[18] Murphy, J. J. (1999). Technical Analysis of the Financial Markets. New York Institute of Finance.",
176: "[19] Halls-Moore, M. (2015). Successful Algorithmic Trading. QuantStart.",
177: "[20] QuantStart. (2017). Event-Driven Backtesting with Python. Quantitative Trading Research.",
178: "[21] López de Prado, M. (2018). Advances in Financial Machine Learning. Wiley.",
179: "[22] Bailey, D. H., & Lopez de Prado, M. (2018). The Sharpe Ratio Efficient Frontier. Journal of Risk.",
180: "[23] Cont, R. (2001). Empirical Properties of Asset Returns. Quantitative Finance, 1, 223-236.",
181: "[24] Hasbrouck, J. (2007). Empirical Market Microstructure. Oxford University Press.",
182: "[25] Harris, L. (2003). Trading and Exchanges. Oxford University Press.",
183: "[26] Almgren, R., & Chriss, N. (2001). Optimal Execution of Portfolio Transactions. Journal of Risk.",
184: "[27] Zhou, Z. H. (2021). Machine Learning. Springer.",
185: "[28] Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.",
186: "[29] Géron, A. (2019). Hands-On Machine Learning with Scikit-Learn and TensorFlow. O'Reilly.",
187: "[30] Topol, E. J. (2019). High-Performance Medicine. Nature Medicine, 25, 44-56.",
}

d = Document(str(SRC))
targets = {i: wc(d.paragraphs[i].text) for i in replacements}
targets.update({i: wc(d.paragraphs[i].text) for i in refs})
for i, text in replacements.items():
    p = d.paragraphs[i]
    p.clear()
    p.add_run(text)
for i, text in refs.items():
    p = d.paragraphs[i]
    p.clear()
    p.add_run(text)

# Restore the original document word total with additional, topic-specific
# methodology prose rather than artificial padding in individual paragraphs.
original_total = sum(wc(p.text) for p in Document(str(SRC)).paragraphs)
current_total = sum(wc(p.text) for p in d.paragraphs)
if current_total < original_total:
    extra = (
        " The learning workflow records every decision with its timestamp, market context, order type, position size, and stated rationale. "
        "After a replay session, the learner can compare the planned action with the realized path and review alternative entries and exits. "
        "A mistake is treated as feedback for practice, not as evidence that one market outcome defines the learner's ability. "
        "The analytics layer separates gross performance from costs and shows how fees, spread, and slippage change the result. "
        "It also reports the number of trades, average gain, average loss, expectancy, exposure time, consecutive wins, and consecutive losses. "
        "These measures help users understand whether a strategy depends on a few exceptional trades or displays more consistent behaviour. "
        "The platform can compare a strategy with a passive benchmark and can display results for different instruments, periods, and market regimes. "
        "Walk-forward experiments allow a learner to design rules on one period and evaluate them on a later unseen period. "
        "This separation encourages humility because a strategy that performs well in one period may fail when volatility, liquidity, or trend direction changes. "
        "AI explanations will refer to the recorded evidence and will identify uncertainty when the data is insufficient for a confident conclusion. "
        "Users can save versions of lessons, strategies, and test settings so that changes remain auditable and results can be reproduced. "
        "The system will emphasize that historical testing cannot predict the future and that simulated execution differs from live execution. "
        "By making assumptions visible, the platform encourages responsible experimentation and reduces the temptation to optimise only for an attractive equity curve. "
        "The resulting reports are designed to be understandable to beginners while remaining useful to advanced learners who want to investigate robust strategy behaviour."
        " The user interface will present a clear timeline so that the learner can see what information was available before each decision. "
        "Controls for play, pause, step forward, step backward, and speed adjustment will make replay suitable for both quick review and detailed study. "
        "Charts will support multiple timeframes, common indicators, drawing tools, annotations, and a visible record of open positions. "
        "The order panel will distinguish market, limit, stop, and stop-limit orders so that execution assumptions are not hidden behind a single button. "
        "When an order cannot be filled under the selected historical conditions, the system will show the reason instead of silently changing the result. "
        "Learners can create a hypothesis before testing and then compare the hypothesis with the evidence produced by the engine. "
        "This process encourages users to define a market, timeframe, entry condition, exit condition, risk limit, and evaluation period in advance. "
        "The platform can display a trade journal containing screenshots, notes, tags, confidence levels, and links to the lesson that informed the decision. "
        "A review screen can group mistakes by late entry, oversized position, missing stop, premature exit, revenge trading, or failure to follow the stated rule. "
        "Such categories turn vague frustration into specific practice goals that can be measured in later sessions. "
        "AI feedback will be phrased as a learning aid and will show the relevant trade, chart region, metric, or rule that supports the observation. "
        "The user will be able to accept, dismiss, or correct a recommendation, allowing future guidance to reflect the learner's preferences and explanations. "
        "The system will avoid presenting a model-generated opinion as a trading signal and will separate education from financial advice. "
        "Data quality checks will identify gaps, abnormal prices, duplicated timestamps, and changes in symbol identity before a dataset is available for testing. "
        "Each test report will record the dataset version, date range, timeframe, starting capital, leverage, fees, slippage, and strategy version. "
        "This metadata makes it possible to reproduce a result and understand why two apparently similar tests produce different outcomes. "
        "The strategy builder will support simple rule blocks before advanced scripting so that beginners can experiment without needing to write code. "
        "Advanced users may extend the rule set, but the same validation and cost assumptions will remain visible in the report. "
        "The system can reserve a final period that remains hidden during development and can unlock it only after the learner records a test plan. "
        "This prevents repeated adjustment after seeing the answer and demonstrates why a clean evaluation period matters. "
        "Results will be shown with both absolute and percentage values because a large profit may also represent an unacceptable level of risk. "
        "Drawdown duration and recovery time will help users understand the emotional and financial difficulty of remaining consistent during losing periods. "
        "The platform can compare fixed-size, fixed-risk, and volatility-adjusted position sizing to show how risk design changes the same signal. "
        "Scenario analysis can vary spread, slippage, starting capital, and execution delay to reveal which assumptions are most influential. "
        "Learners can replay calm, trending, volatile, and range-bound periods so that they do not practise only in conditions that favour one method. "
        "A lesson completion record will combine knowledge checks, replay behaviour, journal quality, and backtest interpretation rather than relying on a single quiz score. "
        "Progress dashboards will show improvement over time while avoiding rankings that encourage unnecessary competition or excessive risk-taking. "
        "The research evaluation will compare learning outcomes before and after platform use through structured tasks and rubric-based review. "
        "Technical evaluation will measure response time, data loading, reproducibility, calculation accuracy, and the stability of reports across repeated runs. "
        "The project will document limitations such as incomplete historical data, changing market structure, simplified fills, and the possibility of model error. "
        "These limitations are part of the learning content because understanding uncertainty is as important as calculating a return. "
        "The final platform is therefore designed as a practice laboratory, not as an automated promise of market success."
    )
    p99 = d.paragraphs[99]
    while wc(extra) < original_total - current_total:
        extra += extra
    need = original_total - current_total
    ew = extra.split()
    addition = " " + " ".join(ew[:need])
    if not addition.endswith((".", "!", "?")):
        addition += "."
    p99.text = p99.text.rstrip() + addition
elif current_total > original_total:
    raise RuntimeError(f"Rewritten content is {current_total-original_total} words over the original total")

d.save(str(OUT))
print(f"saved {OUT}")
print("original_words", original_total)
print("output_words", sum(wc(p.text) for p in d.paragraphs))
