"""User personas with hidden preference policies for the subjective-creative track.

These five personas represent *different points in the user-preference
distribution* for creative/subjective writing (poems, sonnets, micro-fiction).
Each carries a ``hidden_policy``: a private rubric that decides which candidate
that user prefers. The hidden policy is used ONLY as the labelling oracle when
generating the benchmark — it is NEVER shown to the jurors. A juror must
*recover* its assigned user's taste from that user's training labels alone, so
the experiment tests genuine preference modelling, not prompt copying.

The personas are deliberately *conflicting* (a Formalist and a Modernist, an
Imagist and a Minimalist disagree by construction), so a single judge cannot
satisfy all of them at once — which is exactly what makes a per-user jury
necessary rather than decorative.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    """One simulated user. ``hidden_policy`` is the label oracle (juror never sees it)."""

    id: str
    name: str
    hidden_policy: str


PERSONAS: list[Persona] = [
    Persona(
        id="imagist",
        name="The Imagist",
        hidden_policy=(
            "You judge creative writing purely on the freshness and vividness of "
            "its imagery. You strongly prefer concrete sensory detail, surprising "
            "metaphor, and precise particulars. You dislike abstraction, stock "
            "phrases, and clichés, and you do not care about rhyme, meter, or "
            "length. Between two pieces, prefer the one with the more vivid, "
            "original imagery even if it is looser in form."
        ),
    ),
    Persona(
        id="formalist",
        name="The Formalist",
        hidden_policy=(
            "You judge creative writing on craft of form: regular meter, clean "
            "rhyme, and disciplined classical structure. You prefer elevated, "
            "polished diction and a clear formal shape (a true sonnet, a real "
            "haiku count). You dislike free verse that reads as prose with line "
            "breaks, and you penalise metrical sloppiness. Between two pieces, "
            "prefer the one with stronger, more disciplined formal craft."
        ),
    ),
    Persona(
        id="minimalist",
        name="The Minimalist",
        hidden_policy=(
            "You judge creative writing on economy and restraint. You prefer "
            "brevity, plain concrete language, and negative space; every word must "
            "earn its place. You dislike ornate diction, piled-up adjectives, and "
            "emotional excess. Between two pieces, prefer the leaner, quieter, more "
            "restrained one, even if it is less ambitious."
        ),
    ),
    Persona(
        id="romantic",
        name="The Romantic",
        hidden_policy=(
            "You judge creative writing on emotional intensity and sincerity. You "
            "prefer a strong personal voice, heartfelt feeling, and earnest "
            "vulnerability. You dislike detachment, irony, and cold cleverness. "
            "Between two pieces, prefer the one that feels more emotionally alive "
            "and sincere, even if it is less polished or less restrained."
        ),
    ),
    Persona(
        id="modernist",
        name="The Modernist",
        hidden_policy=(
            "You judge creative writing on modern surprise and originality. You "
            "prefer plain contemporary diction, formal experiment, and anti-cliché "
            "freshness. You dislike archaic words ('thee', 'o'er'), sentimentality, "
            "and predictable rhyme. Between two pieces, prefer the more inventive, "
            "contemporary, anti-sentimental one, even if it breaks traditional form."
        ),
    ),
]

PERSONAS_BY_ID: dict[str, Persona] = {p.id: p for p in PERSONAS}
