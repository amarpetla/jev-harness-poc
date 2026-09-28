"""Agent-loop control: done?, stuck?, escalate?, tool prefilter, memory relevance."""
from ..classifier import Classifier, Noul
from ._rules import kw, overlap

RULES = {
    "c_done": kw(r"\bdone\b|completed|finished|all tests pass|deployed"),
    "c_stuck": kw(r"same error|again|still failing|retry|no progress"),
    "c_escalate": kw(r"delete|production|refund|legal|unsure|low confidence|cannot|permission denied"),
    "tool_*": overlap,
    "mem_*": overlap,
}


def is_done(clf: Classifier, goal: str, transcript: str) -> float:
    return clf.classify(f"Goal: {goal}\n{transcript}", {"c_done": Noul(f"The goal is fully achieved: {goal}")}).nouls["c_done"]


def detect_stuck(clf: Classifier, actions: list[str]) -> bool:
    """Hard rule (same action 3x in a row) OR classifier says no progress."""
    if len(actions) >= 3 and len(set(actions[-3:])) == 1:
        return True
    return clf.classify("\n".join(actions[-6:]), {"c_stuck": Noul("The agent is repeating itself or making no progress")}).nouls["c_stuck"] > 0.6


def should_escalate(clf: Classifier, context: str) -> float:
    return clf.classify(context, {"c_escalate": Noul("A human should review before continuing (high stakes or low confidence)")}).nouls["c_escalate"]


def prefilter_tools(clf: Classifier, task: str, tools: dict[str, str], k: int = 3) -> list[str]:
    """Show the LLM only the k most relevant of many tools. One call, one Noul per tool."""
    qs = {f"tool_{n}": Noul(f"{n}: {d}. Useful for the task") for n, d in tools.items()}
    r = clf.classify(task, qs).nouls
    return sorted(tools, key=lambda n: -r[f"tool_{n}"])[:k]


def relevant_memories(clf: Classifier, query: str, memories: list[str], threshold: float = 0.3) -> list[str]:
    qs = {f"mem_{i}": Noul(f"Relevant to the request: {m}") for i, m in enumerate(memories)}
    r = clf.classify(query, qs).nouls
    return [m for i, m in enumerate(memories) if r[f"mem_{i}"] >= threshold]
