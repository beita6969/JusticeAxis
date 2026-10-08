"""Reading references and predictions."""
import json

from .metrics import Outcome, Reference, sentence_value, norm_disposition

HF_REPO = "beita6969/justiceaxis-256"


def _outcome(block):
    o = (block or {}).get("outcome") or {}
    return Outcome(norm_disposition(o.get("disposition")), sentence_value(o.get("sentence")))


def reference_from_row(row):
    if not row.get("available", True):
        return None
    rec = row["recorded"]
    return Reference(row["record_id"], (rec.get("outcome") or {}).get("charge"), _outcome(rec),
                     _outcome(row["rigid_rule"]), _outcome(row["ungrounded_discretion"]))


def load_references(path=None):
    """References from a local references.jsonl, or from the Hugging Face dataset when `path` is None."""
    if path:
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    else:
        from datasets import load_dataset  # optional dependency
        rows = list(load_dataset(HF_REPO, "references", split="train"))
    refs = [reference_from_row(r) for r in rows]
    return [r for r in refs if r is not None]


def load_predictions(path):
    """JSONL with one object per task: record_id, charge, disposition, sentence (total custodial months or null)."""
    preds = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                o = json.loads(line)
                preds[o["record_id"]] = o
    return preds


def load_subset(path):
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}
