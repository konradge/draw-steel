#!/usr/bin/env python3
"""Build a stawl.app-importable Draw Steel statblock JSON from a content file.

Usage:
    python build.py <content.json> <output_dir>

<output_dir> (required) is the project directory: the schema is read from
<output_dir>/statblock.schema.json and the result is written there.

The content file holds only content fields (see references/statblock-format.md).
This script:
  * checks required content fields,
  * fills app defaults (tokenImage, public, source, isOwner, monsterBand),
  * assigns ordinals where missing,
  * generates 10-char base62 ids + microsecond UTC timestamps on every entity,
  * validates against statblock.schema.json in the output dir (Draft 2020-12),
  * writes <Name with underscores>-Stawl.json into the output dir.

Exit code 1 with a field-precise error list on any failure.
"""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

TOP_REQUIRED = [
    "name", "level", "role", "organization", "type", "encounterValue",
    "stamina", "weaknesses", "immunities", "speed", "mobilityTraits",
    "size", "stability", "captainBenefit", "freeStrike",
    "might", "agility", "reason", "intuition", "presence",
    "minion", "features",
]

FEATURE_REQUIRED = [
    "featureType", "name", "text", "type", "roll", "cost", "signature",
    "keywords", "distance", "target", "trigger", "outcomes",
]

OUTCOME_REQUIRED = ["type", "name", "text", "tier1", "tier2", "tier3"]

MALICE_FEATURE_REQUIRED = ["name", "cost", "items"]
MALICE_ITEM_REQUIRED = ["name", "description", "type", "tier1", "tier2", "tier3"]


def rid() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(10))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def check(required, obj, path, errors):
    for key in required:
        if key not in obj:
            errors.append(f"missing field {path}.{key}")


def stamp(entity, now_str):
    entity["id"] = rid()
    entity["createdAt"] = now_str
    entity["updatedAt"] = now_str
    return entity


def build(content, now_str):
    errors = []
    check(TOP_REQUIRED, content, "", errors)
    if errors:
        return None, errors

    # ordinal assignment: 1-based, across features (and within malice items)
    for i, feat in enumerate(content["features"], start=1):
        check(FEATURE_REQUIRED, feat, f"features[{i-1}]", errors)
        feat.setdefault("ordinal", i)
        for j, out in enumerate(feat["outcomes"], start=1):
            check(OUTCOME_REQUIRED, out, f"features[{i-1}].outcomes[{j-1}]", errors)
            out.setdefault("ordinal", j)
            stamp(out, now_str)
        stamp(feat, now_str)

    malice = content.get("maliceFeatures", [])
    for i, mf in enumerate(malice, start=1):
        check(MALICE_FEATURE_REQUIRED, mf, f"maliceFeatures[{i-1}]", errors)
        for j, item in enumerate(mf["items"], start=1):
            check(MALICE_ITEM_REQUIRED, item, f"maliceFeatures[{i-1}].items[{j-1}]", errors)
            item.setdefault("ordinal", j)
            item.setdefault("abilityType", "Main Action")
            item.setdefault("roll", "")
            item.setdefault("keywords", [])
            item.setdefault("distance", "")
            item.setdefault("target", "")
            item.setdefault("trigger", "")
            stamp(item, now_str)
        mf.setdefault("description", "")
        mf.setdefault("minimumEchelon", 1)
        stamp(mf, now_str)

    doc = dict(content)
    doc["monsterBand"] = {
        "name": content.get("monsterBandName") or content["name"],
        "description": "",
        "public": False,
        "source": "Community",
        "sections": [],
        "maliceFeatures": malice,
        "monsters": [],
    }
    doc.setdefault("tokenImage", None)
    doc.setdefault("public", False)
    doc.setdefault("source", "Community")
    doc.setdefault("isOwner", True)
    doc.pop("monsterBandName", None)
    stamp(doc, now_str)
    stamp(doc["monsterBand"], now_str)
    return doc, errors


def ensure_jsonschema():
    try:
        import jsonschema
        return jsonschema
    except ImportError:
        pass

    # Same fallback chain as pdf.py: externaly-managed Pythons (PEP 668)
    # reject plain pip installs, so try --user and --break-system-packages.
    import subprocess
    for args in (["-m", "pip", "install", "-q", "jsonschema"],
                 ["-m", "pip", "install", "-q", "--user", "jsonschema"],
                 ["-m", "pip", "install", "-q", "--break-system-packages", "jsonschema"]):
        print(f"jsonschema not found — trying: {sys.executable} {' '.join(args)}",
              file=sys.stderr)
        if subprocess.run([sys.executable] + args).returncode == 0:
            try:
                import jsonschema
                return jsonschema
            except ImportError:
                continue
    print("could not install jsonschema automatically. "
          "Install it manually (python -m pip install jsonschema) and re-run.",
          file=sys.stderr)
    sys.exit(1)


def validate(doc, schema_path):
    jsonschema = ensure_jsonschema()

    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    return sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    if len(sys.argv) < 3:
        print("usage: python build.py <content.json> <output_dir>", file=sys.stderr)
        return 1
    content_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    schema_path = out_dir / "statblock.schema.json"

    content = json.loads(content_path.read_text())
    now_str = now()

    doc, errors = build(content, now_str)
    if errors:
        print("Content errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 1

    verrors = validate(doc, schema_path)
    if verrors:
        print("Schema validation errors:", file=sys.stderr)
        for e in verrors:
            loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
            print(f"  - {loc}: {e.message}", file=sys.stderr)
        return 1

    out_name = doc["name"].replace(" ", "_") + "-Stawl.json"
    out_path = out_dir / out_name
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"OK {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
