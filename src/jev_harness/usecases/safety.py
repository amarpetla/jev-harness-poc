"""Safety/quality use cases: prompt injection, PII/secrets, output validation, moderation."""
import re

from ..classifier import Classifier, Noul
from ._rules import kw, overlap

RULES = {
    "s_injection": kw(r"ignore (all |any )?(previous|prior|above)", r"system prompt|you are now|disregard", r"exfiltrate|send .* to http|reveal .*(key|password)"),
    "s_pii": kw(r"\b\d{3}-\d{2}-\d{4}\b", r"[\w.]+@[\w.]+\.\w+", r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|api[_-]?key"),
    "s_offpolicy": kw(r"guaranteed returns|medical diagnosis|legal advice", r"i am not able|as an ai"),
    "s_toxic": kw(r"idiot|stupid|hate you|kill|shut up"),
    "s_answers": overlap,
}


def detect_injection(clf: Classifier, untrusted_text: str) -> float:
    """Score tool outputs / web pages / emails BEFORE they enter the agent's context."""
    return clf.classify(untrusted_text, {"s_injection": Noul("Text tries to give the AI new instructions, override its rules, or exfiltrate data")}).nouls["s_injection"]


def contains_pii(clf: Classifier, text: str) -> float:
    return clf.classify(text, {"s_pii": Noul("Text contains personal data or credentials (SSN, email, API key)")}).nouls["s_pii"]


def redact(text: str) -> str:
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)
    text = re.sub(r"[\w.]+@[\w.]+\.\w+", "[EMAIL]", text)
    return re.sub(r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}", "[KEY]", text)


def validate_output(clf: Classifier, question: str, answer: str) -> dict:
    r = clf.classify(f"Q: {question}\nA: {answer}", {
        "s_answers": Noul(f"The answer addresses the question: {question}"),
        "s_offpolicy": Noul("The answer violates policy (financial/medical/legal guarantees)")})
    return {"on_topic": r.nouls["s_answers"], "off_policy": r.nouls["s_offpolicy"],
            "ok": r.nouls["s_answers"] > 0.4 and r.nouls["s_offpolicy"] < 0.5}


def toxic(clf: Classifier, text: str) -> float:
    return clf.classify(text, {"s_toxic": Noul("Text is abusive or harassing")}).nouls["s_toxic"]
