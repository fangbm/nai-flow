# NAI V5 manga storyboard runtime context

Use this mandatory context before producing storyboard JSON. It is a focused,
runtime adaptation of the `nai5-prompting` chapters on concept development,
prompt field division, multi-character direction, comic paneling, and preflight
checks. It governs storyboard text only; the caller owns NovelAI Character
fields, parameter presets, and final prompt assembly.

## 1. Think as a four-stage visual pipeline

For every page, decide in this order: (1) the story beat and memorable visual
event; (2) camera, framing, focal point, and foreground/middle/background
space; (3) each participant's frozen action and interaction with the setting;
then (4) visible light, palette, weather, and material. Do not use decorative
particles or generic mood words to substitute for an event, a camera decision,
or an action.

Each panel is one readable frozen instant. Prefer an action with an observable
reaction or environmental consequence over a static list of props. A character
may be absent from a panel when the story calls for it; do not force every role
into every panel.

## 2. Field division and identity contract

- `Character 1`, `Character 2`, and so on are the only identity labels allowed
  in panel text. They map exactly to the separately supplied NovelAI Character
  fields. Never use a role name, franchise, alias, hair, face, body, clothing,
  accessory, color scheme, or other appearance detail in a panel.
- Character appearance and identity are supplied once in the independent
  Character fields and reused across panels. When a numbered character appears
  again, use the same number; never invent, rename, merge, or replace a role.
- Make interaction ownership explicit: state who starts the action, who receives
  it, and whose hand owns a shared prop. Avoid ambiguous wording such as
  "their hand" or "both of them" when it matters.
- Panel text can make an interaction readable, but it cannot reliably bind a
  complex action to a numbered identity. Keep interactions to one clear pair at
  a time, and do not invent field-only syntax such as `source#` or `target#` in
  the main panel prompt.

## 3. Prompt-writing rules for a single panel

- Use compact tag-like phrases for pose, shot size, and camera direction, such
  as `upper body`, `from side`, `low angle`, or `hands clasped`. Use one short
  sentence only where a relation, action direction, light path, or spatial fact
  must be unambiguous.
- Pick one principal shot distance and one camera direction. Do not stack
  conflicting camera or framing instructions.
- State a concrete setting and visible lighting source/effect. Avoid filler
  including "beautiful", "cinematic", "romantic atmosphere", "detailed", or
  quality tails.
- Do not include dialogue, speech bubbles, written signs, negative prompts,
  sampler settings, or quality tags. If the story genuinely requires text, say
  which panel contains it and identify its physical carrier; otherwise omit it.
- Never write a sequence in one panel: no `then`, `cut to`, `meanwhile`,
  montage wording, or second beat.

## 4. Comic layout and page continuity

- First establish the requested panel count, arrangement, border treatment, and
  position anchors. The layout declaration controls all later panel directions.
- The page layout must be a prompt-ready first sentence, not a meta explanation:
  state the panel count, arrangement, relative sizes, and panel borders. For an
  irregular page, directly name the main-panel/inset relationship.
- When the requested layout names a dominant hero panel with inset strips, do
  not turn it into a grid: use the top narrow strip for a close-up/setup, let
  the center hero panel carry the decisive action, and reserve the bottom narrow
  strip for a reaction or aftermath.
- Write one independent panel entry per anchor. Each entry must start from its
  own action, expression, camera, setting, and light; do not let one sentence
  describe several panels.
- Keep panel entries as separate numbered or bullet lines in the final prompt;
  never collapse them into one prose paragraph.
- Make the page cohere with one visual connective device: a recurring prop, a
  movement direction, an eyeline/reaction chain, a lighting progression, or a
  clear main-panel/inset relationship. Keep a page in one continuous local
  time/place progression unless the requested layout explicitly says otherwise.
- A multi-panel page is visually dense. Keep the style simple and legible, use
  clean equal borders when requested, and make the intended focus explicit in
  the relevant panel rather than adding competing details everywhere.
- The final page continuity note must name the visible prop, direction, light,
  reaction, or unresolved action that the next page can carry forward.

## 5. Mandatory preflight check

Before returning JSON, verify that: every panel has its requested position
anchor; every panel has one frozen moment; all role references are numbered
`Character N`; appearance is absent; each interaction has a clear initiator,
receiver, and prop owner; the layout and exact page/panel counts match; and the
page has a concrete connective device. Use only the output schema requested by
the caller.
