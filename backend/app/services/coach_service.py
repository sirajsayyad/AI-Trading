"""
AI Coach service — Claude API integration for trade critique and Q&A.
"""

from typing import Optional
from app.core.config import get_settings


async def get_trade_critique(
    trades: list[dict],
    session_summary: Optional[dict] = None,
    context: str = "",
) -> str:
    """
    Analyze a set of trades and return coaching feedback.
    Uses Claude API for natural language analysis.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        return _generate_offline_critique(trades, session_summary)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Build trade summary
        trade_summary = _format_trades_for_prompt(trades)

        prompt = f"""You are an educational paper-trading coach analyzing actual recorded trades.
Never invent trades, prices, metrics, or behavior. Do not give a personalized buy/sell signal.
Reference the supplied trade IDs as evidence and say when the sample is insufficient.

## Trades Taken:
{trade_summary}

## Session Context:
{context}

{f"## Session Summary: {session_summary}" if session_summary else ""}

Return these sections: Summary, What went well, What went wrong, Evidence,
Risk violations, Behavioral patterns, One priority improvement, One practice exercise,
Questions for reflection, and Educational disclaimer.

End with: Educational use only. Not financial advice."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text

    except Exception as e:
        return _generate_offline_critique(trades, session_summary)


async def ask_coach(
    question: str,
    trade_context: Optional[list[dict]] = None,
    conversation_history: Optional[list[dict]] = None,
) -> str:
    """
    Free-form Q&A with the AI coach.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        return _generate_offline_answer(question, trade_context)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        system_prompt = """You are an expert trading coach and mentor. 
You help traders improve their skills through clear, actionable advice.
When trades are provided as context, reference specific examples.
Keep responses focused and practical — avoid generic platitudes."""

        messages = []

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        # Build the user message
        user_content = question
        if trade_context:
            trade_summary = _format_trades_for_prompt(trade_context)
            user_content = f"Context — recent trades:\n{trade_summary}\n\nQuestion: {question}"

        messages.append({"role": "user", "content": user_content})

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system_prompt,
            messages=messages,
        )

        return message.content[0].text

    except Exception as e:
        return _generate_offline_answer(question, trade_context)


def _format_trades_for_prompt(trades: list[dict]) -> str:
    """Format trades for inclusion in a prompt."""
    if not trades:
        return "No trades recorded."

    lines = []
    for i, t in enumerate(trades, 1):
        side = t.get("side", "?")
        entry = t.get("entry_price", "?")
        exit_p = t.get("exit_price", "?")
        pnl = t.get("pnl", t.get("net_pnl", "?"))
        duration = t.get("duration_hours", "?")
        symbol = t.get("symbol", "")
        lines.append(
            f"{i}. {side.upper()} {symbol} | Entry: ${entry} → Exit: ${exit_p} | "
            f"P&L: ${pnl} | Duration: {duration}h"
        )

    return "\n".join(lines)


def _generate_offline_critique(trades: list[dict], session_summary: Optional[dict] = None) -> str:
    """Generate basic critique when Claude API is unavailable."""
    if not trades:
        return "No trades to analyze. Consider practicing with the replay module to generate trade history."

    total_pnl = sum(t.get("pnl", t.get("net_pnl", 0)) for t in trades)
    winners = [t for t in trades if t.get("pnl", t.get("net_pnl", 0)) > 0]
    losers = [t for t in trades if t.get("pnl", t.get("net_pnl", 0)) <= 0]
    win_rate = len(winners) / len(trades) if trades else 0

    feedback = f"""## Trade Analysis (Offline Mode)

**Summary:** {len(trades)} trades | {len(winners)} winners, {len(losers)} losers | Win rate: {win_rate:.0%}
**Net P&L:** ${total_pnl:.2f}

### Observations:
"""

    if win_rate < 0.4:
        feedback += "- ⚠️ Low win rate suggests potential issues with entry timing or strategy alignment.\n"
    elif win_rate > 0.7:
        feedback += "- ✅ Strong win rate. Focus on whether risk/reward is also favorable.\n"

    if losers:
        avg_loss = sum(abs(t.get("pnl", t.get("net_pnl", 0))) for t in losers) / len(losers)
        avg_win = sum(t.get("pnl", t.get("net_pnl", 0)) for t in winners) / len(winners) if winners else 0
        if avg_loss > avg_win * 1.5:
            feedback += "- ⚠️ Average loss is significantly larger than average win. Consider tighter stop losses.\n"

    feedback += "\n*Connect an Anthropic API key for detailed AI-powered coaching.*"
    return feedback


def _generate_offline_answer(question: str, trade_context: Optional[list[dict]]) -> str:
    """Generate basic answer when Claude API is unavailable."""
    return (
        f"**Offline Mode** — To get AI-powered coaching responses, "
        f"please configure your ANTHROPIC_API_KEY environment variable.\n\n"
        f"Your question: *{question}*\n\n"
        f"Meanwhile, here are some general tips:\n"
        f"- Always define your risk before entering a trade\n"
        f"- Use stop losses consistently\n"
        f"- Keep a trading journal to track patterns\n"
        f"- Focus on risk-adjusted returns, not just win rate"
    )
