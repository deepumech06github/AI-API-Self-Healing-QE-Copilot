"""Streamlit interface for API test generation and review-first self-healing."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from api_copilot.exports import cases_to_csv, cases_to_json, pytest_export
from api_copilot.llm import suggest_repair_with_llm
from api_copilot.openapi import parse_openapi
from api_copilot.self_healing import propose_self_heal, resolve_json_path
from api_copilot.generator import generate_test_cases


def _api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "")
    try:
        key = key or st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    return key or None


SAMPLE_SPEC = (Path(__file__).parent / "examples" / "orders-openapi.yaml").read_text(encoding="utf-8")
SAMPLE_PAYLOAD = json.dumps({"data": {"orderId": "ord-2001", "status": "confirmed", "customer_id": "cus-409"}}, indent=2)

st.set_page_config(page_title="AI API Self-Healing QE Copilot", page_icon="🔧", layout="wide")
st.title("🔧 AI API Self-Healing QE Copilot")
st.caption("Generate API checks from OpenAPI and review suggested assertion repairs when responses drift.")

generator_tab, healing_tab, about_tab = st.tabs(["OpenAPI test generator", "Self-healing sandbox", "About & architecture"])

with generator_tab:
    st.subheader("OpenAPI contract to automation starter")
    uploaded = st.file_uploader("Upload OpenAPI JSON or YAML (optional)", type=["json", "yaml", "yml"])
    if uploaded is not None:
        uploaded_spec = uploaded.getvalue().decode("utf-8-sig")
        if st.session_state.get("_loaded_uploaded_spec") != uploaded_spec:
            st.session_state["openapi_spec_text"] = uploaded_spec
            st.session_state["_loaded_uploaded_spec"] = uploaded_spec
    if "openapi_spec_text" not in st.session_state:
        st.session_state["openapi_spec_text"] = SAMPLE_SPEC
    spec_text = st.text_area("OpenAPI 3.x document", key="openapi_spec_text", height=300)
    if st.button("Generate API test cases", type="primary"):
        try:
            operations = parse_openapi(spec_text)
            cases = generate_test_cases(operations)
            st.session_state["api_operations"] = operations
            st.session_state["api_cases"] = cases
        except Exception as exc:
            st.error(str(exc))

    operations = st.session_state.get("api_operations", [])
    cases = st.session_state.get("api_cases", [])
    if operations and cases:
        st.divider()
        counts = {kind: sum(case.category == kind for case in cases) for kind in ("Positive", "Negative", "Boundary")}
        metrics = st.columns(4)
        metrics[0].metric("Operations", len(operations))
        metrics[1].metric("Test ideas", len(cases))
        metrics[2].metric("Negative", counts["Negative"])
        metrics[3].metric("Boundary", counts["Boundary"])
        st.markdown("**Discovered operations**")
        st.dataframe([{"Operation ID": op.operation_id, "Method": op.method, "Path": op.path, "Summary": op.summary} for op in operations], use_container_width=True, hide_index=True)
        st.markdown("**Generated test ideas**")
        st.dataframe([{"ID": case.case_id, "Type": case.category, "Operation": case.operation_id, "Title": case.title, "Expected status": case.expected_status, "Priority": case.priority} for case in cases], use_container_width=True, hide_index=True)
        for case in cases:
            with st.expander(f"{case.case_id} · {case.title}"):
                st.json(case.to_dict())
        st.download_button("Download JSON", cases_to_json(operations, cases), "api-test-plan.json", "application/json")
        st.download_button("Download CSV", cases_to_csv(cases), "api-test-plan.csv", "text/csv")
        st.download_button("Download pytest starter", pytest_export(cases), "test_generated_api.py", "text/x-python")
        st.info("The exported pytest script is a starter. Set API_BASE_URL and review sample path values and request data before running it against an API.")

with healing_tab:
    st.subheader("Find a safe assertion repair proposal")
    st.write("Simulate a response field rename. The advisor will check the assertion, suggest a similar field only when evidence is strong, and wait for a human to accept it.")
    path = st.text_input("Expected JSON path", value="data.customerId", key="healing_path")
    expected_type = st.selectbox("Expected value type", ["string", "integer", "number", "boolean", "object", "array", "Any"])
    payload_text = st.text_area("Observed API response JSON", value=SAMPLE_PAYLOAD, height=220)
    repair_mode = st.radio("Repair advisor", ["Offline explainable matcher", "OpenAI LLM"], horizontal=True)
    if st.button("Check and suggest repair", type="primary"):
        try:
            payload = json.loads(payload_text)
            expected = None if expected_type == "Any" else expected_type
            proposal = propose_self_heal(path, payload, expected)
            if repair_mode == "OpenAI LLM":
                proposal = suggest_repair_with_llm(path, payload, expected, api_key=_api_key())
            st.session_state["repair_proposal"] = proposal
        except Exception as exc:
            st.error(str(exc))

    proposal = st.session_state.get("repair_proposal")
    if proposal:
        st.divider()
        if proposal.status == "PASS":
            st.success("The assertion path still resolves with the expected value type.")
        elif proposal.status == "SUGGESTED":
            st.warning("A likely path repair is available. Review the contract and sample response before accepting.")
        else:
            st.error("No safe automatic suggestion was found; keep the assertion failing and investigate the contract change.")
        st.markdown(f"**Status:** {proposal.status}  ·  **Confidence:** {proposal.confidence:.0%}")
        st.markdown(f"**Rationale:** {proposal.rationale}")
        if proposal.proposed_path:
            st.markdown(f"**Original:** `{proposal.original_path}`  →  **Suggested:** `{proposal.proposed_path}`")
        if proposal.alternatives:
            st.dataframe(proposal.alternatives, use_container_width=True, hide_index=True)
        if proposal.status == "SUGGESTED" and st.button("Accept suggestion for this session", key="accept_repair"):
            st.session_state["accepted_assertion_path"] = proposal.proposed_path
        accepted = st.session_state.get("accepted_assertion_path")
        if accepted:
            st.success(f"Working assertion path for this session: {accepted}")
            try:
                result = resolve_json_path(json.loads(payload_text), accepted)
                st.json({"path": accepted, "value_found": result[0], "value": result[1]})
            except json.JSONDecodeError:
                pass
        st.caption("Acceptance changes only the in-app demo state. It does not edit a repository or test file.")

with about_tab:
    st.subheader("Quality engineering signal")
    st.markdown("""
    This portfolio project demonstrates contract-based API test design and a controlled self-healing workflow:

    - Parse OpenAPI 3.x JSON or YAML into operations and response expectations.
    - Generate positive, negative, and boundary test ideas with risk context.
    - Export a reviewable test plan and pytest/requests starter.
    - Detect a broken JSON assertion and propose a type-aware, similarity-based replacement.
    - Require human acceptance before a repair becomes the working assertion.

    The demo does not run tests against your services or modify test code automatically. Offline mode runs without credentials; optional OpenAI mode sends the supplied example payload to the configured model.
    """)
    st.markdown("**Architecture:** OpenAPI document → operation model → test plan and script; observed response + failed assertion → repair advisor → human review. See `docs/architecture.md`.")

