"""System One style classifier: state + questions -> typed probabilities.

Backends:
  * TypeSafeBackend  - real Jev via `langchain-typesafe` (needs TYPESAFE_API_KEY)
  * HeuristicClassifier - offline keyword stand-in so the POC runs anywhere
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol


@dataclass(frozen=True)
class Noul:
    """Yes/no question -> probability the statement is true."""
    instructions: str


@dataclass(frozen=True)
class Choice:
    """Pick one of several options -> probability per option."""
    instructions: str
    options: Mapping[str, str]  # option name -> description


@dataclass(frozen=True)
class Score:
    """Rate against ordered levels -> continuous score in [0, 1] (0 = first level, 1 = last)."""
    instructions: str
    levels: tuple[str, ...] = ("low", "medium", "high")


@dataclass
class Result:
    scores: dict[str, float] = field(default_factory=dict)
    nouls: dict[str, float] = field(default_factory=dict)
    choices: dict[str, dict[str, float]] = field(default_factory=dict)

    def top_choice(self, name: str) -> tuple[str, float]:
        probs = self.choices[name]
        key = max(probs, key=probs.get)
        return key, probs[key]


class Classifier(Protocol):
    def classify(self, state: str, questions: Mapping[str, Noul | Choice | Score]) -> Result: ...


_RISKY = re.compile(
    r"\brm\s+-rf\b|\bsudo\b|\bmkfs\b|\bdd\s+if=|curl[^|]*\|\s*(ba)?sh|\bchmod\s+-R\s+777\b|"
    r"\bgit\s+push\s+.*--force\b|drop\s+table|/etc/(passwd|shadow)|\.ssh/|>\s*/dev/sd",
    re.I,
)
_HARD = re.compile(r"architect|design|migrat|security|debug|race condition|trade-?off|high-stakes", re.I)


Rule = Callable[[str, "Noul | Choice | Score"], "float | dict[str, float]"]


class HeuristicClassifier:
    """Deterministic offline stand-in (NOT a model).

    `rules` maps a question name -> fn(state, question) returning a probability (Noul/Score)
    or {option: prob} (Choice). A trailing "*" makes the key a name prefix. Questions with no
    rule fall back to the original risk/difficulty keyword heuristics."""

    def __init__(self, rules: Mapping[str, Rule] | None = None):
        self.rules = dict(rules or {})

    def _rule(self, name: str) -> Rule | None:
        if name in self.rules:
            return self.rules[name]
        for k, fn in self.rules.items():
            if k.endswith("*") and name.startswith(k[:-1]):
                return fn
        return None

    def classify(self, state: str, questions: Mapping[str, Noul | Choice | Score]) -> Result:
        res = Result()
        for name, q in questions.items():
            rule = self._rule(name)
            if rule is not None:
                out = rule(state, q)
            else:
                out = self._fallback(state, name, q)
            if isinstance(q, Noul):
                res.nouls[name] = float(out)
            elif isinstance(q, Score):
                res.scores[name] = float(out)
            else:
                tot = sum(out.values()) or 1.0
                res.choices[name] = {o: p / tot for o, p in out.items()}
        return res

    @staticmethod
    def _fallback(state, name, q):
        if isinstance(q, Noul):
            hit = bool(_RISKY.search(state)) if "risk" in name or "danger" in name else bool(_HARD.search(state))
            return 0.98 if hit else 0.03
        if isinstance(q, Score):
            return 0.5
        hard = bool(_HARD.search(state)) or len(state) > 400
        opts = list(q.options)
        probs = {o: 0.05 for o in opts}
        probs[opts[-1] if hard else opts[0]] = 0.9
        return probs


class TypeSafeBackend:
    """Real Jev via langchain-typesafe (types verified against the installed package).

    Choice/Score take `criteria` (dict / ordered list). Score answers are an expected value
    in [0, N-1]; we normalise to [0, 1] to match the rest of the harness."""

    def __init__(self, classifier=None) -> None:
        from langchain_typesafe import TypeSafeClassifier  # lazy
        self._c = classifier or TypeSafeClassifier()

    def classify(self, state, questions):
        from langchain_typesafe import Choice as TChoice, Noul as TNoul, Score as TScore
        qs = {}
        for name, q in questions.items():
            if isinstance(q, Noul):
                qs[name] = TNoul(instructions=q.instructions)
            elif isinstance(q, Score):
                qs[name] = TScore(instructions=q.instructions, criteria=list(q.levels))
            else:
                qs[name] = TChoice(instructions=q.instructions, criteria=dict(q.options))
        r = self._c.invoke({"state": state, "questions": qs})
        out = Result()
        for name, q in questions.items():
            if isinstance(q, Noul):
                out.nouls[name] = r.nouls[name].noul
            elif isinstance(q, Score):
                out.scores[name] = r.scores[name].score / (len(q.levels) - 1)
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
