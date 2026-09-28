"""Triage use cases: support tickets, email, alerts/logs, leads, issues, code review, intent routing."""
from ..classifier import Choice, Classifier, Noul, Score
from ._rules import kw, pick

RULES = {
    "t_urgent": kw(r"asap|urgent|immediately|losing|down|outage|now\b", r"days?\b|failing|500"),
    "t_sentiment": lambda s, q: 0.05 if kw(r"angry|terrible|worst|unacceptable|losing|fail")(s, q) > 0.4 else 0.6,
    "t_category": pick({"billing": (r"invoice|charge|refund|payment|stripe",), "bug": (r"error|fail|crash|500|broken",),
                        "howto": (r"how do|how to|can i",), "account": (r"password|login|account|2fa",)}, "howto"),
    "e_action": pick({"reply_now": (r"asap|urgent|today|deadline",), "schedule": (r"meeting|call|calendar|schedule",),
                      "archive": (r"newsletter|receipt|unsubscribe|fyi",), "spam": (r"winner|lottery|crypto giveaway|click here",)},
                     "archive"),
    "a_page": kw(r"error rate|5\d\d|oom|panic|down|outage|timeout", r"prod|customer|payment"),
    "a_noise": kw(r"retry succeeded|deprecat|info\b|debug|healthy"),
    "l_score": lambda s, q: min(0.95, 0.1 + 0.3 * sum(bool(__import__("re").search(w, s, __import__("re").I))
                                                        for w in (r"budget", r"this quarter|asap", r"decision.?maker|cto|vp|director", r"demo|pricing"))),
    "i_priority": pick({"critical": (r"data loss|security|crash|prod|regression",), "normal": (r"bug|error|wrong",),
                        "low": (r"typo|docs|cosmetic|feature request",)}, "normal"),
    "r_sensitive": kw(r"auth|password|secret|token|migration|payment|crypto|\.env|permission"),
    "n_intent": pick({"order_status": (r"where is|track|shipping|delivery",), "refund": (r"refund|money back|charged",),
                      "cancel": (r"cancel|unsubscribe|stop my",), "human": (r"human|agent|representative|manager",)}, "order_status"),
}


def triage_ticket(clf: Classifier, text: str) -> dict:
    r = clf.classify(text, {
        "t_urgent": Noul("The message conveys urgency or time-sensitivity"),
        "t_sentiment": Score("Customer sentiment", ("negative", "neutral", "positive")),
        "t_category": Choice("Ticket category", {"billing": "payments", "bug": "product defect", "howto": "usage question", "account": "login/account"}),
    })
    cat, _ = r.top_choice("t_category")
    urgent, sent = r.nouls["t_urgent"], r.scores["t_sentiment"]
    prio = "P1" if urgent > 0.8 else "P2" if urgent > 0.4 or sent < 0.25 else "P3"
    return {"priority": prio, "category": cat, "urgent": urgent, "sentiment": sent}


def triage_email(clf: Classifier, text: str) -> tuple[str, float]:
    r = clf.classify(text, {"e_action": Choice("What should be done with this email", {
        "reply_now": "needs a prompt reply", "schedule": "meeting/calendar request", "archive": "informational", "spam": "unsolicited junk"})})
    return r.top_choice("e_action")


def triage_alert(clf: Classifier, log: str) -> str:
    r = clf.classify(log, {"a_page": Noul("This requires waking a human on-call now"),
                           "a_noise": Noul("This is routine noise that self-resolved")})
    if r.nouls["a_page"] > 0.7 and r.nouls["a_noise"] < 0.5:
        return "PAGE"
    return "IGNORE" if r.nouls["a_noise"] > 0.4 else "TICKET"


def score_lead(clf: Classifier, text: str) -> str:
    s = clf.classify(text, {"l_score": Score("Purchase intent of this lead", ("cold", "warm", "hot"))}).scores["l_score"]
    return "hot" if s > 0.66 else "warm" if s > 0.33 else "cold"


def prioritize_issue(clf: Classifier, text: str) -> str:
    return clf.classify(text, {"i_priority": Choice("Issue priority", {"critical": "data loss/security/outage", "normal": "ordinary bug", "low": "cosmetic"})}).top_choice("i_priority")[0]


def needs_human_review(clf: Classifier, diff: str, threshold: float = 0.5) -> bool:
    return clf.classify(diff, {"r_sensitive": Noul("Diff touches auth, secrets, payments, migrations or permissions")}).nouls["r_sensitive"] >= threshold


def route_intent(clf: Classifier, text: str) -> str:
    return clf.classify(text, {"n_intent": Choice("Customer intent", {"order_status": "order tracking", "refund": "wants refund", "cancel": "cancel subscription", "human": "wants a person"})}).top_choice("n_intent")[0]
