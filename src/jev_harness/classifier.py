"""System One style classifier: state + questions -> typed probabilities.

Backends:
  * TypeSafeBackend  - real Jev via `langchain-typesafe` (needs TYPESAFE_API_KEY)
  * HeuristicClassifier - offline keyword stand-in so the POC runs anywhere
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Mapping, Protocol


@dataclass(frozen=True)
class Noul:
    """Yes/no question -> probability the statement is true."""
    instructions: str


@dataclass(frozen=True)
class Choice:
    """Pick one of several options -> probability per option."""
    instructions: str
    options: Mapping[str, str]  # option name -> description


@dataclass
class Result:
    nouls: dict[str, float] = field(default_factory=dict)
    choices: dict[str, dict[str, float]] = field(default_factory=dict)

    def top_choice(self, name: str) -> tuple[str, float]:
        probs = self.choices[name]
        key = max(probs, key=probs.get)
        return key, probs[key]


class Classifier(Protocol):
    def classify(self, state: str, questions: Mapping[str, Noul | Choice]) -> Result: ...


_RISKY = re.compile(
    r"\brm\s+-rf\b|\bsudo\b|\bmkfs\b|\bdd\s+if=|curl[^|]*\|\s*(ba)?sh|\bchmod\s+-R\s+777\b|"
    r"\bgit\s+push\s+.*--force\b|drop\s+table|/etc/(passwd|shadow)|\.ssh/|>\s*/dev/sd",
    re.I,
)
_HARD = re.compile(r"architect|design|migrat|security|debug|race condition|trade-?off|high-stakes", re.I)


class HeuristicClassifier:
    """Deterministic stand-in. Answers questions by keying off their names:
    `risky*` -> shell-danger regex, `complex*`/route choice -> difficulty keywords."""

    def classify(self, state: str, questions: Mapping[str, Noul | Choice]) -> Result:
        res = Result()
        for name, q in questions.items():
            if isinstance(q, Noul):
                hit = bool(_RISKY.search(state)) if "risk" in name or "danger" in name else bool(_HARD.search(state))
                res.nouls[name] = 0.98 if hit else 0.03
            else:
                hard = bool(_HARD.search(state)) or len(state) > 400
                opts = list(q.options)
                probs = {o: 0.05 for o in opts}
                probs[opts[-1] if hard else opts[0]] = 0.9
                total = sum(probs.values())
                res.choices[name] = {o: p / total for o, p in probs.items()}
        return res


class TypeSafeBackend:
    def __init__(self) -> None:
        from langchain_typesafe import Noul as TNoul, TypeSafeClassifier  # lazy
        self._c = TypeSafeClassifier()
        self._TNoul = TNoul

    def classify(self, state, questions):
        try:
            from langchain_typesafe import Choice as TChoice
        except ImportError:  # pragma: no cover
            TChoice = None
        qs = {}
        for name, q in questions.items():
            if isinstance(q, Noul):
                qs[name] = self._TNoul(instructions=q.instructions)
            else:
                if TChoice is None:
                    raise RuntimeError("installed langchain-typesafe lacks Choice")
                qs[name] = TChoice(instructions=q.instructions, options=dict(q.options))
        r = self._c.invoke({"state": state, "questions": qs})
        out = Result()
        for name, q in questions.items():
            if isinstance(q, Noul):
                out.nouls[name] = r.nouls[name].noul
            else:
                out.choices[name] = dict(r.choices[name].probabilities)
        return out


def get_classifier() -> Classifier:
    """Real Jev if TYPESAFE_API_KEY + package available, else offline heuristic."""
    if os.environ.get("TYPESAFE_API_KEY"):
        try:
            return TypeSafeBackend()
        except ImportError:
            print("[jev-harness] langchain-typesafe not installed; using heuristic backend")
    return HeuristicClassifier()
