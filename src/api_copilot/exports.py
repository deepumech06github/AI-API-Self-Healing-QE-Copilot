"""JSON, CSV, and Python test script exports."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Iterable

from .models import ApiOperation, ApiTestCase
from .generator import generate_pytest_script


def cases_to_json(operations: Iterable[ApiOperation], cases: Iterable[ApiTestCase]) -> str:
    return json.dumps({
        "schema_version": "1.0",
        "project": "AI-API-Self-Healing-QE-Copilot",
        "operations": [operation.to_dict() for operation in operations],
        "test_cases": [case.to_dict() for case in cases],
    }, indent=2, ensure_ascii=False)


def cases_to_csv(cases: Iterable[ApiTestCase]) -> str:
    output = io.StringIO(newline="")
    fields = ["case_id", "category", "operation_id", "method", "path", "title", "request_mutation", "expected_status", "priority", "risk_rationale", "expected_response_fields"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for case in cases:
        row = asdict(case)
        row["request_mutation"] = json.dumps(row["request_mutation"], ensure_ascii=False)
        row["expected_response_fields"] = "; ".join(row["expected_response_fields"])
        writer.writerow(row)
    return output.getvalue()


def pytest_export(cases: Iterable[ApiTestCase]) -> str:
    return generate_pytest_script(cases)

