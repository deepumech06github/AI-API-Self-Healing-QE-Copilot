from pathlib import Path

from api_copilot.generator import generate_test_cases
from api_copilot.openapi import parse_openapi


def test_sample_openapi_parses_and_generates_positive_negative_boundary_cases():
    sample_path = Path(__file__).parents[1] / "examples" / "orders-openapi.yaml"
    operations = parse_openapi(sample_path.read_text(encoding="utf-8"))
    cases = generate_test_cases(operations)

    assert {operation.operation_id for operation in operations} == {"createOrder", "getOrder"}
    assert {case.category for case in cases} == {"Positive", "Negative", "Boundary"}
    assert any(case.category == "Boundary" and "amount" in case.title for case in cases)


def test_invalid_openapi_is_rejected():
    try:
        parse_openapi("openapi: 2.0\npaths: {}")
    except ValueError as exc:
        assert "OpenAPI 3.x" in str(exc)
    else:
        raise AssertionError("Expected invalid OpenAPI input to be rejected")

