---
name: Draw Steel Import
description: Convert Draw Steel (Cthulhu Workshop TTRPG) monster statblocks from a PDF into stawl.app-importable JSON files. Use when the user provides a PDF containing statblocks and asks to convert, import, or add one or more creatures as JSON.
---

# Draw Steel PDF → stawl.app JSON

## Inputs

- A PDF file with Draw Steel statblocks (usually in the working directory).
- One or more creature names to convert (e.g. "Human Alchemist").

If either is missing, list the PDFs in the working directory, extract the statblock names (`pdftotext -layout` then scan for "Level N" headers), and ask the user which creatures to convert.

## Workflow

1. **Locate the statblock page in the text layer.**

   ```sh
   pdftotext -layout <pdf> /tmp/opencode/ds.txt
   grep -n -i "<creature name>" /tmp/opencode/ds.txt
   ```

   Printed book page numbers are NOT PDF page numbers — find the PDF page whose *content* contains the statblock, not the printed number. (Requires `poppler-utils` for `pdftotext`/`pdftoppm`; install if missing.)

2. **Render the page and read the image.** Multi-column statblocks garble badly in text extraction. Render at 200 dpi and read the PNG — the rendered page is the source of truth:

   ```sh
   pdftoppm -png -r 200 -f <page> -l <page> <pdf> /tmp/opencode/ds
   ```

   Read the image and double-check everything text extraction mangles:
   - signed characteristic modifiers (`−1`, `+2`)
   - potency-row glyphs (`◂11`, `12-16`, `17+`) and potency conditions (`A < 0`, `M < 4` — text extraction turns these into `ac`, `mb`, ...)
   - Malice costs (`N Malice`)
   - action-type chips (`Main Action`, `Maneuver`, `Triggered Action`, `Villain Action 1–3`) and the `Signature Ability` label
   - keywords, distance (`D`), target (`T`), and `Trigger:`/`Effect:` lines

3. **Map fields to JSON** following `references/statblock-format.md` (relative to this skill's directory).

4. **Build and validate.** Write the statblock to a *content* JSON file containing only content fields (no `id`/`createdAt`/`updatedAt`, no `monsterBand`, no app flags), then run the builder (path relative to this skill's directory):

   ```sh
   python3 scripts/build.py /tmp/opencode/<name>.content.json
   ```

   The script checks required content fields, fills app defaults (`tokenImage: null`, `public: false`, `source: "Community"`, `isOwner: true`, band scaffolding, missing ordinals), generates 10-char base62 ids and microsecond-precision UTC timestamps for every entity, validates against `statblock.schema.json` in the working directory (Draft 2020-12), and writes `<Name>-Stawl.json` (spaces → underscores) into the working directory. Exit code 1 with a field-precise error list on validation failure.

   For multiple creatures, repeat steps 2–4 per creature, then run a final pass validating every `*-Stawl.json` in the directory against the schema.

5. **Adapt the schema when the PDF reveals something it doesn't cover.** If validation fails, or if the PDF contains structure with no schema representation, edit `statblock.schema.json` in the working directory per the rules below, re-run the build, and re-validate **all** existing `*-Stawl.json` files in the directory against the updated schema.

## Schema adaptation rules (never drop PDF content)

- **New value for an existing enum** (new action type, size, feature type, outcome type, ...) → extend the `enum` and note the new value in the property's `description`.
- **Value outside a numeric constraint** (a new range of stamina, characteristics, EV, ...) → loosen the constraint (e.g. remove `minimum`/`maximum`), keep `type: "integer"`.
- **New field on an existing object** → add the property with a `description` explaining when it is used; add it to `required` only when it is present in *every* observed example; keep `additionalProperties: false` discipline.
- **New sub-structure** (a new collection on the monster, a new item shape inside `maliceFeatures`, ...) → add a definition under `$defs`, reference it with `$ref`, and follow the existing conventions: camelCase names, `ordinal` (1-based page order), and `id`/`createdAt`/`updatedAt` on every entity. Also extend the defaults in `scripts/build.py` so content files don't need to repeat app scaffolding for the new shape.
- **Never** delete or rename existing schema properties — extend only.
- If the schema and a PDF genuinely conflict (two plausible readings), ask the user which mapping to use instead of guessing.
- Report every schema change in the final answer.

## Conventions

- One JSON file per monster: `<Name with underscores>-Stawl.json` in the working directory.
- `keywords` are listed **alphabetically**, as in the reference files.
- Prose keeps sub-labels as plain text (e.g. "The next strike against the target has an edge."); multi-paragraph text is joined with `\n\n`. Bold sub-headings inside traits use markdown `**Label:**` as in the reference files.
- A lone monster gets a band with its own name, empty `sections` and `monsters`, and `maliceFeatures: []` unless the PDF shows a band-level "Malice Features" section for it.
- `-` in the PDF means "none" → empty string / empty array.

## Final report

For each converted creature, summarize: the file written, non-obvious mapping decisions (organization/role split, signed characteristics, Malice costs, trigger lines), and any schema changes made. Keep it compact.
