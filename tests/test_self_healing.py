from api_copilot.self_healing import propose_self_heal, resolve_json_path


def test_missing_camel_case_field_suggests_snake_case_path():
    payload = {"data": {"customer_id": "cus-409"}}

    proposal = propose_self_heal("data.customerId", payload, "string")

    assert proposal.status == "SUGGESTED"
    assert proposal.proposed_path == "data.customer_id"
    assert proposal.human_review_required is True


def test_existing_path_passes_type_check():
    proposal = propose_self_heal("data.orderId", {"data": {"orderId": "ord-1"}}, "string")

    assert proposal.status == "PASS"
    assert proposal.confidence == 1.0


def test_wrong_type_does_not_propose_incompatible_value():
    proposal = propose_self_heal("data.customerId", {"data": {"customer_id": 42, "status": "ok"}}, "string")

    assert proposal.status == "NO_SAFE_REPAIR"
    assert proposal.proposed_path is None


def test_json_path_resolves_array_indices():
    found, value = resolve_json_path({"items": [{"id": "x1"}]}, "$.items[0].id")

    assert found is True
    assert value == "x1"

