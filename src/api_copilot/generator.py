"""Generate structured API test ideas and a pytest starter script."""

from __future__ import annotations

import json
import re
from typing import Iterable

from .models import ApiOperation, ApiTestCase


def generate_test_cases(operations: Iterable[ApiOperation]) -> list[ApiTestCase]:
    cases: list[ApiTestCase] = []
    index = 1
    for operation in operations:
        cases.append(ApiTestCase(
            case_id=f"API-TC-{index:03d}", category="Positive", operation_id=operation.operation_id,
            method=operation.method, path=operation.path, title=f"{operation.summary}: successful request",
            request_mutation={"payload": operation.request_example, "scenario": "Send a valid request using representative contract data."},
            expected_status=operation.success_status,
            risk_rationale="The primary contract path protects the core client integration and business outcome.", priority="High",
            expected_response_fields=operation.expected_response_fields,
        ))
        index += 1

        mutation = _negative_mutation(operation)
        cases.append(ApiTestCase(
            case_id=f"API-TC-{index:03d}", category="Negative", operation_id=operation.operation_id,
            method=operation.method, path=operation.path, title=f"{operation.summary}: reject invalid or incomplete request",
            request_mutation=mutation, expected_status=operation.client_error_status,
            risk_rationale="Validation gaps can admit invalid state or return inconsistent errors to API consumers.", priority="High",
            expected_response_fields=[],
        ))
        index += 1

        if operation.numeric_boundaries:
            for boundary in operation.numeric_boundaries[:2]:
                field = boundary["field"]
                for bound_name in ("minimum", "maximum"):
                    bound_value = boundary.get(bound_name)
                    if bound_value is None:
                        continue
                    payload = dict(operation.request_example or {})
                    payload[field] = bound_value
                    cases.append(ApiTestCase(
                        case_id=f"API-TC-{index:03d}", category="Boundary", operation_id=operation.operation_id,
                        method=operation.method, path=operation.path, title=f"{operation.summary}: {field} at {bound_name}",
                        request_mutation={"payload": payload, "field": field, "value": bound_value, "scenario": f"Verify the documented {bound_name} value is accepted; also try one representable value beyond it and expect validation."},
                        expected_status=operation.success_status,
                        risk_rationale="Contract boundaries are common sources of off-by-one errors and inconsistent client behavior.", priority="Medium",
                        expected_response_fields=operation.expected_response_fields,
                    ))
                    index += 1
        else:
            cases.append(ApiTestCase(
                case_id=f"API-TC-{index:03d}", category="Boundary", operation_id=operation.operation_id,
                method=operation.method, path=operation.path, title=f"{operation.summary}: identifier boundary",
                request_mutation={"scenario": "Try an empty, malformed, unknown, and maximum-length identifier where applicable."},
                expected_status=operation.client_error_status,
                risk_rationale="Malformed or unknown identifiers should fail predictably without leaking implementation details.", priority="Medium",
                expected_response_fields=[],
            ))
            index += 1
    return cases


def _negative_mutation(operation: ApiOperation) -> dict:
    if operation.required_body_fields:
        payload = dict(operation.request_example or {})
        omitted = operation.required_body_fields[0]
        payload.pop(omitted, None)
        return {"payload": payload, "omitted_required_field": omitted, "scenario": f"Omit required body field `{omitted}` and confirm a contract-compliant 4xx response."}
    if operation.required_parameters:
        return {"omitted_required_parameter": operation.required_parameters[0], "scenario": "Omit a required parameter and confirm a contract-compliant 4xx response."}
    return {"scenario": "Send malformed JSON or an unsupported content type and confirm a contract-compliant 4xx response."}


def generate_pytest_script(cases: Iterable[ApiTestCase]) -> str:
    """Create a reviewable pytest/requests starter for positive cases."""

    positive = [case for case in cases if case.category == "Positive"]
    rows = [{"id": case.case_id, "operation_id": case.operation_id, "method": case.method, "path": case.path,
             "payload": case.request_mutation.get("payload"), "expected_status": case.expected_status}
            for case in positive]
    rows_json = json.dumps(rows, indent=2, ensure_ascii=False)
    rows_json = "\n".join("    " + line for line in rows_json.splitlines())
    return f'''"""Generated API smoke-test starter. Review paths and sample data before use."""
import os
import re

import pytest
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
CASES = {rows_json}


def resolve_path(template: str) -> str:
    def replace(match):
        name = match.group(1)
        return os.getenv(f"API_PARAM_{{name.upper()}}", f"sample-{{name}}")
    return re.sub(r"\{{([^{{}}]+)\}}", replace, template)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_generated_api_smoke(case):
    url = BASE_URL + resolve_path(case["path"])
    response = requests.request(
        case["method"], url, json=case["payload"], timeout=15,
    )
    assert response.status_code == case["expected_status"], response.text[:500]
'''

