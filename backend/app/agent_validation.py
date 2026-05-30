"""Action validators for `apply_map_actions`.

Each action is normalized + checked against a candidate map (datasets touched
this turn + active layers + persistent context layers + transient-prefix layers).
Reject envelope: {"error": str, "hint"?: str}. The `set_chapter_state` action is
delegated to droomzaak_validation.
"""

from __future__ import annotations

from typing import Any

from backend.app import droomzaak_validation

PERSISTENT_CONTEXT_LAYER_IDS = {"stadswijken-gent", "statistische-sectoren-gent"}

# Transient layer id prefixes producible by tools this turn (places-/score-locations-
# are the Droomzaak additions).
TRANSIENT_PREFIXES = {"osm-", "iso-", "rt-", "sub-", "score-", "score-locations-", "places-"}

_TARGET_ACTION_TYPES = {
    "show_layer", "hide_layer", "select_dataset", "zoom_to_layer", "set_layer_filter",
    "clear_layer_filter", "set_layer_style", "set_layer_heatmap", "highlight_features",
    "clear_highlight",
}
_DRAW_ACTION_TYPES = {"draw_radius", "place_marker", "draw_route", "add_annotation", "suggest_street_view"}
_MULTI_ACTION_TYPES = {"compare_layers"}
DROOMZAAK_ACTION_TYPES = {"set_chapter_state"}

ALL_ACTION_TYPES = (
    _TARGET_ACTION_TYPES | _DRAW_ACTION_TYPES | _MULTI_ACTION_TYPES | DROOMZAAK_ACTION_TYPES
)

_HEX = set("0123456789abcdefABCDEF")
_PALETTES = {"blue-yellow-red", "teal-purple", "orange-red"}


def is_transient_layer_id(dataset_id: str) -> bool:
    return any(dataset_id.startswith(p) for p in TRANSIENT_PREFIXES)


def _target_ok(dataset_id: str, candidate_map: dict) -> bool:
    return (
        dataset_id in candidate_map
        or dataset_id in PERSISTENT_CONTEXT_LAYER_IDS
        or is_transient_layer_id(dataset_id)
    )


def _is_lonlat(pair: Any) -> bool:
    return (
        isinstance(pair, (list, tuple))
        and len(pair) == 2
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in pair)
    )


def _hex_ok(color: Any) -> bool:
    return (
        isinstance(color, str)
        and color.startswith("#")
        and len(color) in (4, 7)
        and all(c in _HEX for c in color[1:])
    )


def validate_agent_action(
    action: dict, candidate_map: dict, *, current_chapter_state: dict | None = None
) -> tuple[dict | None, dict | None]:
    if not isinstance(action, dict):
        return None, {"error": "action must be an object"}
    atype = action.get("type")
    if atype not in ALL_ACTION_TYPES:
        return None, {
            "error": f"unknown action type: {atype}",
            "hint": f"Allowed: {sorted(ALL_ACTION_TYPES)}",
        }

    if atype == "set_chapter_state":
        if current_chapter_state is None:
            return None, {
                "error": "set_chapter_state requires current chapter state context",
                "hint": "This is a wrapper bug; report it.",
            }
        return droomzaak_validation.validate_set_chapter_state(action, current_chapter_state)

    if atype in _TARGET_ACTION_TYPES:
        ds = action.get("dataset_id")
        if not isinstance(ds, str) or not _target_ok(ds, candidate_map):
            return None, {
                "error": f"{atype}: unknown or missing dataset_id '{ds}'",
                "hint": "Target a dataset loaded this turn, a persistent context layer, "
                "or a transient layer (osm-/places-/score-locations-/…).",
            }
        if atype == "set_layer_heatmap" and not action.get("field"):
            return None, {"error": "set_layer_heatmap requires a numeric 'field'"}
        if atype == "set_layer_heatmap":
            pal = action.get("palette", "blue-yellow-red")
            if pal not in _PALETTES:
                return None, {"error": f"palette must be one of {sorted(_PALETTES)}"}
        if atype == "set_layer_style":
            style = action.get("style") or {}
            if "color" in style and not _hex_ok(style["color"]):
                return None, {"error": "style.color must be a #hex color"}
        return action, None

    if atype in _MULTI_ACTION_TYPES:
        ids = action.get("dataset_ids")
        if not isinstance(ids, list) or not all(_target_ok(i, candidate_map) for i in ids):
            return None, {"error": "compare_layers: all dataset_ids must be valid targets"}
        return action, None

    if atype == "place_marker":
        markers = action.get("markers")
        if not isinstance(markers, list) or not markers:
            return None, {"error": "place_marker requires a non-empty 'markers' array"}
        for m in markers:
            if not _is_lonlat((m or {}).get("coordinates")):
                return None, {"error": "each marker needs coordinates [lon, lat]"}
        return action, None

    if atype == "draw_radius":
        radii = action.get("radii")
        if not isinstance(radii, list) or not radii:
            return None, {"error": "draw_radius requires a non-empty 'radii' array"}
        for r in radii:
            if not _is_lonlat((r or {}).get("center")):
                return None, {"error": "each radius needs center [lon, lat]"}
        return action, None

    if atype == "draw_route":
        coords = action.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2 or not all(_is_lonlat(c) for c in coords):
            return None, {"error": "draw_route needs ≥2 [lon, lat] coordinates"}
        return action, None

    # add_annotation, suggest_street_view: light-touch (geometry/coords optional)
    return action, None


def validate_actions(
    actions: list, candidate_map: dict, *, current_chapter_state: dict | None = None
) -> tuple[list[dict], list[dict]]:
    """Validate a list. Returns (normalized_actions, errors). One error fails the call."""
    normalized: list[dict] = []
    errors: list[dict] = []
    for idx, action in enumerate(actions or []):
        norm, err = validate_agent_action(
            action, candidate_map, current_chapter_state=current_chapter_state
        )
        if err is not None:
            errors.append({"action_index": idx, **err})
        else:
            normalized.append(norm)
    return normalized, errors
