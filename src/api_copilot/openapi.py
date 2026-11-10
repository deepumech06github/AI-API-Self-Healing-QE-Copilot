"""Parse a practical subset of OpenAPI 3 JSON or YAML documents."""

from __future__ import annotations

import json
from typing import Any

import yaml

from .models import ApiOperation


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def parse_openapi(document_text: str) -> list[ApiOperation]:
    """Parse OpenAPI operations into a compact model used by the demo."""

    if not document_text.strip():
        raise ValueError("Paste or upload an OpenAPI 3.x document first.")
    try:
        try:
            spec = json.loads(document_text)
        except json.JSONDecodeError:
            spec = yaml.safe_load(document_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Could not parse the OpenAPI document: {exc}") from exc
    if not isinstance(spec, dict) or not str(spec.get("openapi", "")).startswith("3."):
        raise ValueError("Expected an OpenAPI 3.x JSON or YAML document.")
    paths = spec.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError("The OpenAPI document has no `paths` entries.")

    operations: list[ApiOperation] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters", [])
        for method, operation in path_item.items():
            method_lower = str(method).lower()
            if method_lower not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            parameters = list(path_parameters or []) + list(operation.get("parameters", []) or [])
            required_parameters = [
                str(parameter.get("name", "parameter"))
                for parameter in parameters
                if isinstance(parameter, dict) and parameter.get("required") is True
            ]
            body_schema, body_required = _request_schema(operation.get("requestBody", {}))
            body_fields = [str(name) for name in (body_schema.get("required", []) or [])]
            numeric = _numeric_boundaries(body_schema)
            request_example = _make_example(body_schema) if body_schema else None
            responses = operation.get("responses", {}) or {}
            success_codes = sorted(int(code) for code in responses if str(code).isdigit() and 200 <= int(code) < 300)
            error_codes = sorted(int(code) for code in responses if str(code).isdigit() and 400 <= int(code) < 500)
            success_status = success_codes[0] if success_codes else (201 if method_lower == "post" else 200)
            client_error_status = error_codes[0] if error_codes else 400
            response_schema = _success_response_schema(responses, success_status)
            operation_id = str(operation.get("operationId") or f"{method_lower}_{_slug(path)}")
            operations.append(ApiOperation(
                operation_id=operation_id,
                method=method_lower.upper(),
                path=str(path),
                summary=str(operation.get("summary") or operation.get("description") or operation_id),
                required_parameters=required_parameters,
                required_body_fields=body_fields if body_required else [],
                numeric_boundaries=numeric,
                request_example=request_example,
                success_status=success_status,
                client_error_status=client_error_status,
                expected_response_fields=_flatten_schema(response_schema),
            ))
    if not operations:
        raise ValueError("No supported HTTP operations were found in the OpenAPI paths.")
    return operations


def _request_schema(request_body: Any) -> tuple[dict[str, Any], bool]:
    if not isinstance(request_body, dict):
        return {}, False
    content = request_body.get("content", {}) or {}
    for media_type in ("application/json", "application/*+json"):
        media = content.get(media_type)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"], bool(request_body.get("required"))
    for media in content.values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"], bool(request_body.get("required"))
    return {}, bool(request_body.get("required"))


def _success_response_schema(responses: dict[str, Any], status: int) -> dict[str, Any]:
    response = responses.get(str(status), {}) or responses.get(status, {}) or {}
    content = response.get("content", {}) if isinstance(response, dict) else {}
    for media in (content or {}).values():
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"]
    return {}


def _numeric_boundaries(schema: dict[str, Any]) -> list[dict[str, Any]]:
    boundaries = []
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    for name, detail in (properties or {}).items():
        if isinstance(detail, dict) and detail.get("type") in {"integer", "number"} and ("minimum" in detail or "maximum" in detail):
            boundaries.append({"field": str(name), "type": detail["type"], "minimum": detail.get("minimum"), "maximum": detail.get("maximum")})
    return boundaries


def _make_example(schema: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return None
    required = set(schema.get("required", []) or [])
    properties = schema.get("properties", {}) or {}
    values = {name: _example_value(detail) for name, detail in properties.items() if not required or name in required}
    return values or None


def _example_value(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return "sample"
    if "example" in schema:
        return schema["example"]
    if schema.get("enum"):
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "string":
        return "user@example.com" if schema.get("format") == "email" else "sample"
    if kind == "integer":
        return schema.get("minimum", 1)
    if kind == "number":
        return schema.get("minimum", 1.0)
    if kind == "boolean":
        return True
    if kind == "array":
        return [_example_value(schema.get("items", {}))]
    if kind == "object":
        properties = schema.get("properties", {}) or {}
        required = set(schema.get("required", []) or [])
        return {key: _example_value(value) for key, value in properties.items() if not required or key in required}
    return None


def _flatten_schema(schema: dict[str, Any], prefix: str = "") -> list[str]:
    if not isinstance(schema, dict):
        return []
    output = []
    for name, child in (schema.get("properties", {}) or {}).items():
        path = f"{prefix}.{name}" if prefix else str(name)
        if isinstance(child, dict) and child.get("type") == "object":
            output.extend(_flatten_schema(child, path))
        else:
            output.append(path)
    return output


def _slug(path: str) -> str:
    return "_".join(part.strip("{}") for part in path.strip("/").replace("/", "_").split("_") if part) or "root"

