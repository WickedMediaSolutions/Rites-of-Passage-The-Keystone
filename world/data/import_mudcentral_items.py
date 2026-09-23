#!/usr/bin/env python3
"""
MudCentral MajorMUD -> Rites of Passage item catalog converter.

INPUT:
    world/data/mudcentral_items_source.txt

OUTPUT:
    world/data/mudcentral_items.json

This converter does NOT modify the live ITEM_REGISTRY or Evennia DB.

Important:
- Repeated appearances of the same item are merged.
- Historical/version differences are preserved as alternate values.
- Same-name records are only split when they appear to be genuinely
  different items rather than repeated database listings.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "mudcentral_items_source.txt"
OUTPUT_FILE = BASE_DIR / "mudcentral_items.json"


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def clean(value: str | None) -> str | None:
    if value is None:
        return None

    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def make_item_id(name: str) -> str:
    value = name.lower().strip()
    value = value.replace("&", " and ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def parse_int(value: str | None) -> int | None:
    value = clean(value)

    if not value:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def parse_number(value: str | None) -> int | float | None:
    value = clean(value)

    if not value:
        return None

    try:
        if "." in value:
            return float(value)

        return int(value)

    except ValueError:
        return None


def parse_damage(
    value: str | None,
) -> tuple[int | None, int | None]:

    value = clean(value)

    if not value:
        return None, None

    match = re.fullmatch(
        r"(-?\d+)\s*-\s*(-?\d+)",
        value,
    )

    if not match:
        return None, None

    return int(match.group(1)), int(match.group(2))


def parse_ac(
    value: str | None,
) -> tuple[int | float | None, int | float | None]:

    value = clean(value)

    if not value:
        return None, None

    parts = value.split("/", 1)

    if len(parts) == 1:
        return parse_number(parts[0]), None

    return (
        parse_number(parts[0]),
        parse_number(parts[1]),
    )


def split_row(line: str) -> list[str]:
    return [
        part.strip()
        for part in line.split("|")
    ]


# ---------------------------------------------------------------------------
# Page classification
# ---------------------------------------------------------------------------

def page_category(
    title: str,
) -> tuple[str | None, str | None]:

    lower = title.lower()

    if "1-handed edged" in lower:
        return "weapon", "1-handed edged"

    if "1-handed blunt" in lower:
        return "weapon", "1-handed blunt"

    if "2-handed edged" in lower:
        return "weapon", "2-handed edged"

    if "2-handed blunt" in lower:
        return "weapon", "2-handed blunt"

    if "all weapons" in lower:
        return "weapon", "all weapons"

    if "all armour" in lower:
        return "armor", "all armour"

    if "suits of armour" in lower:
        return "armor", "suit"

    armor_pages = {
        "arms": "arms",
        "back": "back",
        "chests": "chest",
        "ears": "ears",
        "feet": "feet",
        "fingers": "fingers",
        "hands": "hands",
        "head": "head",
        "legs": "legs",
        "neck": "neck",
        "offhand": "offhand",
        "torso": "torso",
        "waist": "waist",
        "worn": "worn",
        "wrist": "wrist",
    }

    for marker, subtype in armor_pages.items():
        if re.search(
            rf"\b{re.escape(marker)}$",
            lower,
        ):
            return "armor", subtype

    if "food" in lower:
        return "consumable", "food"

    if "drinks and potions" in lower:
        return "consumable", "drink_potion"

    if "keys" in lower:
        return "misc", "key"

    if "light sources" in lower:
        return "misc", "light"

    if "projectiles" in lower:
        return "misc", "projectile"

    return None, None


def is_ignored_page(title: str) -> bool:
    lower = title.lower()

    return (
        "shops:" in lower
        or "shops of the realm" in lower
        or "items monsters drop" in lower
        or "fifth quest" in lower
        or "everything you want to know" in lower
    )


def infer_slot(
    name: str,
    page_title: str,
) -> str | None:

    lower_name = name.lower()
    lower_title = page_title.lower()

    explicit = {
        "(torso)": "chest",
        "(legs)": "legs",
        "(feet)": "feet",
        "(hands)": "hands",
        "(head)": "head",
        "(offhand)": "off_hand",
        "(back)": "back",
        "(neck)": "neck",
        "(waist)": "waist",
        "(wrist)": "wrist",
        "(arms)": "arms",
        "(ears)": "ears",
        "(fingers)": "fingers",
    }

    for marker, slot in explicit.items():
        if marker in lower_name:
            return slot

    title_slots = {
        " arms": "arms",
        " back": "back",
        " chests": "chest",
        " ears": "ears",
        " feet": "feet",
        " fingers": "fingers",
        " hands": "hands",
        " head": "head",
        " legs": "legs",
        " neck": "neck",
        " offhand": "off_hand",
        " torso": "chest",
        " waist": "waist",
        " worn": "worn",
        " wrist": "wrist",
    }

    for marker, slot in title_slots.items():
        if lower_title.endswith(marker):
            return slot

    return None


# ---------------------------------------------------------------------------
# Page extraction
# ---------------------------------------------------------------------------

PAGE_RE = re.compile(
    r"^PAGE\s+(\d+)\s*$",
    re.MULTILINE,
)


def extract_pages(
    text: str,
) -> list[dict[str, Any]]:

    matches = list(PAGE_RE.finditer(text))
    pages: list[dict[str, Any]] = []

    for index, match in enumerate(matches):

        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        block = text[start:end]

        title_match = re.search(
            r"^TITLE:\s*(.+)$",
            block,
            re.MULTILINE,
        )

        url_match = re.search(
            r"^URL:\s*(.+)$",
            block,
            re.MULTILINE,
        )

        structured_match = re.search(
            r"^STRUCTURED TABLE DATA\s*$",
            block,
            re.MULTILINE,
        )

        raw_match = re.search(
            r"^RAW PAGE TEXT\s*$",
            block,
            re.MULTILINE,
        )

        structured_text = ""

        if structured_match:

            structured_start = (
                structured_match.end()
            )

            if raw_match:
                structured_end = raw_match.start()
            else:
                structured_end = len(block)

            structured_text = block[
                structured_start:
                structured_end
            ]

            structured_text = re.sub(
                r"^-{20,}\s*$",
                "",
                structured_text,
                flags=re.MULTILINE,
            )

        pages.append(
            {
                "page": int(match.group(1)),

                "title": (
                    clean(title_match.group(1))
                    if title_match
                    else ""
                ),

                "url": (
                    clean(url_match.group(1))
                    if url_match
                    else ""
                ),

                "structured_text":
                    structured_text.strip(),
            }
        )

    return pages


# ---------------------------------------------------------------------------
# Common parsing
# ---------------------------------------------------------------------------

def skip_line(line: str) -> bool:

    stripped = line.strip()

    if not stripped:
        return True

    if stripped.startswith("[TABLE "):
        return True

    if stripped.startswith("Name |"):
        return True

    if stripped.startswith("Name> |"):
        return True

    if stripped == "Special":
        return True

    if stripped.startswith("TOTAL |"):
        return True

    if stripped.startswith("This colour"):
        return True

    if stripped.startswith("This means"):
        return True

    return False


def source_fields(
    page: dict[str, Any],
    raw_row: str,
) -> dict[str, Any]:

    return {
        "source_detail": [],
        "source_pages": [page["page"]],
        "source_titles": [page["title"]],
        "source_urls": [page["url"]],
        "raw_rows": [raw_row],
    }


# ---------------------------------------------------------------------------
# Weapons
# ---------------------------------------------------------------------------

def parse_weapon_page(
    page: dict[str, Any],
) -> list[dict[str, Any]]:

    lines = page["structured_text"].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 3:

            damage_raw = clean(parts[1])

            damage_min, damage_max = (
                parse_damage(damage_raw)
            )

            if (
                damage_min is not None
                and damage_max is not None
            ):

                if current:
                    records.append(current)

                name = clean(parts[0])

                if not name:
                    current = None
                    continue

                current = {
                    "item_id": make_item_id(name),
                    "name": name,

                    "category": "weapon",

                    "subcategory":
                        page_category(
                            page["title"]
                        )[1],

                    "equipment_slot":
                        "main_hand",

                    "damage_raw":
                        damage_raw,

                    "damage_min":
                        damage_min,

                    "damage_max":
                        damage_max,

                    "speed_raw":
                        clean(
                            parts[2]
                            if len(parts) > 2
                            else None
                        ),

                    "speed":
                        parse_int(
                            parts[2]
                            if len(parts) > 2
                            else None
                        ),

                    "strength_raw":
                        clean(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "strength":
                        parse_int(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "weapon_ac_raw":
                        clean(
                            parts[4]
                            if len(parts) > 4
                            else None
                        ),

                    "accuracy_raw":
                        clean(
                            parts[5]
                            if len(parts) > 5
                            else None
                        ),

                    "accuracy":
                        parse_int(
                            parts[5]
                            if len(parts) > 5
                            else None
                        ),

                    "backstab_accuracy_raw":
                        clean(
                            parts[6]
                            if len(parts) > 6
                            else None
                        ),

                    "backstab_accuracy":
                        parse_int(
                            parts[6]
                            if len(parts) > 6
                            else None
                        ),

                    "encumbrance_raw":
                        clean(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "encumbrance":
                        parse_int(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "level_raw":
                        clean(
                            parts[8]
                            if len(parts) > 8
                            else None
                        ),

                    "level":
                        parse_int(
                            parts[8]
                            if len(parts) > 8
                            else None
                        ),

                    "limit_raw":
                        clean(
                            parts[9]
                            if len(parts) > 9
                            else None
                        ),

                    "limit":
                        parse_int(
                            parts[9]
                            if len(parts) > 9
                            else None
                        ),

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Armor
# ---------------------------------------------------------------------------

def parse_armor_page(
    page: dict[str, Any],
) -> list[dict[str, Any]]:

    lines = page[
        "structured_text"
    ].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 5:

            name = clean(parts[0])
            armor_type = clean(parts[1])
            ac_raw = clean(parts[4])

            armor_ac, armor_dr = (
                parse_ac(ac_raw)
            )

            if (
                name
                and armor_type
                and armor_ac is not None
            ):

                if current:
                    records.append(current)

                location_raw = clean(
                    parts[5]
                    if len(parts) > 5
                    else None
                )

                current = {
                    "item_id":
                        make_item_id(name),

                    "name":
                        name,

                    "category":
                        "armor",

                    "subcategory":
                        armor_type.lower(),

                    "equipment_slot":
                        infer_slot(
                            name,
                            page["title"],
                        ),

                    "armor_type":
                        armor_type,

                    "level_raw":
                        clean(
                            parts[2]
                            if len(parts) > 2
                            else None
                        ),

                    "level":
                        parse_int(
                            parts[2]
                            if len(parts) > 2
                            else None
                        ),

                    "encumbrance_raw":
                        clean(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "encumbrance":
                        parse_int(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "armor_ac_raw":
                        ac_raw,

                    "armor_ac":
                        armor_ac,

                    "armor_dr":
                        armor_dr,

                    "location_raw":
                        location_raw,

                    "accuracy_raw":
                        clean(
                            parts[6]
                            if len(parts) > 6
                            else None
                        ),

                    "accuracy":
                        parse_int(
                            parts[6]
                            if len(parts) > 6
                            else None
                        ),

                    "limit_raw":
                        clean(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "limit":
                        parse_int(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "locations":
                        (
                            [location_raw]
                            if location_raw
                            else []
                        ),

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Food / Keys
# ---------------------------------------------------------------------------

def parse_name_enc_page(
    page: dict[str, Any],
    category: str,
    subcategory: str,
) -> list[dict[str, Any]]:

    lines = page[
        "structured_text"
    ].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 2:

            name = clean(parts[0])

            enc_raw = clean(parts[1])
            enc = parse_int(enc_raw)

            if name and enc is not None:

                if current:
                    records.append(current)

                current = {
                    "item_id":
                        make_item_id(name),

                    "name":
                        name,

                    "category":
                        category,

                    "subcategory":
                        subcategory,

                    "equipment_slot":
                        None,

                    "encumbrance_raw":
                        enc_raw,

                    "encumbrance":
                        enc,

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Light sources
# ---------------------------------------------------------------------------

def parse_light_page(
    page: dict[str, Any],
) -> list[dict[str, Any]]:

    lines = page[
        "structured_text"
    ].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 3:

            name = clean(parts[0])
            enc = parse_int(parts[1])
            rounds = parse_int(parts[2])

            if name and enc is not None:

                if current:
                    records.append(current)

                current = {
                    "item_id":
                        make_item_id(name),

                    "name":
                        name,

                    "category":
                        "misc",

                    "subcategory":
                        "light",

                    "equipment_slot":
                        None,

                    "encumbrance_raw":
                        clean(parts[1]),

                    "encumbrance":
                        enc,

                    "rounds_raw":
                        clean(parts[2]),

                    "rounds":
                        rounds,

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Drinks / Potions
# ---------------------------------------------------------------------------

def parse_potion_page(
    page: dict[str, Any],
) -> list[dict[str, Any]]:

    lines = page[
        "structured_text"
    ].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 3:

            name = clean(parts[0])
            enc = parse_int(parts[1])
            uses = parse_int(parts[2])

            if name and enc is not None:

                if current:
                    records.append(current)

                current = {
                    "item_id":
                        make_item_id(name),

                    "name":
                        name,

                    "category":
                        "consumable",

                    "subcategory":
                        "drink_potion",

                    "equipment_slot":
                        None,

                    "encumbrance_raw":
                        clean(parts[1]),

                    "encumbrance":
                        enc,

                    "uses_raw":
                        clean(parts[2]),

                    "uses":
                        uses,

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Projectiles
# ---------------------------------------------------------------------------

def parse_projectile_page(
    page: dict[str, Any],
) -> list[dict[str, Any]]:

    lines = page[
        "structured_text"
    ].splitlines()

    records: list[dict[str, Any]] = []
    current = None

    for raw_line in lines:

        line = raw_line.strip()

        if skip_line(line):
            continue

        parts = split_row(line)

        if "|" in line and len(parts) >= 3:

            name = clean(parts[0])

            speed_raw = clean(
                parts[2]
                if len(parts) > 2
                else None
            )

            speed = parse_int(speed_raw)

            if name and speed is not None:

                if current:
                    records.append(current)

                damage_raw = clean(
                    parts[1]
                    if len(parts) > 1
                    else None
                )

                damage_min, damage_max = (
                    parse_damage(damage_raw)
                )

                current = {
                    "item_id":
                        make_item_id(name),

                    "name":
                        name,

                    "category":
                        "misc",

                    "subcategory":
                        "projectile",

                    "equipment_slot":
                        None,

                    "damage_raw":
                        damage_raw,

                    "damage_min":
                        damage_min,

                    "damage_max":
                        damage_max,

                    "speed_raw":
                        speed_raw,

                    "speed":
                        speed,

                    "strength_raw":
                        clean(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "strength":
                        parse_int(
                            parts[3]
                            if len(parts) > 3
                            else None
                        ),

                    "weapon_ac_raw":
                        clean(
                            parts[4]
                            if len(parts) > 4
                            else None
                        ),

                    "accuracy_raw":
                        clean(
                            parts[5]
                            if len(parts) > 5
                            else None
                        ),

                    "accuracy":
                        parse_int(
                            parts[5]
                            if len(parts) > 5
                            else None
                        ),

                    "backstab_accuracy_raw":
                        clean(
                            parts[6]
                            if len(parts) > 6
                            else None
                        ),

                    "encumbrance_raw":
                        clean(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "encumbrance":
                        parse_int(
                            parts[7]
                            if len(parts) > 7
                            else None
                        ),

                    "level_raw":
                        clean(
                            parts[8]
                            if len(parts) > 8
                            else None
                        ),

                    "level":
                        parse_int(
                            parts[8]
                            if len(parts) > 8
                            else None
                        ),

                    "limit_raw":
                        clean(
                            parts[9]
                            if len(parts) > 9
                            else None
                        ),

                    "limit":
                        parse_int(
                            parts[9]
                            if len(parts) > 9
                            else None
                        ),

                    **source_fields(
                        page,
                        line,
                    ),
                }

                continue

        if current:
            current[
                "source_detail"
            ].append(line)

    if current:
        records.append(current)

    return records


# ---------------------------------------------------------------------------
# Merge repeated item appearances
# ---------------------------------------------------------------------------

LIST_FIELDS = {
    "source_detail",
    "locations",
    "source_pages",
    "source_titles",
    "source_urls",
    "raw_rows",
}


def records_compatible(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> bool:
    """
    Determine whether two same-name records represent the same item.

    MajorMUD's aggregate pages and detailed pages contain historical/version
    stat differences. Same-name records from those pages are the same item
    and must be merged rather than generating fake _2 items.

    Same-name entries in categories such as keys and potions may genuinely
    represent different records, so those are handled more cautiously.
    """

    if (
        existing.get("category")
        != incoming.get("category")
    ):
        return False

    name_a = clean(existing.get("name"))
    name_b = clean(incoming.get("name"))

    if name_a != name_b:
        return False

    category = existing.get("category")

    # Armor duplicates across All Armour / Suits / slot pages are the
    # same item. Preserve all differing values during merge.
    if category == "armor":
        return True

    # Weapon duplicates across aggregate and individual weapon pages
    # are also the same named weapon.
    if category == "weapon":
        return True

    subtype_a = existing.get("subcategory")
    subtype_b = incoming.get("subcategory")

    if subtype_a != subtype_b:
        return False

    # For simple items, compare their defining values.
    important = (
        "encumbrance_raw",
        "uses_raw",
        "rounds_raw",
        "damage_raw",
        "speed_raw",
        "level_raw",
    )

    comparisons = 0
    disagreements = 0

    for key in important:

        a = existing.get(key)
        b = incoming.get(key)

        if (
            a not in (None, "")
            and b not in (None, "")
        ):
            comparisons += 1

            if a != b:
                disagreements += 1

    if comparisons and disagreements >= 2:
        return False

    return True


def merge_records(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> None:
    """
    Merge repeated appearances while preserving every differing value.
    """

    for key, value in incoming.items():

        if key in LIST_FIELDS:
            continue

        old = existing.get(key)

        if old in (None, "", []):
            existing[key] = value

        elif (
            value not in (None, "", [])
            and value != old
        ):

            alt_key = (
                f"{key}_alternate_values"
            )

            existing.setdefault(
                alt_key,
                [],
            )

            if (
                value
                not in existing[alt_key]
            ):
                existing[
                    alt_key
                ].append(value)

    for key in LIST_FIELDS:

        existing.setdefault(
            key,
            [],
        )

        for value in incoming.get(
            key,
            [],
        ):

            if value not in existing[key]:
                existing[key].append(value)


def add_record(
    catalog: dict[str, dict[str, Any]],
    collisions: list[dict[str, Any]],
    record: dict[str, Any],
) -> None:

    base_id = record["item_id"]

    if not base_id:
        return

    if base_id not in catalog:
        catalog[base_id] = record
        return

    existing = catalog[base_id]

    if records_compatible(
        existing,
        record,
    ):
        merge_records(
            existing,
            record,
        )
        return

    suffix = 2

    while (
        f"{base_id}_{suffix}"
        in catalog
    ):

        candidate = catalog[
            f"{base_id}_{suffix}"
        ]

        if records_compatible(
            candidate,
            record,
        ):
            merge_records(
                candidate,
                record,
            )
            return

        suffix += 1

    new_id = (
        f"{base_id}_{suffix}"
    )

    record["item_id"] = new_id

    catalog[new_id] = record

    collisions.append(
        {
            "name":
                record["name"],

            "base_item_id":
                base_id,

            "new_item_id":
                new_id,

            "source_page":
                record[
                    "source_pages"
                ][0],
        }
    )


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def main() -> None:

    if not SOURCE_FILE.exists():
        raise SystemExit(
            f"Source file not found: "
            f"{SOURCE_FILE}"
        )

    text = SOURCE_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )

    pages = extract_pages(text)

    catalog: dict[
        str,
        dict[str, Any]
    ] = {}

    collisions: list[
        dict[str, Any]
    ] = []

    counts = {
        "weapon": 0,
        "armor": 0,
        "food": 0,
        "key": 0,
        "light": 0,
        "drink_potion": 0,
        "projectile": 0,
    }

    parsed_pages = 0
    ignored_pages = 0
    unsupported_pages = []

    for page in pages:

        title = page["title"]

        if is_ignored_page(title):
            ignored_pages += 1
            continue

        category, subtype = (
            page_category(title)
        )

        records = []

        if category == "weapon":

            records = (
                parse_weapon_page(page)
            )

            counts["weapon"] += (
                len(records)
            )

        elif category == "armor":

            records = (
                parse_armor_page(page)
            )

            counts["armor"] += (
                len(records)
            )

        elif (
            category == "consumable"
            and subtype == "food"
        ):

            records = (
                parse_name_enc_page(
                    page,
                    "consumable",
                    "food",
                )
            )

            counts["food"] += (
                len(records)
            )

        elif (
            category == "misc"
            and subtype == "key"
        ):

            records = (
                parse_name_enc_page(
                    page,
                    "misc",
                    "key",
                )
            )

            counts["key"] += (
                len(records)
            )

        elif (
            category == "misc"
            and subtype == "light"
        ):

            records = (
                parse_light_page(page)
            )

            counts["light"] += (
                len(records)
            )

        elif (
            category == "consumable"
            and subtype
            == "drink_potion"
        ):

            records = (
                parse_potion_page(page)
            )

            counts[
                "drink_potion"
            ] += len(records)

        elif (
            category == "misc"
            and subtype == "projectile"
        ):

            records = (
                parse_projectile_page(
                    page
                )
            )

            counts[
                "projectile"
            ] += len(records)

        else:

            unsupported_pages.append(
                {
                    "page":
                        page["page"],

                    "title":
                        title,
                }
            )

            continue

        parsed_pages += 1

        for record in records:

            add_record(
                catalog,
                collisions,
                record,
            )

    output = {
        "format":
            "rop_mudcentral_item_catalog",

        "version":
            3,

        "source":
            str(SOURCE_FILE),

        "statistics": {
            "pages_found":
                len(pages),

            "pages_parsed":
                parsed_pages,

            "pages_ignored":
                ignored_pages,

            "pages_unsupported":
                len(
                    unsupported_pages
                ),

            "weapon_rows":
                counts["weapon"],

            "armor_rows":
                counts["armor"],

            "food_rows":
                counts["food"],

            "key_rows":
                counts["key"],

            "light_rows":
                counts["light"],

            "drink_potion_rows":
                counts[
                    "drink_potion"
                ],

            "projectile_rows":
                counts["projectile"],

            "unique_catalog_records":
                len(catalog),

            "name_collisions_preserved":
                len(collisions),
        },

        "unsupported_pages":
            unsupported_pages,

        "name_collisions":
            collisions,

        "items":
            dict(
                sorted(
                    catalog.items()
                )
            ),
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "MudCentral COMPLETE "
        "item conversion"
    )

    print("=" * 60)

    print(
        f"Pages found:             "
        f"{len(pages)}"
    )

    print(
        f"Pages parsed:            "
        f"{parsed_pages}"
    )

    print(
        f"Pages ignored metadata:  "
        f"{ignored_pages}"
    )

    print(
        f"Pages unsupported:       "
        f"{len(unsupported_pages)}"
    )

    print()

    print(
        f"Weapon appearances:      "
        f"{counts['weapon']}"
    )

    print(
        f"Armor appearances:       "
        f"{counts['armor']}"
    )

    print(
        f"Food items:              "
        f"{counts['food']}"
    )

    print(
        f"Keys:                    "
        f"{counts['key']}"
    )

    print(
        f"Light sources:           "
        f"{counts['light']}"
    )

    print(
        f"Drinks/Potions:          "
        f"{counts['drink_potion']}"
    )

    print(
        f"Projectiles:             "
        f"{counts['projectile']}"
    )

    print()

    print(
        f"Unique catalog records:  "
        f"{len(catalog)}"
    )

    print(
        f"Name collisions kept:    "
        f"{len(collisions)}"
    )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    if unsupported_pages:

        print()
        print(
            "UNSUPPORTED PAGES:"
        )

        for page in unsupported_pages:

            print(
                f"  PAGE "
                f"{page['page']}: "
                f"{page['title']}"
            )

    if collisions:

        print()
        print(
            "Genuine same-name "
            "records preserved separately:"
        )

        for collision in collisions:

            print(
                f"  "
                f"{collision['name']}: "
                f"{collision['base_item_id']}"
                f" -> "
                f"{collision['new_item_id']}"
            )


if __name__ == "__main__":
    main()
