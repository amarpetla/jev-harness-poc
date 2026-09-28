"""Minimal agent loop: route model -> (LLM proposes tool calls) -> guard -> execute.

The "LLM" is pluggable; the demo uses a scripted planner so no LLM key is needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .guardrail import AutoModeGuard
from .router import ModelRouter


@dataclass
class Tool:
    name: str
    fn: Callable[..., str]


# planner(model, task) -> iterable of (tool_name, args)
Planner = Callable[[str, str], Iterable[tuple[str, dict[str, Any]]]]


class Harness:
    def __init__(self, router: ModelRouter, guard: AutoModeGuard, tools: list[Tool], planner: Planner):
        self.router, self.guard, self.tools, self.planner = router, guard, {t.name: t for t in tools}, planner

    def run(self, task: str) -> list[str]:
        key, model, conf = self.router.route(task)
        log = [f"route: {key} -> {model} (conf {conf:.2f})"]
        for name, args in self.planner(model, task):
            d = self.guard.check(name, args, context=task)
            if not d.allowed:
                log.append(f"BLOCK {name}({args}): {d.reason}")
                continue
            log.append(f"ok    {name}({args}) -> {self.tools[name].fn(**args)}")
        return log
