# Data2MCP

<div align="center">

[![论文：OpenReview](https://img.shields.io/badge/论文-OpenReview-b31b1b)](https://openreview.net/forum?id=2EeNisg3Xk)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.10-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![MCP](https://img.shields.io/badge/协议-MCP-5b5bd6)](https://modelcontextprotocol.io/)

<p><a href="README.md">English</a> · <a href="README_zh-CN.md">中文</a></p>

<p>Data2MCP 是论文<a href="https://openreview.net/forum?id=2EeNisg3Xk"><em>Structured Strategy Injection for Data Analysis Agents</em></a>的官方配套实现。<br>
它是一个面向数据分析 Agent 的路由编排框架，将异构数据源封装为兼容 MCP 的工具，<br>
通过多轮控制器调度工具调用，并支持结构化分析策略和执行后的合规性检查。</p>

<p><a href="https://openreview.net/forum?id=2EeNisg3Xk">论文</a> · <a href="README.md#quick-start">快速开始</a> · <a href="#策略注入">策略注入</a> · <a href="#配置">配置</a> · <a href="#评测">评测</a> · <a href="#安全">安全</a></p>

<p><strong>项目状态</strong><br>
这是与 OpenReview 论文对应的公开研究版本。核心实现已经发布；benchmark 数据集和外部数据服务需要单独获取和配置。</p>

</div>

## 项目简介

Data2MCP 与论文是一体的项目。论文介绍结构化策略注入方法和 Data2MCP 架构；本仓库提供论文中描述的实现、配置模板、交互式 Demo 和复现实验工具。

当前实现支持关系型数据库、Neo4j 知识图谱、FAISS 文档检索、CSV/JSON Pandas 分析，以及固定、自动选择和自适应生成策略。

## 策略注入

策略由 `StrategySpec` 表示，包含策略 key、策略指令和可观察的输出检查点。路由器支持固定策略、自动选择策略和自适应策略。

系统会验证执行轨迹和最终答案。实现代码位于 `src/data2mcp_v2/server/`，详细说明见：

- [策略注入指南](docs/guides/STRATEGY_INJECTION_IMPLEMENTATION.md)
- [策略提取指南](docs/guides/STRATEGY_EXTRACTION_GUIDE.md)
- [策略验证指南](docs/guides/STRATEGY_VALIDATION_GUIDE.md)

相关 API 包括 `GET /api/strategies`、`POST /api/chat`、`POST /api/extract-strategies` 和 `POST /api/upload-and-extract`。

## 目录结构

`config/` 是 Hydra 配置模板；`data/` 是示例数据和 benchmark 下载说明；`demo/` 是 React/Vite 网页界面；`scripts/` 是 Demo 和评测工具；`src/data2mcp_v2/` 是 Python 核心包；`tests/` 是离线 smoke tests。

仓库不包含大型 benchmark、生成结果、向量索引、日志或第三方 baseline 仓库。

## 环境要求

- Python 3.10 或更高版本；
- Node.js 20 或更高版本；
- 一个兼容 OpenAI API 格式的模型服务。

Neo4j、MySQL、PostgreSQL 和 Elasticsearch 等适配器需要相应的外部服务。

## 安装与运行

创建虚拟环境并安装：`python -m venv .venv`、`source .venv/bin/activate`、`python -m pip install -e .`，然后复制 `.env.example` 为 `.env` 并设置模型服务配置。

启动后端：`python -m data2mcp_v2.server.api --port 2733`。

另开终端启动前端：`cd demo`、`npm ci`、`npm run dev`。访问 `http://localhost:5173`，在配置面板填写模型服务地址和 API Key。

Docker 启动：`cp .env.example .env`，然后执行 `docker compose up --build`。Docker 模式下前端地址为 `http://localhost:5160`，后端地址为 `http://localhost:2734`。

## 配置与评测

Hydra 从 `config/config.yaml` 组合配置，默认使用 `data/examples/sales.sqlite`。可以在 `config/agent/` 中替换数据源，并通过 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL` 提供凭据。

DAComp 和 BIRD MiniDev 实验工具位于 `scripts/`，需要单独下载 benchmark 数据。下载方式和目录结构见 [data/README.md](data/README.md)。

## 测试

安装开发依赖 `python -m pip install -r requirements-dev.txt`，运行 `python -m pytest tests/`。前端检查命令为 `cd demo && npm run lint && npm run build`。

## 安全

当 `allow_dangerous_code: true` 时，DataFrame Agent 可以执行模型生成的 Python 代码，仅应在可信输入和隔离环境中启用。数据库建议使用只读账号。对外暴露 API 前请阅读 [SECURITY.md](SECURITY.md)。

## 引用

请使用 [OpenReview 页面](https://openreview.net/forum?id=2EeNisg3Xk)提供的引用信息。论文标题为 *Structured Strategy Injection for Data Analysis Agents*。

## 许可证

当前发布版本尚未选择许可证。正式公开前请添加 `LICENSE` 文件；在没有许可证的情况下，其他人没有复制、修改或再分发代码的默认权限。
