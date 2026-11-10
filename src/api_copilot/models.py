"""Data models shared by the OpenAPI generator and repair advisor."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ApiOperation:
    operation_id: str
    method: str
    path: str
    summary: str
    required_parameters: list[str]
    required_body_fields: list[str]
    numeric_boundaries: list[dict[str, Any]]
    request_example: dict[str, Any] | None
    success_status: int
    client_error_status: int
    expected_response_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApiTestCase:
    case_id: str
    category: str
    operation_id: str
    method: str
    path: str
    title: str
    request_mutation: dict[str, Any]
    expected_status: int
    risk_rationale: str
    priority: str
    expected_response_fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepairProposal:
    status: str
    original_path: str
    proposed_path: str | None
    confidence: float
    rationale: str
    alternatives: list[dict[str, Any]]
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

