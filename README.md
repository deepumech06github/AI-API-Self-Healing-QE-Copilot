# AI-API-Self-Healing-QE-Copilot

A portfolio-ready API automation and self-healing demo for quality engineering teams. It generates positive, negative, and boundary API test ideas from an OpenAPI 3.x contract, exports a pytest/requests starter, and proposes type-aware JSON assertion repairs when a response field changes. Offline mode is deterministic and works without API credentials; optional OpenAI assistance is available.

## What it demonstrates

- OpenAPI-based operation discovery and API test design
- Positive, negative, and schema-boundary coverage
- Risk rationale and priorities for test planning
- Export to JSON, CSV, and a pytest starter script
- Explainable, type-aware repair suggestions with an ambiguity threshold
- Human approval before a suggested assertion is used
- Unit tests and GitHub Actions CI

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
streamlit run app.py
```

The sample OpenAPI contract and self-healing payload load by default. No API key is needed for either offline workflow.

## Optional OpenAI repair advisor

Install the optional integration and configure a key in an environment variable or Streamlit secrets. The repair payload is sent to the selected model; use only data allowed by your organization's policy.

```bash
pip install -e ".[llm]"
# macOS / Linux:
export OPENAI_API_KEY="your-key"
# Windows PowerShell:
$env:OPENAI_API_KEY = "your-key"
streamlit run app.py
```

Set `OPENAI_MODEL` to choose another compatible chat-completions model. Never commit a real API key.

## Generated pytest starter

The app exports `test_generated_api.py`, which uses `requests`. Review its sample values and point it at a controlled test API before running:

```bash
$env:API_BASE_URL = "https://your-test-api.example"
pytest test_generated_api.py
```

Path parameters use `API_PARAM_<NAME>` environment variables, such as `API_PARAM_ORDERID`. The generated script is a starter and may need endpoint-specific authentication, fixtures, and request data.

## Run unit tests

```bash
python -m pip install -e ".[dev]"
pytest
```

## Upload to GitHub

1. Extract the project ZIP.
2. Create a repository named `AI-API-Self-Healing-QE-Copilot`.
3. Upload the extracted folder contents, including `.github/workflows/ci.yml`.
4. Commit with a message such as `Add API self-healing QE copilot`.

## Repository map

```text
app.py                              Streamlit dashboard
src/api_copilot/openapi.py          OpenAPI 3 JSON/YAML parser
src/api_copilot/generator.py        API test ideas and pytest starter
src/api_copilot/self_healing.py     JSON assertion repair suggestions
src/api_copilot/llm.py              Optional LLM repair advisor
src/api_copilot/exports.py          JSON, CSV, and script exports
tests/                              Unit tests
examples/orders-openapi.yaml        Fictional sample API contract
docs/architecture.md               Architecture and guardrails
.github/workflows/ci.yml            GitHub Actions checks
```

## Limitations

The OpenAPI reader supports common OpenAPI 3 paths, parameters, JSON request bodies, and JSON responses; it does not resolve external `$ref` definitions. The self-healing matcher works on JSON response paths and is advisory. The generated test file needs environment-specific setup and should be reviewed before use. The app does not call your APIs or change repository files.

## License

MIT. See [LICENSE](LICENSE).

