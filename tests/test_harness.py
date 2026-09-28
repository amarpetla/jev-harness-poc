from jev_harness import *


def make():
    clf = HeuristicClassifier()
    router = ModelRouter(clf, {"fast": ModelChoice("m-fast", "easy"), "powerful": ModelChoice("m-big", "hard")})
    ran = []
    tool = Tool("bash", lambda cmd: ran.append(cmd) or "done")
    planner = lambda m, t: [("bash", {"cmd": "ls"}), ("bash", {"cmd": "sudo rm -rf /"})]
    return Harness(router, AutoModeGuard(clf, ["bash"]), [tool], planner), ran


def test_routing():
    h, _ = make()
    assert h.router.route("what is in README")[1] == "m-fast"
    assert h.router.route("design the architecture")[1] == "m-big"


def test_guard_blocks_dangerous_only():
    h, ran = make()
    log = h.run("do stuff")
    assert ran == ["ls"]
    assert any(l.startswith("BLOCK") for l in log)


def test_ungated_tool_passes():
    g = AutoModeGuard(HeuristicClassifier(), ["bash"])
    assert g.check("read_file", {"path": "/etc/passwd"}).allowed
