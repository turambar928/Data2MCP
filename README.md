# Data2MCP

Data2MCP is the official implementation accompanying the paper
[*Structured Strategy Injection for Data Analysis Agents*](https://openreview.net/forum?id=2EeNisg3Xk).
It is a router-based framework for data analysis agents that exposes
heterogeneous data sources as MCP-compatible tools, dispatches tool calls in a
multi-turn controller, and supports structured analysis strategies with
post-execution compliance checks.

## Associated paper

This repository and the paper are a single project. The paper presents the
structured strategy injection method and the Data2MCP architecture; the code
here provides the implementation, configuration templates, demo interface, and
reproduction utilities described there.

Read the paper on [OpenReview](https://openreview.net/forum?id=2EeNisg3Xk).

The current implementation supports:

- relational databases through SQLAlchemy and text-to-SQL agents;
- knowledge graphs through Neo4j and text-to-Cypher agents;
- document retrieval through FAISS vector stores;
- CSV and JSON analysis through Pandas agents;
- fixed, automatically selected, and adaptively generated analysis strategies;
- a FastAPI backend and a React/Vite configuration and chat interface.

## Repository layout

```text
config/                 Hydra configuration templates
data/                   Example data and benchmark download instructions
demo/                   React/Vite web interface
docs/guides/            Strategy implementation guides
scripts/                Demo and evaluation utilities
src/data2mcp_v2/        Python package
tests/                   Offline smoke tests
```

Large benchmark files, generated outputs, vector indexes, logs, and third-party
baseline repositories are intentionally not included.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer for the web interface
- an OpenAI-compatible chat completion endpoint

Some data source adapters need external services such as Neo4j, MySQL,
PostgreSQL, or Elasticsearch. Install and configure only the services used by
your experiment.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

Set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` in your shell or
`.env`. The checked-in configuration contains no credentials.

## Quick start

The default configuration uses the included SQLite example:

```bash
python -m data2mcp_v2.server.api --port 2733
```

In another terminal:

```bash
cd demo
npm ci
npm run dev
```

Open `http://localhost:5173`, enter the model endpoint and API key in the
configuration panel, and submit an analysis question. The API is available at
`http://localhost:2733`.

The UI stores entered configuration in the browser. Do not use shared browser
profiles for sensitive credentials.

## Configuration

Hydra composes the root configuration from `config/config.yaml`. Data sources
are declared in `config/agent/`; the included default points to
`data/examples/sales.sqlite`. Copy the template and replace the data source
fields for your own deployment.

Credentials can be supplied with OmegaConf environment interpolation:

```yaml
api_key: ${oc.env:OPENAI_API_KEY,''}
base_url: ${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}
model: ${oc.env:OPENAI_MODEL,gpt-4o-mini}
```

DAComp data is not redistributed here. See [data/README.md](data/README.md) for
download and expected directory layout.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/
cd demo && npm run lint && npm run build
```

The smoke tests are offline. Adapter integration tests require their respective
data services and model credentials.

## Security

DataFrame agents can execute model-generated Python when
`allow_dangerous_code: true`. Use that option only with trusted inputs in an
isolated environment. Database users should be read-only. See
[SECURITY.md](SECURITY.md) before exposing the API beyond localhost.

## Citation

Please use the citation information provided by
[the OpenReview record](https://openreview.net/forum?id=2EeNisg3Xk). The paper
title is *Structured Strategy Injection for Data Analysis Agents*.

## License

No license has been selected in this export. Add a `LICENSE` file before making
the repository public; without one, others do not have permission to reuse,
modify, or redistribute the code.
