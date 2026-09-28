"""Agent-domain use cases: browser next-step, trading gate (PAPER ONLY), LLM-as-judge."""
from ..classifier import Choice, Classifier, Noul, Score
from ._rules import kw, overlap, pick

RULES = {
    "b_step": pick({"click": (r"button|link|submit|login",), "type": (r"input|field|search box|form",),
                    "scroll": (r"more results|below|footer",), "extract": (r"price|table|results list|data",),
                    "done": (r"order confirmed|thank you|success",)}, "scroll"),
    "x_hype": kw(r"guaranteed|moon|100x|insider|pump|can'?t lose|urgent buy"),
    "j_quality": lambda s, q: min(0.95, 0.15 + 0.1 * len(s.split()) / 5) if len(s.split()) < 25 else 0.85,
}


def browser_next_step(clf: Classifier, page_summary: str) -> str:
    return clf.classify(page_summary, {"b_step": Choice("Next browser action", {
        "click": "press a button/link", "type": "fill an input", "scroll": "reveal more", "extract": "read data", "done": "goal reached"})}).top_choice("b_step")[0]


def trade_gate(clf: Classifier, signal_text: str, size_usd: float, auto_limit: float = 100.0) -> str:
    """Decide auto / human / reject for a *paper* trade. No orders are placed; not financial advice."""
    hype = clf.classify(signal_text, {"x_hype": Noul("The signal is hype, manipulation, or unverifiable claims")}).nouls["x_hype"]
    if hype > 0.7:
        return "reject"
    return "auto" if size_usd <= auto_limit and hype < 0.3 else "human"


def judge_answer(clf: Classifier, question: str, answer: str) -> float:
    """LLM-as-judge replacement for cheap large-scale evals (0 bad .. 1 good)."""
    return clf.classify(f"Q: {question}\nA: {answer}", {"j_quality": Score("Answer quality", ("bad", "ok", "good"))}).scores["j_quality"]
