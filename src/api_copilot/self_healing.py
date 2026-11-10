"""Review-first JSON assertion repair suggestions for API contract drift."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .models import RepairProposal


def resolve_json_path(payload: Any, path: str) -> tuple[bool, Any]:
    """Resolve dot notation such as `data.customer_id` or `$[0].id`."""

    segments = _segments(path)
    current = payload
    for segment in segments:
        try:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            elif isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
                current = current[int(segment)]
            else:
                return False, None
        except (KeyError, IndexError, TypeError):
            return False, None
    return True, current


def propose_self_heal(assertion_path: str, observed_payload: Any, expected_type: str | None = None) -> RepairProposal:
    """Suggest a replacement JSON path when the original assertion fails.

    Suggestions require a strong name/type match and are never applied to test
    files automatically. Every returned proposal requires a human review.
    """

    found, value = resolve_json_path(observed_payload, assertion_path)
    if found and _type_matches(value, expected_type):
        return RepairProposal(
            status="PASS", original_path=assertion_path, proposed_path=assertion_path,
            confidence=1.0, rationale="The assertion path resolves and the observed value matches the expected type.", alternatives=[],
        )

    target = _segments(assertion_path)
    if not target:
        return _no_repair(assertion_path, "The assertion path is empty or invalid.")
    target_leaf = _normalize(target[-1])
    target_parent = ".".join(_normalize(part) for part in target[:-1])
    candidates = []
    for candidate_path, candidate_value in _leaf_values(observed_payload):
        candidate_parts = _segments(candidate_path)
        candidate_leaf = _normalize(candidate_parts[-1]) if candidate_parts else ""
        if expected_type and not _type_matches(candidate_value, expected_type):
            continue
        name_score = SequenceMatcher(None, target_leaf, candidate_leaf).ratio() if target_leaf and candidate_leaf else 0.0
        parent = ".".join(_normalize(part) for part in candidate_parts[:-1])
        parent_bonus = 0.15 if target_parent and parent == target_parent else 0.0
        score = min(1.0, name_score * 0.85 + parent_bonus)
        if candidate_path != assertion_path:
            candidates.append((score, candidate_path, candidate_value))
    candidates.sort(key=lambda item: item[0], reverse=True)
    alternatives = [{"path": path, "value_type": _json_type(value), "score": round(score, 2)} for score, path, value in candidates[:3]]
    if not candidates or candidates[0][0] < 0.52:
        return _no_repair(assertion_path, "No sufficiently similar field with a compatible value type was found. Keep the failed assertion for investigation.", alternatives)
    best_score = candidates[0][0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0.0
    if len(candidates) > 1 and best_score - second_score < 0.08:
        return _no_repair(assertion_path, "Several fields are similarly plausible, so the advisor will not choose one automatically.", alternatives)
    proposed = candidates[0][1]
    confidence = min(0.98, round(0.55 + best_score * 0.4, 2))
    return RepairProposal(
        status="SUGGESTED", original_path=assertion_path, proposed_path=proposed,
        confidence=confidence,
        rationale=f"The original path did not resolve with the expected type. `{proposed}` is the strongest field-name and response-context match; inspect the contract and sample response before accepting it.",
        alternatives=alternatives,
    )


def _no_repair(path: str, reason: str, alternatives: list[dict[str, Any]] | None = None) -> RepairProposal:
    return RepairProposal("NO_SAFE_REPAIR", path, None, 0.0, reason, alternatives or [])


def _segments(path: str) -> list[str]:
    cleaned = path.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    cleaned = cleaned.lstrip(".")
    return [segment for segment in re.split(r"[.\[\]]+", cleaned) if segment]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _leaf_values(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                values.extend(_leaf_values(value, path))
            else:
                values.append((path, value))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}.{index}" if prefix else str(index)
            if isinstance(value, (dict, list)):
                values.extend(_leaf_values(value, path))
            else:
                values.append((path, value))
    return values


def _json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def _type_matches(value: Any, expected_type: str | None) -> bool:
    if not expected_type:
        return True
    actual = _json_type(value)
    if expected_type == "number":
        return actual in {"integer", "number"}
    return actual == expected_type

