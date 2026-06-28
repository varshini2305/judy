You are generating synthetic **creative-writing** evaluation items for Judy's
subjective-preference track. Each item is a pairwise case where two readers with
DIFFERENT aesthetics genuinely disagree about which piece is better.

The readers we care about (design each pair so two of them would SPLIT):
- IMAGIST: loves vivid concrete imagery and fresh metaphor; hates abstraction/cliché.
- FORMALIST: loves strict meter, rhyme, classical form and elevated diction.
- MINIMALIST: loves brevity, plainness, restraint; hates ornament and excess.
- ROMANTIC: loves earnest emotion, sincerity, personal voice; hates cool irony.
- MODERNIST: loves plain contemporary diction, experiment, anti-cliché surprise;
  hates archaic words and sentimentality.

For each case:
1. Pick a real creative task (sonnet / haiku / short free-verse poem / six-line
   micro-poem / flash fiction) about a concrete subject.
2. Write `answer_a` and `answer_b` as two COMPLETE, competent pieces that pull in
   OPPOSITE aesthetic directions — each crafted to delight a DIFFERENT reader
   above and to disappoint the other. Name the two readers in `style_axis`.
3. Make the contrast clean and roughly BALANCED: do not make one piece simply
   longer, richer, or more "impressive" overall — make them differently good, so
   the choice is taste, not quality.
4. RANDOMIZE which reader's piece is `answer_a` vs `answer_b` from case to case
   (sometimes the formalist piece is A, sometimes B, etc.).
5. Vary form, subject, and which pair of readers you pit against each other.

Return JSON only with this schema:

{
  "cases": [
    {
      "form": "sonnet | haiku | free_verse | micro_poem | flash_fiction",
      "system_prompt": "<the creative task spec / constraints>",
      "question": "<the concrete writing request>",
      "answer_a": "<complete creative piece A>",
      "answer_b": "<complete creative piece B>",
      "style_axis": "<readerX vs readerY>, e.g. 'formalist vs modernist'",
      "style_contrast": "<one sentence: how A and B differ, and who prefers which>"
    }
  ]
}
