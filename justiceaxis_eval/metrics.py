"""JusticeAxis metrics.

A judgment is J = (c, d, s, r): charge, disposition, sentence (total custodial months), reasoning. Each task has three
reference judgments: recorded (gold), rigid-rule (rigid) and ungrounded-discretion (ungrounded).

Reported columns (all in percent except Pol):
  Acc, Fam, Disp, Sent   share of cases with charge, charge family, disposition, sentence exactly correct; Avg = their mean
  Acc/Fam                exact charge among family-correct cases;   Sent/Disp: exact sentence among disposition-correct cases
  J_gold, J_rig, J_ung   share of cases whose outcome lands closest to each reference under the outcome distance rho
  Miss                   100 - J_gold
  Pol                    (J_rig - J_ung) / (J_rig + J_ung), the signed share of misses toward the rigid pole
  RMR                    relative reduction of the misses of a baseline (only with a baseline run)
"""
import math
import random
from collections import namedtuple

from .families import charge_components, charge_families

DISPOSITIONS = (
    "custody_immediate", "custody_suspended", "community_order", "fine", "conditional_discharge_or_caution",
    "convicted_no_sentence_reported", "acquitted_or_dismissed", "appeal_allowed", "appeal_dismissed",
    "charges_withdrawn", "force_found_lawful", "force_found_unlawful", "outcome_not_reported",
)
ROLES = ("gold", "rigid", "ungrounded")
Outcome = namedtuple("Outcome", "disposition sentence")
Reference = namedtuple("Reference", "record_id charge gold rigid ungrounded")


def sentence_value(x):
    """Total custodial months as float, or None when absent."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def norm_disposition(d):
    if d is None:
        return None
    d = str(d).strip().lower()
    return d or None


def _s0(s):
    s = sentence_value(s)
    return 0.0 if s is None else max(s, 0.0)


def sentence_match(pred, gold, tol=1e-6):
    """Exact sentence. An absent or zero sentence matches an absent or zero sentence."""
    p, g = _s0(pred), _s0(gold)
    if sentence_value(pred) is None and sentence_value(gold) is not None and g > 0:
        return False
    if sentence_value(gold) is None and sentence_value(pred) is not None and p > 0:
        return False
    return abs(p - g) <= tol


def log_diff(s, s2):
    """l(s, s') = |log(1+s) - log(1+s')|; absent sentences count as 0."""
    return abs(math.log1p(_s0(s)) - math.log1p(_s0(s2)))


def outcome_distance(d, s, d2, s2, s_max, lambda_d=0.5, lambda_s=0.5):
    """rho(J, J') = lambda_d * 1[d != d'] + lambda_s * l(s, s') / log(1 + s_max)."""
    dd = 0.0 if (norm_disposition(d) is not None and norm_disposition(d) == norm_disposition(d2)) else 1.0
    denom = math.log1p(max(s_max, 1e-9))
    return lambda_d * dd + lambda_s * log_diff(s, s2) / denom


def nearest_anchor(pred, ref, s_max, lambda_d=0.5, lambda_s=0.5, tie="gold-first", eps=1e-12):
    """Weights of the prediction over the three references (they sum to 1).

    The prediction goes to the reference with the smallest rho. Ties: with `gold-first` a tie that includes the recorded
    judgment goes to it and any other tie is split evenly; with `split` every tie is split evenly.
    """
    dist = {r: outcome_distance(pred.disposition, pred.sentence, getattr(ref, r).disposition, getattr(ref, r).sentence,
                                s_max, lambda_d, lambda_s) for r in ROLES}
    best = min(dist.values())
    winners = [r for r in ROLES if dist[r] <= best + eps]
    if tie == "gold-first" and "gold" in winners:
        winners = ["gold"]
    w = {r: (1.0 / len(winners) if r in winners else 0.0) for r in ROLES}
    return w, dist


def polarity(rigid, ungrounded):
    tot = rigid + ungrounded
    return None if tot <= 0 else (rigid - ungrounded) / tot


def wilson_halfwidth(k, n, z=1.96):
    """Half-width of the Wilson score interval for k successes in n trials."""
    if n <= 0:
        return None
    p = k / n
    den = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den


def charge_exact(pred, gold):
    pc, gc = charge_components(pred), charge_components(gold)
    return pc == gc


def family_match(pred, gold, family_table=None, mode="primary-in-pred"):
    gf = charge_families(gold, family_table)
    pf = charge_families(pred, family_table)
    if mode == "set-equal":
        return set(gf) == set(pf)
    if mode == "any-overlap":
        return bool(set(gf) & set(pf))
    return gf[0] in pf


def _pct(x):
    return None if x is None else 100.0 * x


def resolve_s_max(references, s_max="all"):
    """Longest sentence in the data: over all three references ('all'), over the recorded ones ('gold'), or a number."""
    if isinstance(s_max, (int, float)):
        return float(s_max)
    vals = []
    for r in references:
        roles = ROLES if s_max == "all" else ("gold",)
        vals.extend(_s0(getattr(r, role).sentence) for role in roles)
    return max(vals) if vals else 1.0


def _case_row(ref, pred, s_max, lambda_d, lambda_s, tie, family_table, family_mode):
    missing = pred is None
    pc = None if missing else pred.get("charge")
    pd = None if missing else norm_disposition(pred.get("disposition"))
    ps = None if missing else sentence_value(pred.get("sentence", pred.get("sentence_months")))
    out = Outcome(pd, ps)
    fam_ok = False if missing else family_match(pc, ref.charge, family_table, family_mode)
    acc_ok = False if missing else charge_exact(pc, ref.charge)
    disp_ok = (not missing) and pd == norm_disposition(ref.gold.disposition)
    sent_ok = (not missing) and sentence_match(ps, ref.gold.sentence)
    w, dist = nearest_anchor(out, ref, s_max, lambda_d, lambda_s, tie)
    return {
        "record_id": ref.record_id, "missing_prediction": missing, "charge_exact": acc_ok, "family_correct": fam_ok,
        "disposition_correct": disp_ok, "sentence_exact": sent_ok,
        "w_gold": w["gold"], "w_rigid": w["rigid"], "w_ungrounded": w["ungrounded"],
        "rho_gold": dist["gold"], "rho_rigid": dist["rigid"], "rho_ungrounded": dist["ungrounded"],
    }


def _summarise(rows):
    n = len(rows)
    k = lambda key: sum(1 for r in rows if r[key])
    acc, fam, disp, sent = k("charge_exact"), k("family_correct"), k("disposition_correct"), k("sentence_exact")
    fam_rows = [r for r in rows if r["family_correct"]]
    disp_rows = [r for r in rows if r["disposition_correct"]]
    j = {role: sum(r["w_" + role] for r in rows) for role in ROLES}
    res = {
        "n": n,
        "Acc": _pct(acc / n) if n else None, "Fam": _pct(fam / n) if n else None,
        "Disp": _pct(disp / n) if n else None, "Sent": _pct(sent / n) if n else None,
    }
    res["Avg"] = None if not n else (res["Acc"] + res["Fam"] + res["Disp"] + res["Sent"]) / 4.0
    res["Acc/Fam"] = _pct(sum(1 for r in fam_rows if r["charge_exact"]) / len(fam_rows)) if fam_rows else None
    res["Sent/Disp"] = _pct(sum(1 for r in disp_rows if r["sentence_exact"]) / len(disp_rows)) if disp_rows else None
    res["J_gold"] = _pct(j["gold"] / n) if n else None
    res["J_rig"] = _pct(j["rigid"] / n) if n else None
    res["J_ung"] = _pct(j["ungrounded"] / n) if n else None
    res["Miss"] = None if res["J_gold"] is None else 100.0 - res["J_gold"]
    res["Pol"] = polarity(j["rigid"], j["ungrounded"])
    return res


def evaluate(references, predictions, lambda_d=0.5, lambda_s=0.5, s_max="all", tie="gold-first", family_table=None,
             family_mode="primary-in-pred", baseline=None, bootstrap=2000, seed=0):
    """Score `predictions` (record_id -> dict(charge, disposition, sentence)) against `references` (list of Reference).

    Cases without a prediction count as wrong on every metric. Returns (report, per_case_rows).
    """
    refs = list(references)
    smax = resolve_s_max(refs, s_max)
    rows = [_case_row(r, predictions.get(r.record_id), smax, lambda_d, lambda_s, tie, family_table, family_mode) for r in refs]
    rep = _summarise(rows)
    n = rep["n"]
    ci = {}
    for name, key in (("Acc", "charge_exact"), ("Fam", "family_correct"), ("Disp", "disposition_correct"), ("Sent", "sentence_exact")):
        ci[name] = _pct(wilson_halfwidth(sum(1 for r in rows if r[key]), n))
    ci["J_gold"] = _pct(wilson_halfwidth(round(sum(r["w_gold"] for r in rows)), n))
    rng = random.Random(seed)
    pols = []
    if bootstrap and n:
        for _ in range(bootstrap):
            samp = [rows[rng.randrange(n)] for _ in range(n)]
            p = polarity(sum(r["w_rigid"] for r in samp), sum(r["w_ungrounded"] for r in samp))
            if p is not None:
                pols.append(p)
        pols.sort()
    ci["Pol"] = None if len(pols) < 20 else (pols[int(0.975 * (len(pols) - 1))] - pols[int(0.025 * (len(pols) - 1))]) / 2.0
    rep["ci95_halfwidth"] = ci
    rep["config"] = {"lambda_d": lambda_d, "lambda_s": lambda_s, "s_max": smax, "tie": tie, "family_mode": family_mode,
                     "n_missing_predictions": sum(1 for r in rows if r["missing_prediction"])}
    if baseline is not None:
        brep, _ = evaluate(refs, baseline, lambda_d, lambda_s, s_max, tie, family_table, family_mode, bootstrap=0)
        rep["delta_vs_baseline"] = {
            "Acc": rep["Acc"] - brep["Acc"], "Sent": rep["Sent"] - brep["Sent"], "J_gold": rep["J_gold"] - brep["J_gold"],
            "RMR": None if not brep["Miss"] else 100.0 * (brep["Miss"] - rep["Miss"]) / brep["Miss"],
        }
    return rep, rows
