You are generating synthetic benchmark items for **Judy**, a spec-aware QA
judge. Produce realistic pairwise evaluation cases for human review and model
training.

Your job is to generate **objective** cases where one answer is actually better
than the other according to the task specification.

Important anti-bias rules:

1. Do not make the better answer always longer, shorter, more polished, or more
   formatted. Randomize these surface traits.
2. The weaker answer should often be **plausible**. Avoid obvious nonsense.
3. Vary failure modes:
   - factual error
   - unsupported claim
   - ignored constraint
   - wrong format
   - persona/tone violation
   - incomplete reasoning
   - wrong unit / numeric mistake
4. Randomize whether the better answer is `A` or `B`.
5. Do not leak the winner in field names, wording, or extra commentary.
6. Make the `system_prompt` matter. The winner should be defined by correctness
   plus compliance with explicit constraints.

Return JSON only with this schema:

{
  "cases": [
    {
      "task_type": "...",
      "system_prompt": "...",
      "question": "...",
      "answer_a": "...",
      "answer_b": "...",
      "objectively_better": "A or B",
      "failure_axis": "factual_error | unsupported_claim | ignored_constraint | wrong_format | persona_violation | incomplete_reasoning | numeric_error",
      "winner_reason": "one sentence",
      "difficulty": "easy | medium | hard"
    }
  ]
}

