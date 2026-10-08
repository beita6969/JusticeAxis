"""python -m justiceaxis_eval --predictions preds.jsonl [--references references.jsonl] [--subset ids.txt] ..."""
import argparse
import json

from .families import load_family_map
from .io import load_predictions, load_references, load_subset
from .metrics import evaluate

COLS = ["Acc", "Fam", "Disp", "Sent", "Avg", "Acc/Fam", "Sent/Disp", "J_gold", "J_rig", "J_ung", "Miss", "Pol"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="justiceaxis_eval", description="Score predictions on JusticeAxis.")
    ap.add_argument("--predictions", help="JSONL: record_id, charge, disposition, sentence (months)")
    ap.add_argument("--template", help="write an empty predictions file with every record_id and exit")
    ap.add_argument("--references", help="local references.jsonl (default: download the Hugging Face dataset)")
    ap.add_argument("--subset", help="text file with one record_id per line; only these tasks are scored")
    ap.add_argument("--baseline", help="predictions of a baseline system, for the delta and RMR columns")
    ap.add_argument("--lambda-d", type=float, default=0.5)
    ap.add_argument("--lambda-s", type=float, default=0.5)
    ap.add_argument("--s-max", default="all", help="'all' (longest sentence over all references), 'gold', or a number of months")
    ap.add_argument("--tie", choices=["gold-first", "split"], default="gold-first")
    ap.add_argument("--family-map", help="JSON list of [family, [regex, ...]] replacing the default charge families")
    ap.add_argument("--family-mode", choices=["primary-in-pred", "set-equal", "any-overlap"], default="primary-in-pred")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", help="write the report as JSON")
    ap.add_argument("--per-case", help="write per-task results as JSONL")
    a = ap.parse_args(argv)

    refs = load_references(a.references)
    if a.subset:
        keep = load_subset(a.subset)
        refs = [r for r in refs if r.record_id in keep]
    if a.template:
        with open(a.template, "w", encoding="utf-8") as f:
            for r in refs:
                f.write(json.dumps({"record_id": r.record_id, "charge": None, "disposition": None, "sentence": None}) + "\n")
        print(f"wrote {len(refs)} rows to {a.template}")
        return
    if not a.predictions:
        ap.error("--predictions is required unless --template is used")
    preds = load_predictions(a.predictions)
    base = load_predictions(a.baseline) if a.baseline else None
    s_max = a.s_max if a.s_max in ("all", "gold") else float(a.s_max)
    table = load_family_map(a.family_map) if a.family_map else None
    rep, rows = evaluate(refs, preds, a.lambda_d, a.lambda_s, s_max, a.tie, table, a.family_mode, base, a.bootstrap, a.seed)

    print(f"tasks scored: {rep['n']}  (missing predictions: {rep['config']['n_missing_predictions']})")
    print("  ".join(f"{c}={'-' if rep[c] is None else format(rep[c], '.2f' if c != 'Pol' else '.3f')}" for c in COLS))
    if "delta_vs_baseline" in rep:
        print("vs baseline: " + "  ".join(f"{k}={'-' if v is None else format(v, '+.2f')}" for k, v in rep["delta_vs_baseline"].items()))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
    if a.per_case:
        with open(a.per_case, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
