from ..classifier import HeuristicClassifier, get_classifier as _real
from . import agents, cost, loop_control, safety, triage

_ALL = {**triage.RULES, **safety.RULES, **loop_control.RULES, **cost.RULES, **agents.RULES}


def get_usecase_classifier():
    """Real Jev when TYPESAFE_API_KEY is set, else an offline heuristic with all use-case rules."""
    c = _real()
    return HeuristicClassifier(_ALL) if isinstance(c, HeuristicClassifier) else c
