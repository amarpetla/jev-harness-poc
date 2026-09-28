"""create_agent + langchain-typesafe AutoModeMiddleware, fully offline (fake chat model + mocked TypeSafe API)."""
import json

import pytest

pytest.importorskip("langchain")
pytest.importorskip("langchain_typesafe.experimental.middleware")
import httpx2
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_typesafe import TypeSafeClassifier
from langchain_typesafe.experimental.middleware import AutoModeMiddleware

RAN = []


@tool
def bash(cmd: str) -> str:
    """Run a shell command (simulated)."""
    RAN.append(cmd)
    return f"ran {cmd}"


class ScriptedModel(BaseChatModel):
    """Turn 1: propose a safe and a dangerous bash call. Turn 2: finish."""

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kw):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kw):
        if any(isinstance(m, ToolMessage) for m in messages):
            msg = AIMessage(content="done")
        else:
            msg = AIMessage(content="", tool_calls=[
                {"name": "bash", "args": {"cmd": "ls"}, "id": "1"},
                {"name": "bash", "args": {"cmd": "sudo rm -rf /"}, "id": "2"}])
        return ChatResult(generations=[ChatGeneration(message=msg)])


def _fake_typesafe(request: httpx2.Request) -> httpx2.Response:
    body = json.loads(request.content)
    risky = "rm -rf" in json.dumps(body["state"]["tool_call"])  # judge the proposed call only
    answers = {n: {"type": "noul", "noul": 0.99 if risky else 0.01} for n in body["questions"]}
    return httpx2.Response(200, json={"model": "jev-latest", "answers": answers})


def test_auto_mode_blocks_dangerous_tool_call_in_real_agent(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")  # middleware builds a classifier eagerly; we swap it below
    RAN.clear()
    mw = AutoModeMiddleware(tools=["bash"])
    mw.classifier = TypeSafeClassifier(api_key="test", client=httpx2.Client(transport=httpx2.MockTransport(_fake_typesafe)))
    agent = create_agent(ScriptedModel(), tools=[bash], middleware=[mw])
    out = agent.invoke({"messages": [HumanMessage("clean up")]})
    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert RAN == ["ls"]                                   # dangerous call never executed
    assert [m.status for m in tool_msgs] == ["success", "error"]
