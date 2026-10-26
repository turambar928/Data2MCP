<h1 align="center">Data2MCP</h1>

<div align="center">

[![Paper: Findings of EMNLP 2026](https://img.shields.io/badge/Paper-Findings_of_EMNLP_2026-b31b1b)](https://aclanthology.org/2026.findings-emnlp.1279/)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.10-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-5b5bd6)](https://modelcontextprotocol.io/)

<p><a href="README.md">English</a> · <a href="README_zh-CN.md">中文</a></p>

<p>Official implementation of<br>
<em>Structured Strategy Injection for Data Analysis Agents</em>.</p>

<p><a href="#quick-start">Quick start</a> · <a href="#strategy-injection">Strategy injection</a> · <a href="#configuration">Configuration</a> · <a href="#evaluation">Evaluation</a> · <a href="#security">Security</a> · <a href="#citation">Citation</a></p>

</div>

## Overview

Data2MCP is a router-based framework for data analysis agents. It exposes
heterogeneous data sources as MCP-compatible tools, coordinates multi-turn
tool calls, and supports structured analysis strategies with post-execution
validation.

The current implementation supports:

- relational databases through SQLAlchemy and text-to-SQL agents;
- knowledge graphs through Neo4j and text-to-Cypher agents;
- document retrieval through FAISS vector stores;
- CSV and JSON analysis through Pandas agents;
- fixed, automatically selected, and adaptively generated analysis strategies;
- a FastAPI backend and a React/Vite configuration and chat interface.

## Architecture

```text
Natural-language query
          |
          v
  Strategy module  ---- fixed / auto-selected / adaptive strategy
          |
          v
        Router  ------ multi-turn tool dispatch and synthesis
          |
          v
  MCP-compatible data tools
  SQL | Neo4j | FAISS | Pandas
          |
          v
 Strategy + output validators
```

The strategy module controls the analytical procedure, while the Data2MCP
router coordinates execution across data sources.

## Strategy injection

Strategies are represented as `StrategySpec` objects containing a key, an
instruction, and observable output checkpoints. The Router supports three modes:

- **Fixed**: set `strategy_key` or provide a strategy instruction explicitly.
- **Auto-selected**: set `auto_select_strategy: true` or use `retrieval_strategy: auto`.
- **Adaptive**: generate a task-specific strategy from the query and data summary.

The implementation also validates execution traces and the final answer. See
the [injection guide](docs/guides/STRATEGY_INJECTION_IMPLEMENTATION.md),
[extraction guide](docs/guides/STRATEGY_EXTRACTION_GUIDE.md), and
[validation guide](docs/guides/STRATEGY_VALIDATION_GUIDE.md).

Relevant API endpoints are `GET /api/strategies`, `POST /api/chat`,
`POST /api/extract-strategies`, and `POST /api/upload-and-extract`.

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

### Docker

```bash
cp .env.example .env
docker compose up --build
```

The backend is exposed on `http://localhost:2734` and the frontend on
`http://localhost:5160`.

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

## Evaluation

The release includes utilities for DAComp and BIRD MiniDev experiments under
`scripts/`. These scripts expect the corresponding benchmark files and a
running API endpoint; they do not download data or call a model by default.
Start with [data/README.md](data/README.md), then inspect the script `--help`
output before running an experiment.

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

If you use Data2MCP in your research, please cite:

```bibtex
@inproceedings{tao-etal-2026-structured,
    title = "Structured Strategy Injection for Data Analysis Agents",
    author = "Tao, Zifu  and
      Mo, Guozhao  and
      Zhou, Weixiang  and
      Lu, Yaojie  and
      Lin, Hongyu  and
      He, Ben  and
      Han, Xianpei  and
      Sun, Le",
    editor = "Lee, Hung-Yi  and
      Dev, Sunipa  and
      Li, Jessy  and
      Elliott, Desmond",
    booktitle = "Findings of the {A}ssociation for {C}omputational {L}inguistics: {EMNLP} 2026",
    month = oct,
    year = "2026",
    address = "Budapest, Hungary",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2026.findings-emnlp.1279/",
    pages = "27100--27123",
    ISBN = "979-8-89176-462-0",
    abstract = "Data analysis agents often produce shallow or non-auditable summaries because they lack the explicit reasoning frameworks and validation habits used by domain experts, especially when evidence must be gathered across heterogeneous data sources. We propose structured strategy injection, which injects compact methodology specifications with explicit checkpoints into an agent{'}s controller context, turning expert workflows into executable plans and enabling compliance-based transparency. To make such methodology-driven planning executable and auditable in heterogeneous settings, we introduce Data2MCP, a router-based orchestration infrastructure that standardizes SQL databases, knowledge graphs, vector stores, and tables as MCP-compatible tools and routes queries dynamically for multi-source retrieval and join-like reasoning. We compare Data2MCP against a RAG baseline and DA-Agent across multi-source retrieval, DAComp, and BIRD MiniDev. In multi-source retrieval, Data2MCP outperforms DA-Agent, and strategy injection benefits both architectures. On DAComp, strategy injection improves DA-Agent from 50.84 to 57.17 (+6.33). The code is available at https://github.com/turambar928/Data2MCP."
}
```

## License

No license has been selected in this export. Add a `LICENSE` file before making
the repository public; without one, others do not have permission to reuse,
modify, or redistribute the code.
