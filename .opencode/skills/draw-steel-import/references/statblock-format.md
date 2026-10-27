# Statblock Format Reference

Field-by-field mapping from a Draw Steel statblock (as printed in the PDF) to the
JSON shape defined by `statblock.schema.json` in the working directory. Read the
schema itself for the authoritative list of required fields; this file explains
*where each value comes from on the page*.

## Top level

| JSON field | Source on the statblock | Notes |
|---|---|---|
| `name` | Large monster name (left of the level header) | e.g. "Human Alchemist" |
| `level` | `Level N` in the header | N only |
| `organization` | Header band, e.g. `Platoon`, `Minion`, `Solo` | Part of "Level 2 Platoon Hexer" → `"Platoon"` |
| `role` | Header role word, e.g. `Hexer`, `Ambusher`, `Support` | Same header → `"Hexer"` |
| `type` | Creature types line, e.g. `Human, Humanoid` | Comma-separated → array |
| `encounterValue` | `EV N` | |
| `stamina` | `Stamina` column | |
| `weaknesses` | `Weakness: ...` | `-` → `[]` |
| `immunities` | `Immunity: ...` | Entries like `"Corruption 2"`; `-` → `[]` |
| `speed` | `Speed` column | |
| `mobilityTraits` | `Movement: ...` | e.g. `"Fly"`, `"Climb"`, `"swim"`; `-` → `[]` |
| `size` | `Size` column | `1S`/`1M`/`1L`/`2M`/... |
| `stability` | `Stability` column | |
| `captainBenefit` | Captain benefit line (some leaders) | None → `""` |
| `freeStrike` | `Free Strike` column | |
| `might`/`agility`/`reason`/`intuition`/`presence` | Characteristic row | **Signed integers**: PDF prints `Might −1`, `Reason +2` → `-1`, `+2`. A bare `0` stays `0`. Read from the rendered image, text extraction garbles these. |
| `features` | Everything below the characteristic row | See below |
| `minion` | `Minion` label / minion header | true only for minion blocks |

App-only fields (`tokenImage`, `public`, `source`, `isOwner`, `id`, timestamps,
`monsterBand` scaffolding) are **not** read from the PDF — `scripts/build.py`
fills them.

## Features

Two kinds of rows appear below the characteristic row.

### Abilities (action rows)

| JSON field | Source |
|---|---|
| `featureType` | always `"ability"` |
| `name` | Bold ability name (after the ability-type icon) |
| `type` | Colored action chip: red `Main Action`, blue `Maneuver`, green `Triggered Action`, `Villain Action 1–3` (villain blocks) |
| `roll` | Dice expression next to the name, e.g. `2d10+2` → `"2d10 + 2"`. Absent → `""` |
| `cost` | Right-aligned `N Malice` → `"N Malice"`. Absent → `""` |
| `signature` | `Signature Ability` label on the right → `true` |
| `keywords` | Comma list under the name (e.g. `Area, Magic, Ranged, Weapon`) |
| `distance` | After the `D` icon: `Melee 1`, `Ranged 5`, `3 cube within 5`, `1 burst`, `Self`, `Melee 1 or ranged 5` |
| `target` | After the `T` icon: `One creature`, `Each enemy in the area`, `The triggering creature`, `Self` |
| `trigger` | `Trigger:` line (Triggered Actions only) |
| `ordinal` | 1-based order on the page (abilities and traits share the sequence) |

### Traits (star rows)

`featureType: "trait"`, `name` = bold trait name, body text in `text`
(markdown `**Sub Label:**` for labeled sub-paragraphs, join paragraphs with
`\n\n`), all other action fields `""` / `[]`, `outcomes: []`.

### Outcomes (inside an ability)

Ordered 1-based array:

1. **powerRoll** (only if the ability has potency rows): `type: "powerRoll"`,
   `name: ""`, `text: ""`, and the three potency rows fill
   `tier1`/`tier2`/`tier3`. PDF potency glyphs map to tiers by *printed order*:
   `◂11` → tier1 (lowest potency, weakest effect), `12-16` → tier2, `17+` →
   tier3 (highest potency, strongest effect). Keep potency conditions exactly
   as printed, normalized with a thin space, e.g. `A < 0 dazed (EoT)`.
   Read the glyphs from the rendered image — text extraction corrupts them.
2. **effect** rows: one entry per labeled sub-block, `name` = the label
   (`"Effect"`, `"Special"`, or a Malice label such as `"1+ Malice"`,
   `"3 Malice"`), prose in `text`, tiers `""`.
   - A single trailing `Effect:` paragraph with no potency rows → one effect
     outcome named `"Effect"` and no powerRoll.
   - `N Malice:` upgrade paragraphs after an effect → separate effect
     outcomes named `"N Malice"` / `"1+ Malice"`.

## Malice Features (band-level, optional)

Some blocks have a band-level "Malice Features" section (e.g. leader blocks).
Map it to `monsterBand.maliceFeatures[]`:

| JSON field | Source |
|---|---|
| `name` | Feature name (bold) |
| `cost` | `N Malice` |
| `minimumEchelon` | Echelon gate if printed (e.g. `Echelon 2+`); default `1` |
| `description` | usually `""` |
| `items[]` | The sub-rows: prose rows → `type: "text"` with text in `description`; ability-summary rows → `type: "ability"` (fill `keywords`/`distance`/`target`/`abilityType`, no outcomes); potency tables → `type: "powerRoll"` with `tier1-3` |

## monsterBand (single-monster default)

For a lone statblock: `name` = monster name, `description: ""`, `sections: []`,
`monsters: []`, `maliceFeatures: []` (unless the PDF prints a Malice section
for it). `build.py` creates this scaffolding automatically.

## build.py content-file shape

A content JSON file contains only content fields. Minimal complete example:

```json
{
  "name": "Example Monster",
  "level": 1,
  "role": "",
  "organization": "Solo",
  "type": ["Human", "Humanoid"],
  "encounterValue": 10,
  "stamina": 30,
  "weaknesses": [],
  "immunities": [],
  "speed": 5,
  "mobilityTraits": [],
  "size": "1M",
  "stability": 0,
  "captainBenefit": "",
  "freeStrike": 2,
  "might": 0, "agility": 0, "reason": 0, "intuition": 0, "presence": 0,
  "minion": false,
  "features": [
    {
      "featureType": "ability",
      "name": "Example Strike",
      "text": "",
      "type": "Main Action",
      "roll": "2d10 + 2",
      "cost": "",
      "signature": true,
      "keywords": ["Melee", "Strike"],
      "distance": "Melee 1",
      "target": "One creature",
      "trigger": "",
      "outcomes": [
        { "type": "powerRoll", "name": "", "text": "",
          "tier1": "2 damage", "tier2": "4 damage", "tier3": "5 damage" },
        { "type": "effect", "name": "Effect",
          "text": "Some effect.", "tier1": "", "tier2": "", "tier3": "" }
      ]
    },
    {
      "featureType": "trait",
      "name": "Example Trait",
      "text": "The monster does something passively.",
      "type": "", "roll": "", "cost": "", "signature": false,
      "keywords": [], "distance": "", "target": "", "trigger": "",
      "outcomes": []
    }
  ]
}
```

Omitted `ordinal` values are assigned in order; `maliceFeatures` in the content
file (if present) needs no id/timestamp/ordinal scaffolding — build.py fills
those too.
