from jev_harness.evals.run import prf, run_all
from jev_harness.usecases import get_usecase_classifier


def test_prf_math():
    p, r, f1, acc = prf([0.9, 0.8, 0.2, 0.1], [True, False, True, False], 0.5)
    assert (p, r, acc) == (0.5, 0.5, 0.5) and f1 == 0.5


def test_run_all_structure_and_offline_quality_floor():
    res = run_all(get_usecase_classifier())
    assert len(res["binary"]) == 7 and len(res["categorical"]) == 7
    for r in res["binary"]:
        assert 0 <= r["f1"] <= 1 and r["best_f1"] >= r["f1"] and r["n"] >= 10
    # offline rules were written against these seeds, so this only guards against regressions in the harness itself
    assert all(r["accuracy"] >= 0.5 for r in res["categorical"])
