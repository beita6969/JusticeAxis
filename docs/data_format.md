# Data format

Two JSONL files, hosted at [`beita6969/justiceaxis-256`](https://huggingface.co/datasets/beita6969/justiceaxis-256),
plus media under `data/media/cases/<case_id>/{I,A}/`.

- `data/justiceaxis-256.jsonl`: the case inputs, one row per task (258 rows).
- `data/references.jsonl`: the three reference judgments, one row per task (258 rows). Join on `record_id`.

## Inputs: `justiceaxis-256.jsonl`

| Field | Type | Description |
|---|---|---|
| `case_id` | string | Case identifier, e.g. `JAV200-002`, `NEW-UK-007`. |
| `record_id` | string | Task identifier, `<case_id>::<branch>`. |
| `branch_id` | string | `main`, or the branch name for the two cases with two tasks (`JAVG-B02-008`, `JAVG-B06-012`). |
| `cohort` | string | `baseline128` (original) or `new128` (added later). |
| `language` | string | Always `en`. |
| `modalities` | list of string | `T` text, `I` images, `A` audio. |
| `event_group` | string or null | Tasks that report the same event share a value. |
| `instruction` | string | Task instruction shown to the solver. |
| `requested_output` | list of string | Output parts requested. |
| `images`, `audio` | list of `{path}` | Media paths relative to the repository root. |
| `input_json` | string (JSON) | The full solver input. Parse it with `json.loads`. |

### `input_json`

- `task`: what to judge, the instruction, the prediction boundary, the requested output.
- `modalities.T`: case facts (`evidence_statements`, `chronology`, `reconstructed_background`, `contested_or_unknown`,
  `source_conflicts`), context, legal context (`candidate_statutes`, `predecision_precedents`, `sentencing_framework`),
  sentencing background.
- `modalities.I`: a description of each image.
- `modalities.A`: a description of each audio clip, with its limits.
- `evidence_alignment`: links between facts, images and audio.

The 130 original inputs and the 128 added inputs share one structure; participants are aliased (P1, P2, O1, V1, W1, ...); where
the material does not exist the field is empty. The inner layout is not identical across cases, so it is stored as a JSON
string.

## References: `references.jsonl`

A system's judgment `J = (c, d, s, r)` is compared with all three references of the task. The comparison (outcome
distance, placement, polarity) is defined in the [README](../README.md#references-and-metrics).

| Field | Description |
|---|---|
| `record_id`, `case_id`, `branch_id` | As above. |
| `available` | True for all 258 tasks. |
| `recorded` | `summary`, `answer_json`, `outcome`. |
| `rigid_rule` | `answer`, `major_premise`, `minor_premise`, `conclusion`, `error_type`, `error_explanation`, `contrast_to_standard`, `citations_json`, `outcome`. |
| `ungrounded_discretion` | `answer`, `subjective_premise`, `factual_anchor`, `reasoning`, `conclusion`, `error_type`, `error_explanation`, `contrast_to_standard`, `citations_json`, `outcome`. |

`outcome` has the same structure for all three: `charge`, `disposition`, `component` (always `custodial_total`), `unit`
(always `months`), `scope` (whose sentence), `sentence`, `note`. `disposition` is one of
`custody_immediate`, `custody_suspended`, `community_order`, `fine`, `conditional_discharge_or_caution`,
`convicted_no_sentence_reported`, `acquitted_or_dismissed`, `appeal_allowed`, `appeal_dismissed`, `charges_withdrawn`,
`force_found_lawful`, `force_found_unlawful`, `outcome_not_reported`, or null when none fits. `sentence` is total
custodial months, null when the source states no month or year figure or for life terms; defendants are never added
together and a driving ban is not added to custodial time.

## Media

- Images: PNG / JPEG keyframes, 1,441 files.
- Audio: original WAV / FLAC clips, 435 files, no transcripts. Three cases have no audio: `JAVG-N52-003`,
  `JAVG-SBUF-GL04`, `JAVG-SBUF-GL47`.
- The media is about 19 GB in total; download only the cases you need.
