"""Optional OpenAI explanation/candidate helper for API assertion repairs."""

from __future__ import annotations

import json
import os
from typing import Any

from .models import RepairProposal
from .self_healing import propose_self_heal, resolve_json_path


def suggest_repair_with_llm(assertion_path: str, payload: Any, expected_type: str | None = None, api_key: str | None = None) -> RepairProposal:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY to use the optional LLM repair advisor.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('Install the optional dependency with: pip install -e ".[llm]"') from exc

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You advise on broken API JSONPath assertions. Return JSON with proposed_path (string or null), confidence (0 to 1), rationale (string), alternatives (array of {path, score}). Do not invent fields absent from the payload. A path suggestion is only advisory; a human must review it."},
            {"role": "user", "content": json.dumps({"assertion_path": assertion_path, "expected_type": expected_type, "observed_payload": payload}, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The LLM returned an empty repair suggestion.")
    data = json.loads(content)
    proposed = data.get("proposed_path")
    alternatives = data.get("alternatives", [])
    if not isinstance(alternatives, list):
        raise ValueError("LLM alternatives must be an array.")
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("LLM confidence must be numeric.") from exc
    if not 0 <= confidence <= 1:
        raise ValueError("LLM confidence must be between 0 and 1.")
    if proposed is not None:
        if not isinstance(proposed, str):
            raise ValueError("LLM proposed_path must be a string or null.")
        exists, _ = resolve_json_path(payload, proposed)
        if not exists:
            raise ValueError("The LLM proposed a path that is absent from the observed payload.")
        if propose_self_heal(proposed, payload, expected_type).status != "PASS":
            raise ValueError("The LLM proposed a path whose observed value does not match the expected type.")
        status = "SUGGESTED"
    else:
        status = "NO_SAFE_REPAIR"
    return RepairProposal(
        status=status, original_path=assertion_path, proposed_path=proposed,
        confidence=confidence, rationale=str(data.get("rationale", "Review the contract manually.")),
        alternatives=alternatives, human_review_required=True,
    )

