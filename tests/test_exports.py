import csv
import io
import json
from pathlib import Path

from api_copilot.exports import cases_to_csv, cases_to_json, pytest_export
from api_copilot.generator import generate_test_cases
from api_copilot.openapi import parse_openapi


def _cases_and_operations():
    path = Path(__file__).parents[1] / "examples" / "orders-openapi.yaml"
    operations = parse_openapi(path.read_text(encoding="utf-8"))
    return operations, generate_test_cases(operations)


def test_json_export_contains_generated_cases():
    operations, cases = _cases_and_operations()
    payload = json.loads(cases_to_json(operations, cases))

    assert payload["project"] == "AI-API-Self-Healing-QE-Copilot"
    assert len(payload["test_cases"]) == len(cases)


def test_csv_and_pytest_exports_have_expected_content():
    operations, cases = _cases_and_operations()
    rows = list(csv.DictReader(io.StringIO(cases_to_csv(cases))))
    script = pytest_export(cases)

    assert len(rows) == len(cases)
    assert "requests.request" in script
    assert "API_BASE_URL" in script

