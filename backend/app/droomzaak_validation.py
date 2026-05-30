"""Droomzaak's only genuinely new validator: `set_chapter_state`.

Enforces the chapter-state contract server-side so even a misbehaving model can't
break the chapter rail: allow-listed keys, type checks, sequential advancement,
and exit conditions checked before `current_chapter` may advance.
"""

from __future__ import annotations

from typing import Any

CHAPTER_STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "current_chapter": {
            "type": "string",
            "enum": ["1_droom", "2_niche", "3_waar", "4_vergunningen", "5_pakket"],
        },
        "dream_profile": {"type": ["object", "null"]},
        "niche_signals": {"type": ["object", "null"]},
        "candidate_locations": {"type": ["array", "null"]},
        "chosen_location": {"type": ["object", "null"]},
        "permit_checklist": {"type": ["array", "null"]},
        "subsidies": {"type": ["array", "null"]},
        "legal_form": {"type": ["object", "null"]},
        "dream_narrative": {"type": ["string", "null"]},
        "tuesday_morning": {"type": ["string", "null"]},
        "package_url": {"type": ["string", "null"]},
    },
    "required": ["current_chapter"],
}

CHAPTER_INDEX = {"1_droom": 1, "2_niche": 2, "3_waar": 3, "4_vergunningen": 4, "5_pakket": 5}

CHAPTER_EXIT_CONDITIONS = {
    "1_droom": lambda s: bool((s.get("dream_profile") or {}).get("sector")),
    "2_niche": lambda s: bool(s.get("niche_signals")),
    "3_waar": lambda s: bool((s.get("chosen_location") or {}).get("coordinates")),
    "4_vergunningen": lambda s: bool(
        s.get("permit_checklist") and s.get("subsidies") and s.get("legal_form")
    ),
    "5_pakket": lambda s: True,
}

EXIT_HINTS_NL = {
    "1_droom": "Set dream_profile.sector first — roep extract_dream_profile aan met de droom-tekst.",
    "2_niche": "Set niche_signals first — roep peer_benchmarks_statbel aan.",
    "3_waar": "Set chosen_location.coordinates first — wacht tot de gebruiker een locatie kiest.",
    "4_vergunningen": "Set permit_checklist, subsidies EN legal_form — roep de drie tools aan.",
    "5_pakket": "Hoofdstuk 5 is terminaal; er valt niets te advancen.",
}

_JSON_TYPE_PY = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


def _type_matches(value: Any, spec: dict) -> bool:
    types = spec.get("type")
    if types is None:
        return True
    if isinstance(types, str):
        types = [types]
    for t in types:
        if t == "null":
            if value is None:
                return True
            continue
        py = _JSON_TYPE_PY.get(t)
        if py and isinstance(value, py) and not (py is int and isinstance(value, bool)):
            return True
    return False


def deep_merge(base: dict, patch: dict) -> dict:
    """Nested dicts merge deep; lists/scalars replace wholesale."""
    out = dict(base)
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def validate_set_chapter_state(
    action: dict, current_state: dict
) -> tuple[dict | None, dict | None]:
    patch = action.get("patch")
    if not isinstance(patch, dict):
        return None, {
            "error": "set_chapter_state.patch must be a dict",
            "hint": "Patch is the partial chapter state to merge.",
        }

    props = CHAPTER_STATE_SCHEMA["properties"]
    invalid = set(patch) - set(props)
    if invalid:
        return None, {
            "error": f"set_chapter_state.patch has unknown keys: {sorted(invalid)}",
            "hint": f"Allowed keys: {sorted(props)}.",
        }

    for key, value in patch.items():
        if not _type_matches(value, props[key]):
            return None, {
                "error": f"set_chapter_state.patch.{key} has wrong type",
                "hint": f"Expected {props[key]['type']}.",
            }

    if "current_chapter" in patch:
        enum = props["current_chapter"]["enum"]
        if patch["current_chapter"] not in enum:
            return None, {"error": f"current_chapter must be one of {enum}"}

    curr = current_state.get("current_chapter", "1_droom")
    target = patch.get("current_chapter")

    if target and target != curr:
        provisional = deep_merge(
            current_state, {k: v for k, v in patch.items() if k != "current_chapter"}
        )
        check = CHAPTER_EXIT_CONDITIONS.get(curr)
        if check and not check(provisional):
            return None, {
                "error": f"Cannot advance past '{curr}': exit condition not met",
                "hint": EXIT_HINTS_NL.get(curr, "Check the chapter exit conditions."),
            }
        if CHAPTER_INDEX[target] != CHAPTER_INDEX[curr] + 1:
            return None, {
                "error": f"Cannot jump from '{curr}' to '{target}'",
                "hint": "Chapters must advance sequentially. Backwards = start a new dream.",
            }

    return {"type": "set_chapter_state", "patch": patch}, None
