"""Exercise TypeSafeBackend against a mocked TypeSafe HTTP API (no key/network needed)."""
import json

import pytest

pytest.importorskip("langchain_typesafe")
import httpx2
from langchain_typesafe import TypeSafeClassifier

from jev_harness import Choice, Noul, Score
from jev_harness.classifier import TypeSafeBackend


def _server(seen):
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        seen.append((str(request.url), body))
        answers = {}
        for name, q in body["questions"].items():
            if q["type"] == "noul":
                answers[name] = {"type": "noul", "noul": 0.9}
            elif q["type"] == "choice":
                labels = list(q["criteria"])
                answers[name] = {"type": "choice", "choice": labels[-1], "confidence": 0.8,
                                 "probabilities": {l: (0.7 if l == labels[-1] else 0.3 / (len(labels) - 1)) for l in labels}}
            else:
                n = len(q["criteria"])
                answers[name] = {"type": "score", "score": (n - 1) / 2, "confidence": 0.6,
                                 "legend": {i: c for i, c in enumerate(q["criteria"])},
                                 "probabilities": {i: 1 / n for i in range(n)}}
        return httpx2.Response(200, json={"model": "jev-latest", "answers": answers})
    return handler


def test_backend_roundtrip_all_question_types():
    seen = []
    client = httpx2.Client(transport=httpx2.MockTransport(_server(seen)))
    be = TypeSafeBackend(TypeSafeClassifier(api_key="test", client=client))
    r = be.classify("hello", {
        "u": Noul("urgent?"),
        "c": Choice("which?", {"a": "first", "b": "second"}),
        "s": Score("how bad?", ("low", "mid", "high")),
    })
    assert r.nouls["u"] == 0.9
    assert r.top_choice("c")[0] == "b"
    assert r.scores["s"] == pytest.approx(0.5)  # (3-1)/2 = 1.0 of max 2 -> 0.5
    url, body = seen[0]
    assert url.endswith("/v1/systemone") and body["questions"]["c"]["criteria"] == {"a": "first", "b": "second"}


def test_full_usecase_through_real_backend_path():
    from jev_harness.usecases import triage
    client = httpx2.Client(transport=httpx2.MockTransport(_server([])))
    be = TypeSafeBackend(TypeSafeClassifier(api_key="test", client=client))
    r = triage.triage_ticket(be, "anything")
    assert r["priority"] == "P1" and r["category"] == "account"
