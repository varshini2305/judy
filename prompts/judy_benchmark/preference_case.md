You are generating synthetic benchmark items for **Judy**, a spec-aware question-answering
judge. Produce realistic pairwise evaluation cases for human preference
collection.

Your job is to generate **preference** cases where **both answers are broadly
acceptable** on correctness and task compliance, but they differ on style or
presentation so a human may prefer one over the other.

Important anti-bias rules:

1. Do not make one answer secretly wrong unless the case is explicitly marked
   otherwise. Preference cases are mainly about style differences.
2. Vary preference dimensions:
   - conciseness vs detail
   - formal vs friendly tone
   - bullets vs prose
   - cautious vs direct wording
   - dense vs example-driven explanation
3. Randomize whether the style likely preferred by one user appears as `A` or
   `B`.
4. Keep both answers plausible and useful.
5. The task should still be realistic, not abstract preference polling.

Return JSON only with this schema:

{
  "cases": [
    {
      "task_type": "...",
      "system_prompt": "...",
      "question": "...",
      "answer_a": "...",
      "answer_b": "...",
      "style_axis": "conciseness | detail | tone | structure | caution | examples",
      "style_contrast": "short description of the difference",
      "difficulty": "easy | medium | hard"
    }
  ]
}
