# jev-harness-poc

Proof of concept based on LangChain's ["Building a Harness with Jev"](https://www.langchain.com/blog/building-a-harness-with-jev).
Jev is a *System One* model: it takes a `state` plus typed `questions` (Noul / Choice / Score) and returns probabilities
in one cheap call, instead of generating text. This POC uses it for two agent-loop decisions:

| Component | What it does |
|---|---|
| `ModelRouter` | One `Choice` question picks the cheapest adequate model for a task |
| `AutoModeGuard` | One `Noul` question scores each tool call's risk; blocks before execution |
| `Harness` | Minimal loop: route -> plan -> guard -> execute (planner is scripted; swap in an LLM) |

## Use cases (all runnable: `python examples/run_all_usecases.py`)
| Module | Use cases |
|---|---|
| `usecases/triage.py` | support tickets (Noul+Score+Choice), email triage, alert/log paging, lead scoring, issue priority, code-review pre-screen, intent routing |
| `usecases/safety.py` | prompt-injection detection on untrusted text, PII/secret detection + redaction, output validation, moderation |
| `usecases/loop_control.py` | task-done check, stuck-loop detection, human escalation, tool pre-filter, memory relevance |
| `usecases/cost.py` | semantic cache lookup, needs-retrieval, context compression |
| `usecases/agents.py` | browser next-step, trade gate (paper only, not advice), LLM-as-judge scoring |
| `router.py` / `guardrail.py` / `harness.py` | model routing + Auto Mode tool gating in a minimal agent loop |

Offline mode uses keyword/overlap rules (`usecases/_rules.py`) that only imitate Jev so the logic and tests run without a key.
Their outputs are NOT representative of Jev's accuracy; validate thresholds against the real API.

## Run
```bash
pip install -e '.[dev]'
pytest
python examples/demo.py                      # offline heuristic backend
pip install -e '.[jev]' && TYPESAFE_API_KEY=... python examples/demo.py   # real Jev
```
## What is verified
- `TypeSafeBackend` was checked against the installed `langchain-typesafe` types (`Choice`/`Score` use `criteria`; `Score` returns an
  expected value in [0, N-1], normalised here to [0, 1]) and is tested through a mocked TypeSafe HTTP API.
- `tests/test_langchain_integration.py` runs a real `create_agent` with the library's `AutoModeMiddleware` (fake chat model + mocked API):
  the dangerous tool call is blocked and never executed.
- **Not verified:** behaviour/accuracy against the live Jev API (no key was available). Offline heuristic outputs are not representative.
- Tools are simulated; nothing dangerous is executed.

## Using the official middleware
```python
from langchain.agents import create_agent
from langchain_typesafe.experimental.middleware import AutoModeMiddleware, ModelRouterMiddleware, ModelChoice
agent = create_agent("openai:gpt-5.6-luna", tools=[bash], middleware=[AutoModeMiddleware(tools=["bash"])])
```
Note: the classifier sees recent messages as context, so judge/mocks must key on the proposed `tool_call`, not the whole state.

## Evals: pick thresholds with data
```bash
python -m jev_harness.evals                     # offline heuristic (numbers are NOT about Jev)
TYPESAFE_API_KEY=... python -m jev_harness.evals --json out.json   # real Jev
```
`evals/datasets.py` holds small labelled seed sets for 7 probability use cases (injection, PII, toxicity, needs-retrieval, escalate,
task-done, code-review) and 7 categorical ones. For each probability use case it reports precision/recall/F1 at the default threshold,
sweeps 0.05-0.95, and prints the best-F1 plateau plus every misclassified example. Offline scores are near-perfect only because the
heuristic rules were written against these same seeds. Replace/extend the datasets with real examples (dozens per use case) first.

## Next steps
Label real examples and tune thresholds per use case against the live API; swap the scripted planner in `harness.py` for an LLM.
