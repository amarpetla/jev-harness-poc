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
The heuristic backend is a keyword stand-in, not a model. The real-Jev backend (`TypeSafeBackend`) follows the blog's
`TypeSafeClassifier` example but is **untested against the live API** (the `Choice` field names in particular are unverified).
Tools are simulated; nothing dangerous is executed.

## Next steps
Score questions, LangChain `create_agent` middleware integration (`langchain_typesafe.experimental.middleware`), real LLM planner.
