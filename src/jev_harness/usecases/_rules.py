"""Offline rule helpers used by the heuristic backend (stand-ins for Jev's judgement)."""
import re


def kw(*words: str, base: float = 0.03, per_hit: float = 0.7):
    pats = [re.compile(w, re.I) for w in words]

    def rule(state, q):
        hits = sum(1 for p in pats if p.search(state))
        return min(0.97, base + per_hit * hits)
    return rule


def pick(options: dict[str, tuple[str, ...]], default: str):
    comp = {o: [re.compile(w, re.I) for w in ws] for o, ws in options.items()}

    def rule(state, q):
        probs = {o: 0.04 + sum(1 for p in ps if p.search(state)) for o, ps in comp.items()}
        probs[default] += 0.3
        return probs
    return rule


_STOP = {"this", "that", "with", "from", "have", "what", "does", "about", "into", "your", "will", "the", "and", "for", "useful", "task", "asks", "same", "thing", "relevant", "request", "still", "goal"}


def _tok(t: str) -> set[str]:
    ws = {w[:-1] if w.endswith("s") else w for w in re.findall(r"[a-z0-9']{3,}", t.lower())}
    return {w for w in ws if len(w) >= 4 and w not in _STOP}


def overlap(state, q):
    """Fraction of the question's content words that appear in the state."""
    want = _tok(q.instructions.split(":")[-1])
    if not want:
        return 0.03
    r = len(want & _tok(state)) / len(want)
    return min(0.97, 0.03 + 1.6 * r)
