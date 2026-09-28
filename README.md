# jev-harness-poc

Proof of concept based on LangChain's ["Building a Harness with Jev"](https://www.langchain.com/blog/building-a-harness-with-jev).
Jev is a *System One* model: it takes a `state` plus typed `questions` (Noul / Choice / Score) and returns probabilities
in one cheap call, instead of generating text. This POC uses it for two agent-loop decisions:

| Component | What it does |
|---|---|
| `ModelRouter` | One `Choice` question picks the cheapest adequate model for a task |
| `AutoModeGuard` | One `Noul` question scores each tool call's risk; blocks before execution |
| `Harness` | Minimal loop: route -> plan -> guard -> execute (planner is scripted; swap in an LLM) |

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
