# 策略注入实现文档

本文档详细描述 data2mcp_v2 系统中分析策略（Retrieval Strategy）的完整注入流程，从实验脚本到最终答案的每个环节。

---

## 整体架构概览

```
实验脚本 (run_strategy_experiment.py)
    ↓ 构建含 strategy_full_text 的 config
后端 API (api.py)
    ↓ 传递给 Router
Router (router.py)
    ↓ 1. 策略选择（手动 / 自动 / 无）
    ↓ 2. 注入 System Prompt
    ↓ 3. Agent 执行循环
    ↓ 4. 过程验证（StrategyValidator）
    ↓ 5. 产出验证 + Refinement（OutputValidator）
最终答案
```

---

## 第一步：策略来源

策略有两个来源，在运行时合并使用：

| 类型 | 内置策略（hard-coded） | 提取策略（PDF 提取） |
|------|----------------------|-------------------|
| 存储位置 | `run_strategy_experiment.py` 的 `load_strategy_map()` | `config/extracted_strategies.json` |
| 示例 | Structured Brainstorming, Virtual Brainstorming, Nominal Group, Starbursting | CRISP-DM, 假设生成, 竞争假说分析… |
| 字段 | `key`, `name`, `full_text`, `checkpoints=[]` | `key`, `name`, `description`, `full_text`, `checkpoints`, `source` |

### 内置策略一览

| key | name | 核心思路 |
|-----|------|---------|
| `structured` | Structured Brainstorming | 并行查询所有数据源，先覆盖后聚合 |
| `virtual` | Virtual Brainstorming | 迭代式查询，每轮独立反思后再查 |
| `nominal` | Nominal Group | 每个数据源独立查询一次，聚合后排序 |
| `starbursting` | Starbursting (5W1H) | 问题拆解为 Who/What/When/Where/Why/How 六维度分别查询 |

### CRISP-DM 策略定义（当前实验所用）

```json
{
  "key": "crisp_dm",
  "name": "CRISP-DM",
  "description": "A structured framework for data mining projects with phases and tasks.",
  "full_text": "Begin by understanding the business objectives and success criteria. Collect and describe initial data, ensuring data quality. Prepare data by cleaning, constructing, integrating, and formatting it. Select modeling techniques and build models, assessing their performance. Evaluate results against business success criteria and plan deployment, monitoring, and maintenance. Document the entire process and review project experience.",
  "checkpoints": [
    "includes phases: Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment",
    "lists outputs for each phase, such as 'Data Description Report' and 'Model Assessment'",
    "states assumptions before drawing conclusions",
    "contains a project plan with initial assessment of tools and techniques",
    "documents review of process and project experience"
  ],
  "source": "crisp-dm.pdf"
}
```

---

## 第二步：Config 构建（实验脚本 → Router）

`build_config()` 函数（`run_strategy_experiment.py:157`）将策略信息打包进 config 字典：

```python
{
  "retrieval_strategy": strategy_full_text,   # 策略全文（注入到 system prompt）
  "strategy_key": strategy_key,               # 策略 key（如 "crisp_dm"）
  "auto_select_strategy": False,              # 手动指定时为 False
  "max_turns": 30,
  "max_refinement_rounds": 0,
  ...
}
```

### 三种运行模式对比

| 条件 | `strategy_key` | `retrieval_strategy` | `auto_select_strategy` |
|------|---------------|---------------------|----------------------|
| Baseline（对照组） | `""` | `""` | `False` |
| 手动策略（如 crisp_dm） | `"crisp_dm"` | CRISP-DM 全文 | `False` |
| 自动选择 | `""` | `""` | `True` |

---

## 第三步：System Prompt 注入（Router）

在 `router.py:138` 的 `route()` 方法中，策略全文被嵌入 system prompt 的固定位置：

```
You are a professional data analyst. You retrieve and synthesize answers
from databases using the data tools available to you.

---

# 🎯 Retrieval Strategy (MUST FOLLOW)

{strategy_full_text}          ← CRISP-DM 全文插入此处

---

# 📊 Data Analysis Requirements
...（后续固定 prompt 内容）
```

- **有策略时**：`strategy_section` 包含完整策略文本，LLM 在执行前看到并遵循
- **Baseline（无策略）**：`strategy_section = ""`，该区块直接为空，LLM 无任何策略约束

相关代码（`router.py:136-156`）：

```python
strategy_section = ""
if retrieval_strategy_text:
    strategy_section = f"""

---

# 🎯 Retrieval Strategy (MUST FOLLOW)

{retrieval_strategy_text}

---
"""

messages = [
    {
        "role": "system",
        "content": SYS_PROMPT.format(
            stop_tools=self.end_tool,
            retrieval_strategy_section=strategy_section
        ),
    }
]
```

---

## 第四步：自动策略选择（仅 auto 模式）

当 `auto_select_strategy=True` 时，`select_retrieval_strategy()`（`auto_strategy.py`）执行以下流程：

1. 加载所有可用策略（内置 + `extracted_strategies.json` 提取策略）
2. 构建当前数据源摘要（表名、行数、列名）
3. 调用 LLM，传入用户问题 + 数据源摘要 + 策略列表
4. LLM 返回 JSON `{"strategy": "key", "reason": "..."}`
5. 取对应策略的 `full_text` 注入 system prompt

```python
# auto_strategy.py:63-88（简化）
selected_key, retrieval_strategy_text = select_retrieval_strategy(
    query=query,
    config=self.config,
    chat=self.llm,
    candidates=all_strategies,
)
```

---

## 第五步：过程验证（StrategyValidator）

Agent 执行过程中，每次工具调用都被记录（`router.py:228`）：

```python
validator.record_tool_call(tool_name, tool_calls_total, is_parallel_batch)
```

执行结束后，`validator.analyze_pattern()` 分析工具调用模式，输出 `compliance_score`（0~1）：

### 各策略的过程验证规则

| 策略 | 验证维度 | 满分条件 |
|------|---------|---------|
| `structured` | 并行率、工具数量、总调用次数 | 并行率≥50%、≥3种工具、≥5次调用 |
| `virtual` | 串行率、轮次数量、重复查询 | 串行率≥70%、≥4轮、有重复查询同一工具 |
| `nominal` | 每工具调用次数、工具总数 | 每工具只查一次、覆盖≥3个工具 |
| `starbursting` | 总调用次数、工具种类 | ≥6次查询（对应6维度）、≥2种工具 |
| **`crisp_dm`（及其他提取策略）** | 无特定规则 | 走 `_generic_report()`，直接得分 **1.0** |

> **注**：CRISP-DM 属于从 PDF 提取的策略，`strategy_validator.py` 中无对应 `_validate_crisp_dm()` 方法，因此走 generic 路径，**过程合规分恒为 1.0**，不影响实验执行。

---

## 第六步：产出验证 + Refinement（OutputValidator）

Agent 执行完成后，使用 LLM 对最终答案做 checkpoint 检查（`router.py:371-418`）：

```python
ov = OutputValidator(self._active_spec, self.llm)
ov_report = ov.validate(current_answer)
output_compliance_score = ov_report.compliance_score
```

### CRISP-DM 的 5 个 Checkpoint

1. 包含六个阶段（Business Understanding / Data Understanding / Data Preparation / Modeling / Evaluation / Deployment）
2. 列出各阶段产出物（如 Data Description Report、Model Assessment）
3. 结论前有假设前置声明
4. 包含项目计划（工具与技术初步评估）
5. 文档化过程回顾与经验总结

### Refinement 循环

若 `compliance_score < 0.7` 且 `max_refinement_rounds > 0`：

```
失败 checkpoint 列表 → 注入反馈 message → 重新调用 LLM 修改答案（禁止再查数据）→ 再次验证
```

> **当前实验设置 `max_refinement_rounds=0`，不启用 refinement**，仅做单次验证记录。

---

## 关键参数汇总

| 参数 | 当前实验值 | 作用 |
|------|-----------|------|
| `max_turns` | 30 | 最大工具调用轮数 |
| `max_refinement_rounds` | **0** | 产出验证后不做 refinement（仅记录分数）|
| `auto_select_strategy` | `False` | 固定用指定策略，不自动选 |
| `strategy_key` | `crisp_dm` | 决定产出 checkpoint 验证规则 |
| `tool_call_timeout` | 600s | 单次工具调用超时 |
| `tool_call_max_length` | 10000 | 工具返回结果最大字符数 |

---

## 相关文件索引

| 文件 | 职责 |
|------|------|
| `data/benchmark/DAComp/run_strategy_experiment.py` | 实验入口，构建 config，逐题运行 |
| `src/data2mcp_v2/server/router.py` | 核心编排：策略注入、Agent 循环、验证 |
| `src/data2mcp_v2/server/prompt.py` | System prompt 模板（含 `{retrieval_strategy_section}` 占位符）|
| `src/data2mcp_v2/server/auto_strategy.py` | 自动策略选择逻辑（LLM 选 key）|
| `src/data2mcp_v2/server/strategy_validator.py` | 过程验证：分析工具调用模式合规性 |
| `src/data2mcp_v2/server/output_validator.py` | 产出验证：LLM 检查答案是否满足 checkpoints |
| `src/data2mcp_v2/server/strategy_catalog.py` | 策略注册表，合并内置与提取策略 |
| `config/extracted_strategies.json` | 从 PDF 提取的策略库（含 CRISP-DM）|
