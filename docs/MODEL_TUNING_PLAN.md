# Judy — Model Tuning Plan

> Concrete plan for the **weight-update track**. This is separate from the
> existing policy-rewrite loop: here we improve the judge by tuning Gemini
> models on explicit datasets through Google Cloud's model-tuning workflow.

_Last updated: 2026-06-28_

## Goal

Add a lightweight but real **model-update baseline** to Judy so we can compare:

1. **Static vanilla judge**
2. **Context-improved Judy** (current `SKILL.md` rewrite loop)
3. **Weight-updated judge** (Gemini tuning)
4. **Hybrid** (tuned judge + context-improvement loop later)

The first milestone is not "best possible judge." It is:

> Can small, practical weight updates improve LLM-as-a-judge performance for question-answering
> with modest data and modest cloud cost?

## Chosen Gemini setup

Use different Gemini families for the two tuning modes because Google Cloud's
support matrix differs by method:

- **Supervised fine-tuning (SFT):** `Gemini 3.5 Flash`
- **Preference tuning:** `Gemini 2.5 Flash`

Why:

- `Gemini 3.5 Flash` is available for supervised fine-tuning and is the closest
  tuned version of our current primary judge.
- Preference tuning is currently supported on `Gemini 2.5 Flash` /
  `Gemini 2.5 Flash-Lite`, not `Gemini 3.5 Flash`.
- This gives us one strong "same-family tuned judge" path and one explicit
  preference-optimization path without forcing unsupported workflows.

## Cloud operating choices

- **Region:** `us-central1`
- **Auth:** Application Default Credentials (ADC)
- **Dataset store:** **Google Cloud Storage**, not MongoDB

Why GCS:

- Agent Platform / Gemini tuning expects dataset URIs in GCS.
- Static training/validation corpora are cheaper and simpler in object storage
  than in a database.
- MongoDB remains optional later for app-side feedback collection, but should
  not be the system of record for tuning datasets.

## Proposed GCS layout

Use one bucket in the US and keep versioned JSONL snapshots there.

```text
gs://judy-tuning-us/
  sft/
    gemini35-flash/
      v1/
        train.jsonl
        val.jsonl
        test.jsonl
        metadata.json
  pref/
    gemini25-flash/
      v1/
        train.jsonl
        val.jsonl
        test.jsonl
        metadata.json
  eval/
    rewardbench/
    judgebench/
```

## Experiment shape

### Track A — SFT judge on Gemini 3.5 Flash

Train a pairwise question-answering judge on explicit winner labels.

**Input:**

- `system_prompt`
- `question`
- `answer_a`
- `answer_b`

**Target:**

- winner (`A` or `B`)
- optionally structured rationale / criteria for richer supervision later

**Primary use:**

- objective question-answering judge improvement
- closest comparison to the current Judy task

### Track B — Preference tuning on Gemini 2.5 Flash

Train a judge to better match **preferred** evaluations or answers.

There are two reasonable uses:

1. **Answer preference judge**
   Tune on pairs of answers where one is preferred over the other.
2. **Judge-response preference**
   Tune on pairs of candidate *judgments* where one judgment is better than the
   other.

For Judy, start with **answer preference judge** because it aligns with the
existing pairwise question-answering framing and requires less new plumbing.

## Dataset strategy

Keep the first pass small and clean.

### SFT dataset

Build from:

- the tiered synthetic Judy dataset (`A > B > C > D`)
- RewardBench sample
- JudgeBench sample

Derive examples as pairwise supervision:

- `A-vs-C`, `A-vs-B`, `A-vs-D`, and selected harder negatives
- use order-balanced examples so the model does not learn answer-position bias

### Preference-tuning dataset

Start from:

- the existing preference/simulated-user track for cheap offline prototyping
- later, real user choices if collected

For the first cloud run, preference tuning can still be grounded in objective question-answering
preference pairs if needed; the important thing is to validate the pipeline and
measure whether the tuned judge improves.

## JSONL schemas to generate

### SFT JSONL

Keep a Judy-owned intermediate schema in-repo, then render it to the exact
Gemini tuning format when exporting.

Judy intermediate row:

```json
{
  "id": "heldout-001",
  "task_type": "factual_qa",
  "system_prompt": "You are ...",
  "question": "What is ...?",
  "answer_a": "Answer text A",
  "answer_b": "Answer text B",
  "winner": "A",
  "rationale": "A is correct and B violates the constraint."
}
```

Prompt template:

```text
You are a question-answering judge.

SYSTEM PROMPT:
{system_prompt}

QUESTION:
{question}

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}

Return which answer is better: A or B.
```

Target:

```text
A
```

Start **label-only** first. Rationales can be added in a later SFT ablation if
we want to test whether rationale supervision helps or only adds noise.

### Preference JSONL

Use an intermediate schema that can represent chosen vs rejected pairwise
preferences:

```json
{
  "id": "pref-001",
  "task_type": "simple_q",
  "system_prompt": "You are ...",
  "question": "Explain X",
  "answer_a": "Short answer",
  "answer_b": "Longer answer",
  "chosen": "A",
  "rejected": "B",
  "preference_source": "simulated_user_concise"
}
```

Render to the exact GCP preference-tuning format at export time.

## Minimal build order

### Phase 1 — data export

Add scripts that export Judy datasets into tuning-ready JSONL:

- `scripts/export_sft_dataset.py`
- `scripts/export_preference_dataset.py`

Do not tie these directly to cloud APIs yet. First make the datasets legible and
reviewable locally.

### Phase 2 — tuning job runners

Add thin wrappers for launching jobs once dataset format is stable:

- `scripts/run_gemini_sft.py`
- `scripts/run_gemini_preference_tune.py`

These should take:

- project id
- region
- GCS train/val URIs
- display name / version
- base model id

### Phase 3 — evaluation bridge

Add a way to compare tuned-model outputs against:

- vanilla Gemini judge
- current Judy `SKILL.md` judge
- benchmark samples

Likely script:

- `scripts/eval_tuned_judge.py`

## First experiment to run

The fastest informative experiment is:

1. Export a **small SFT set** for pairwise judging
2. Fine-tune `Gemini 3.5 Flash`
3. Evaluate on:
   - held-out synthetic Judy split
   - RewardBench sample
   - JudgeBench sample
4. Compare against:
   - vanilla Gemini 3.5 Flash judge
   - current `SKILL.md`-conditioned Judy judge

This answers the first real question:

> Does supervised weight tuning improve the judge enough to justify the extra
> complexity over the current context-only method?

## Success criteria

For the first tuning pass, success is modest:

- measurable agreement gain over vanilla on at least one benchmark/split
- no obvious collapse in position-consistency
- cloud workflow is reproducible end to end

We do **not** need a giant jump to learn something useful.

## Risks

- **Overfitting to synthetic labels**
  Mitigation: always include external benchmark checks.
- **Judge learns position shortcuts**
  Mitigation: balance answer order in exported data.
- **Preference tuning becomes subjective without a clear metric**
  Mitigation: start with explicit held-out user-policy or benchmark-style
  preference evaluation.
- **Cloud-format churn**
  Mitigation: keep Judy's intermediate schema stable and use exporters.

## Immediate next implementation tasks

1. Add dataset-export scripts for SFT and preference tuning.
2. Add a small config surface for GCP tuning parameters.
3. Add a README/docs section that explains the cloud tuning track.
4. Only after export is reviewed, wire the actual tuning-job launchers.
