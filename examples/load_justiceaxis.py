"""Load JusticeAxis-256 from the Hugging Face Hub, look at one task and its three references.

    pip install datasets huggingface_hub
    python examples/load_justiceaxis.py --case JAV200-002 --images-only
"""
import argparse
import json

from datasets import load_dataset
from huggingface_hub import snapshot_download

REPO = "beita6969/justiceaxis-256"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="case_id to load (default: first task)")
    ap.add_argument("--images-only", action="store_true", help="skip the large audio files")
    ap.add_argument("--no-media", action="store_true", help="do not download any media")
    args = ap.parse_args()

    inputs = load_dataset(REPO, "default", split="train")
    refs = load_dataset(REPO, "references", split="train")
    if args.case:
        rows = inputs.filter(lambda cid: cid == args.case, input_columns="case_id")
        if len(rows) == 0:
            raise SystemExit(f"no such case: {args.case}")
        task = rows[0]
    else:
        task = inputs[0]
    ref = next(r for r in refs if r["record_id"] == task["record_id"])

    solver_input = json.loads(task["input_json"])
    print("record_id  :", task["record_id"], "| cohort:", task["cohort"])
    print("modalities :", task["modalities"])
    print("instruction:", (task["instruction"] or "")[:160])
    print("input keys :", sorted(solver_input))
    print("images/audio:", len(task["images"]), "/", len(task["audio"]))
    if ref["available"]:
        for name in ("recorded", "rigid_rule", "ungrounded_discretion"):
            o = ref[name]["outcome"]
            print(f"{name:22s}: {o['disposition']} | sentence (months): {o['sentence']}")
    else:
        print("references : not available -", ref["unavailable_reason"])

    if args.no_media:
        return
    paths = [p["path"] for p in task["images"]]
    if not args.images_only:
        paths += [p["path"] for p in task["audio"]]
    root = snapshot_download(REPO, repo_type="dataset", allow_patterns=paths)
    print("media root :", root)
    for p in paths[:3]:
        print("  ", f"{root}/{p}")


if __name__ == "__main__":
    main()
