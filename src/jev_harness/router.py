from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .classifier import Choice, Classifier


@dataclass(frozen=True)
class ModelChoice:
    model: str
    criteria: str


class ModelRouter:
    """Pick the cheapest adequate model for a request with one classifier call."""

    def __init__(self, classifier: Classifier, choices: Mapping[str, ModelChoice],
                 instructions: str = "Choose the least costly model that can complete the task."):
        self.classifier, self.choices = classifier, dict(choices)
        self.question = Choice(instructions=instructions,
                               options={k: v.criteria for k, v in self.choices.items()})

    def route(self, user_message: str) -> tuple[str, str, float]:
        res = self.classifier.classify(user_message, {"route": self.question})
        key, conf = res.top_choice("route")
        return key, self.choices[key].model, conf
