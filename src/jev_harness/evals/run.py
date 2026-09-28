"""Run: python -m jev_harness.evals [--json out.json]   (TYPESAFE_API_KEY -> real Jev, else offline heuristic)"""
import argparse
import json
import os

from ..usecases import get_usecase_classifier
from .datasets import BINARY, CATEGORICAL


def prf(scores, labels, thr):
    tp = sum(s >= thr and y for s, y in zip(scores, labels))
    fp = sum(s >= thr and not y for s, y in zip(scores, labels))
    fn = sum(s < thr and y for s, y in zip(scores, labels))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    acc = sum((s >= thr) == y for s, y in zip(scores, labels)) / len(labels)
    return p, r, f1, acc


def eval_binary(clf, name, fn, default_thr, cases):
    scores = [fn(clf, x) for x, _ in cases]
    labels = [y for _, y in cases]
    p, r, f1, acc = prf(scores, labels, default_thr)
    sweep = [(round(t / 20, 2), prf(scores, labels, t / 20)) for t in range(1, 20)]
    best_f1 = max(s[1][2] for s in sweep)
    best = [s[0] for s in sweep if s[1][2] == best_f1]
    mid = best[len(best) // 2]  # middle of the plateau, less brittle than the edge
    return {"name": name, "n": len(cases), "default_thr": default_thr, "precision": p, "recall": r, "f1": f1,
            "accuracy": acc, "best_thr": mid, "best_f1": best_f1, "best_range": [best[0], best[-1]],
            "errors": [(x, round(s, 2)) for (x, y), s in zip(cases, scores) if (s >= default_thr) != y]}


def eval_categorical(clf, name, fn, cases):
    preds = [fn(clf, x) for x, _ in cases]
    wrong = [(x, y, p) for (x, y), p in zip(cases, preds) if p != y]
    return {"name": name, "n": len(cases), "accuracy": 1 - len(wrong) / len(cases), "errors": wrong}


def run_all(clf=None):
    clf = clf or get_usecase_classifier()
    return {"binary": [eval_binary(clf, *b) for b in BINARY],
            "categorical": [eval_categorical(clf, *c) for c in CATEGORICAL]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    real = bool(os.environ.get("TYPESAFE_API_KEY"))
    print(f"backend: {'REAL Jev' if real else 'OFFLINE heuristic (numbers say nothing about Jev)'}\n")
    res = run_all()
    print(f"{'binary use case':<24}{'n':>3} {'thr':>5} {'prec':>5} {'rec':>5} {'f1':>5} | {'best thr (F1)':<18}")
    for r in res["binary"]:
        print(f"{r['name']:<24}{r['n']:>3} {r['default_thr']:>5} {r['precision']:>5.2f} {r['recall']:>5.2f} {r['f1']:>5.2f} | "
              f"{r['best_thr']} (F1 {r['best_f1']:.2f}, plateau {r['best_range'][0]}-{r['best_range'][1]})")
    print(f"\n{'categorical use case':<24}{'n':>3} {'acc':>5}")
    for r in res["categorical"]:
        print(f"{r['name']:<24}{r['n']:>3} {r['accuracy']:>5.2f}")
    print("\nMisclassified at default thresholds:")
    for r in res["binary"] + res["categorical"]:
        for e in r["errors"]:
            print(f"  [{r['name']}] {e}")
    print("\nCaveat: seed sets are tiny; extend datasets.py with real examples before adopting a threshold.")
    if a.json:
        json.dump(res, open(a.json, "w"), indent=2, default=str)


if __name__ == "__main__":
    main()
