"""Cost/perf use cases: semantic cache, needs-retrieval, context compression."""
from ..classifier import Classifier, Noul
from ._rules import kw, overlap

RULES = {
    "k_retrieval": kw(r"latest|today|current|price|policy|docs?|our |company|internal|this repo", r"\bwho\b|\bwhen\b|how much"),
    "cache_*": overlap,
    "ctx_*": overlap,
}


def cache_lookup(clf: Classifier, query: str, cached: list[str], threshold: float = 0.6) -> int | None:
    qs = {f"cache_{i}": Noul(f"Asks for the same thing as: {c}") for i, c in enumerate(cached)}
    r = clf.classify(query, qs).nouls
    best = max(range(len(cached)), key=lambda i: r[f"cache_{i}"], default=None)
    return best if best is not None and r[f"cache_{best}"] >= threshold else None


def needs_retrieval(clf: Classifier, query: str) -> float:
    return clf.classify(query, {"k_retrieval": Noul("Answering requires looking up external or private knowledge")}).nouls["k_retrieval"]


def compress_context(clf: Classifier, goal: str, messages: list[str], keep_last: int = 2, threshold: float = 0.3) -> list[str]:
    head, tail = messages[:-keep_last], messages[-keep_last:]
    kept = []
    for i, m in enumerate(head):
        p = clf.classify(m, {f"ctx_{i}": Noul(f"Still relevant to the goal: {goal}")}).nouls[f"ctx_{i}"]
        if p >= threshold:
            kept.append(m)
    return kept + tail
