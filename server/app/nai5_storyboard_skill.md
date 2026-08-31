# NAI V5 storyboarding subskill

This is a compact runtime extraction of the local `nai5-prompting` skill. Apply it
before producing storyboard JSON. It governs shot descriptions only; the caller
owns NovelAI Character fields and final prompt assembly.

## Character contract

- `Character 1`, `Character 2`, and so on are the only identity labels in panel
  text. They map exactly to the separately supplied NovelAI Character fields.
  Never invent, rename, merge, or replace a role, and do not put a role name in
  panel text.
- Hair, eyes, face, body, clothes, accessories, color schemes, and other visual
  appearance belong exclusively to NovelAI Character fields. Never describe
  those details in a panel.
- For every interaction, make the direction unambiguous: name who initiates the
  action, who receives it, and who owns any shared prop. Do not write ambiguous
  phrases such as "their hands" or "both of them" when ownership matters.

## Panel contract

- One panel equals one frozen instant. Never combine shots using "then", "cut
  to", "meanwhile", montage language, or a second beat.
- Start from a concrete visual action. Use concise pose and camera phrases for
  discrete facts (for example `upper body`, `from side`, `hands clasped`), then
  use a short sentence only for spatial relation, action direction, or light.
- Select one principal camera distance and one camera direction per panel. Do
  not stack conflicting camera instructions.
- State scene and lighting concretely. Avoid generic filler such as "beautiful",
  "cinematic", "romantic atmosphere", or "detailed" unless tied to visible
  light, weather, or environment.
- No dialogue, speech bubbles, written signs, or quality-tag tails.

## Manga-page contract

- Every panel must have a position anchor: Top-left, Top-right, Bottom-left,
  Bottom-right, or Panel N.
- Keep all panels on the same page in one continuous location/time progression.
  Give each page a visual connective device such as a shared prop, direction of
  movement, lighting progression, or a reaction that follows the previous panel.
- Do not repeat character appearance across panels. The separate Character
  fields provide cross-panel consistency.

## Output contract

- Return only the requested JSON object.
- `title` and `beat` are concise Chinese editorial notes.
- Each `panels` entry is one English visual prompt under 75 words, with its
  position anchor included. It must be usable as a single manga panel without
  relying on any other panel's sentence.
