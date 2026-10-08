# Evaluation

`justiceaxis_eval` scores a system on the metrics of the paper. It needs no dependencies (the Hugging Face
`datasets` package is only used when the references are downloaded instead of read from a local file).

```bash
pip install -e .                       # from the repository root, or run with  python -m justiceaxis_eval
python -m justiceaxis_eval --template predictions.jsonl      # empty file with every record_id
# fill in charge / disposition / sentence for each task, then:
python -m justiceaxis_eval --predictions predictions.jsonl --out report.json --per-case cases.jsonl
```

## Predictions

One JSON object per task:

```json
{"record_id": "JAV200-002::main", "charge": "murder", "disposition": "custody_immediate", "sentence": 308, "reasoning": "..."}
```

`disposition` is one of `custody_immediate`, `custody_suspended`, `community_order`, `fine`,
`conditional_discharge_or_caution`, `convicted_no_sentence_reported`, `acquitted_or_dismissed`, `appeal_allowed`,
`appeal_dismissed`, `charges_withdrawn`, `force_found_lawful`, `force_found_unlawful`, `outcome_not_reported`.
`sentence` is the total custodial term in months; leave it `null` (or 0) when there is no custodial term.
`reasoning` is not scored: how a judgment is argued is constrained, not scored.

A task without a prediction counts as wrong on every metric.

## Metrics

A judgment is `J = (c, d, s, r)`. Each task has three references: the recorded judgment (`gold`), the rigid-rule
judgment (`rigid`) and the ungrounded-discretion judgment (`ungrounded`).

| Column | Definition |
|---|---|
| Acc | share of tasks whose charge matches exactly |
| Fam | share of tasks whose charge family is correct |
| Disp | share of tasks whose disposition matches exactly |
| Sent. | share of tasks whose sentence matches exactly |
| Avg | mean of Acc, Fam, Disp and Sent. |
| Acc/Fam | exact charge among family-correct tasks |
| Sent/Disp | exact sentence among disposition-correct tasks |
| J_gold, J_rig, J_ung | share of tasks whose outcome lands closest to each reference under `rho` (nearest anchor) |
| Miss | `100 - J_gold` |
| Pol | `(J_rig - J_ung) / (J_rig + J_ung)`, the signed share of misses toward the rigid pole, in [-1, 1] |
| delta, RMR | gain over a baseline run (`--baseline`); RMR is the relative reduction of the baseline's misses |

Intervals are Wilson 95 % half-widths for the proportions and a bootstrap 95 % half-width for Pol.

### Outcome distance

```
l(s, s')   = | log(1 + s) - log(1 + s') |
rho(J, J') = lambda_d * 1[d != d'] + lambda_s * l(s, s') / log(1 + s_max)
```

`s_max` is the longest sentence in the data. An absent sentence counts as 0 months. The paper leaves the weights
open; they default to `lambda_d = lambda_s = 0.5` (`--lambda-d`, `--lambda-s`). `--s-max` takes `all` (the longest
sentence over all references, the default), `gold` (recorded references only) or a number of months.

### Nearest anchor and ties

A prediction goes to the reference with the smallest `rho`. When several references are equally close, the default
`--tie gold-first` gives the task to the recorded judgment if it is among them and splits it evenly otherwise;
`--tie split` splits every tie evenly. Some tasks have references that share the same disposition and sentence, so
this choice matters for them.

### Sentences and charges

* A sentence matches when the months are equal; an absent and a zero sentence match each other.
* A charge matches when the sets of normalised offence components are equal. Labels are split on `;`, `,`, `/` and
  `and`, lower-cased, stripped of statute citations, years and count words.
* The charge family comes from keyword rules (`justiceaxis_eval/families.py`). By default the family counts as correct
  when the primary family of the recorded charge is among the predicted families (`--family-mode`:
  `primary-in-pred`, `set-equal`, `any-overlap`). To use a different family table pass `--family-map table.json`, a
  list of `[family, [regex, ...]]` pairs.

### Scoring a subset

The release does not say which tasks belong to the evaluation split of the paper. To score a subset, pass the
`record_id`s one per line with `--subset ids.txt`.

## Checks

```bash
python -m unittest tests.test_metrics
```

The tests reproduce the arithmetic of the main results table of the paper (Wilson half-widths, Pol, conditional
accuracies, the miss reduction) and the distance, tie and charge rules.
