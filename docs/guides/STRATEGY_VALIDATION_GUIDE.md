# 策略验证系统使用指南

## 概述

该系统可以验证LLM是否真正遵循了选定的检索策略，提供可观测性和质量保证。

## 功能特性

### 1. 后端验证
- ✅ 自动记录所有工具调用
- ✅ 分析调用模式（并行/串行）
- ✅ 针对每种策略的专项检查
- ✅ 生成 0-1 合规评分
- ✅ 详细的违规报告

### 2. 前端显示
- ✅ 实时显示选择的策略
- ✅ 可视化合规度评分
- ✅ 查看详细验证报告
- ✅ 违规警告提示

## 验证指标

### Structured Brainstorming（结构化头脑风暴）
**预期行为**：
- 并行查询比例 > 50%
- 查询至少3个不同工具
- 多轮查询（>= 5次）

**检测标准**：
```python
✅ 并行调用 >= 50% → 全分
⚠️ 并行调用 30-50% → 扣0.2分
❌ 并行调用 < 30% → 扣0.4分

✅ 查询工具 >= 3个 → 全分
⚠️ 查询工具 = 2个 → 扣0.2分
❌ 查询工具 <= 1个 → 扣0.3分
```

### Virtual Brainstorming（虚拟头脑风暴）
**预期行为**：
- 串行调用比例 > 70%
- 多轮迭代（>= 4次）
- 可能重复查询同一工具（深入探索）

**检测标准**：
```python
✅ 串行调用 >= 70% → 全分
⚠️ 串行调用 50-70% → 扣0.2分
❌ 串行调用 < 50% → 扣0.4分

✅ 查询轮次 >= 4 → 全分
⚠️ 查询轮次 < 4 → 扣0.2分
```

### Nominal Group（名义团体法）
**预期行为**：
- 每个工具只查询一次
- 查询至少3个独立工具

**检测标准**：
```python
✅ 每个工具查询1次 → 全分
⚠️ 有工具被重复查询 → 扣0.2分

✅ 查询工具 >= 3个 → 全分
❌ 查询工具 <= 2个 → 扣0.4分
```

### Starbursting (5W1H)
**预期行为**：
- 至少6次查询（对应6个维度）
- 查询至少2个不同工具

**检测标准**：
```python
✅ 查询次数 >= 6 → 全分
⚠️ 查询次数 4-5 → 扣0.2分
❌ 查询次数 < 4 → 扣0.4分
```

## 安装步骤

### 后端修改

1. **已完成**：[strategy_validator.py](../src/data2mcp_v2/server/strategy_validator.py) 已创建

2. **需要手动**：修改 [router.py](../src/data2mcp_v2/server/router.py)

在 `process_query_agentic` 方法中，找到这段代码（约第268行）：

```python
# 生成策略验证报告
if validator:
    report = validator.analyze_pattern()
    report_text = format_validation_report(report)
    logger.info("\n" + report_text)

    # 如果合规分数过低，警告
    if report.compliance_score < 0.5:
        logger.warning(
            f"⚠️ Low strategy compliance ({report.compliance_score:.1%})! "
            f"LLM may not be following '{selected_strategy_key}' strategy correctly."
        )
```

**在它之后添加**（保存验证报告）：

```python
    # 保存报告供API返回
    self.validation_report = {
        "strategy_key": report.strategy_key,
        "strategy_name": report.strategy_name,
        "compliance_score": report.compliance_score,
        "total_tool_calls": report.total_tool_calls,
        "parallel_calls": report.parallel_calls,
        "sequential_calls": report.sequential_calls,
        "distinct_tools": report.distinct_tools,
        "tool_call_pattern": report.tool_call_pattern,
        "compliance_details": report.compliance_details,
        "violations": report.violations
    }
```

3. **需要手动**：修改 [api.py](../src/data2mcp_v2/server/api.py)

在 `/api/chat` endpoint（约第57行），修改返回值：

```python
return {
    "final_text": final_text,
    "messages": message,
    "strategy_used": getattr(router, "strategy_used", ""),
    "validation_report": getattr(router, "validation_report", None),  # ← 新增这一行
}
```

### 前端修改

1. **已完成**：[StrategyValidationBadge.jsx](./components/StrategyValidationBadge.jsx) 已创建

2. **需要手动**：在 App.jsx 中集成

在消息列表上方添加验证徽章（约第280行，ChatMessages组件之前）：

```jsx
import StrategyValidationBadge from './components/StrategyValidationBadge';

// 在组件中添加状态
const [validationReport, setValidationReport] = useState(null);

// 在handleSend中保存验证报告
if (response.ok) {
  // ... 现有代码 ...
  if (data.validation_report) {
    setValidationReport(data.validation_report);
  }
}

// 在渲染部分添加徽章
<ChatMessages ... />
{validationReport && (
  <StrategyValidationBadge
    validationReport={validationReport}
    strategyUsed={data.strategy_used}
    darkMode={darkMode}
  />
)}
```

## 使用方法

### 1. 查看后端日志

启动后端后，每次查询完成会自动打印验证报告：

```bash
python -m data2mcp_v2.server.api
```

查询后会看到：

```
============================================================
📊 Strategy Validation Report: Structured Brainstorming
============================================================
Compliance Score: 85.0% ✅

Execution Statistics:
  • Total tool calls: 8
  • Parallel calls: 5
  • Sequential calls: 3
  • Distinct tools: 4
  • Call pattern: Batch parallel → Sequential

Compliance Checks:
  ✅ High parallel call ratio (>50%)
  ✅ Queried 4 different tools (good coverage)
  ✅ Multiple rounds of queries (thorough exploration)

============================================================
```

### 2. 前端查看

启动前端后：

```bash
cd demo
npm run dev
```

发送查询后，会在聊天界面顶部看到：

- **蓝色徽章**：显示使用的策略名称
- **绿色/黄色/红色徽章**：显示合规度评分
  - ✅ 绿色 (>=70%): 策略执行良好
  - ⚠️ 黄色 (50-70%): 部分遵循策略
  - ❌ 红色 (<50%): 严重偏离策略

点击信息图标可查看详细报告。

## 用于Benchmark测试

### 统计策略遵循度

在你的DAComp测试脚本中，记录每次的合规分数：

```python
compliance_scores = []

for question in dacomp_dataset:
    response = await router.route(question)

    if router.validation_report:
        compliance_scores.append({
            "question": question,
            "strategy": router.strategy_used,
            "score": router.validation_report["compliance_score"],
            "violations": router.validation_report["violations"]
        })

# 分析结果
import pandas as pd
df = pd.DataFrame(compliance_scores)

print("Average compliance by strategy:")
print(df.groupby("strategy")["score"].agg(["mean", "std", "min", "max"]))

print(f"\nLow compliance cases (<50%):")
print(df[df["score"] < 0.5][["question", "strategy", "violations"]])
```

### 发现问题模式

```python
# 哪些类型的问题容易导致策略偏离？
low_compliance = df[df["score"] < 0.6]
print("Problematic question patterns:")
for _, row in low_compliance.iterrows():
    print(f"Q: {row['question'][:100]}...")
    print(f"   Strategy: {row['strategy']}, Score: {row['score']:.1%}")
    print(f"   Violations: {', '.join(row['violations'][:2])}\n")
```

## 调试建议

### 如果合规度低

1. **检查策略提示**：确认策略文本清晰明确
2. **增加温度**：尝试调整LLM temperature（太低可能导致过于保守）
3. **添加示例**：在策略提示中添加具体的执行示例
4. **硬编码控制**：对于关键策略，考虑实现工作流编排（之前讨论的LangGraph方案）

### 如果Auto选择不准确

1. **检查数据摘要**：确认`build_data_summary`返回了足够信息
2. **优化选择提示**：修改 `auto_strategy.py` 中的 `AUTO_STRATEGY_SYSTEM_PROMPT`
3. **人工标注**：在测试集上标注最优策略，计算Auto的准确率

## 下一步优化

1. **可视化工具调用图**：用D3.js绘制工具调用序列
2. **策略推荐系统**：基于历史数据，推荐最适合的策略
3. **A/B测试框架**：自动对比不同策略的效果
4. **强化学习**：让系统学习在什么情况下选择什么策略

## 示例输出

### 好的执行（Structured Brainstorming）

```
Strategy: structured
Compliance: 90%
Pattern: Batch parallel → Sequential

Checks:
  ✅ High parallel call ratio (62.5%)
  ✅ Queried 5 different tools
  ✅ Multiple rounds (8 calls total)

Violations: None
```

### 不好的执行（Structured Brainstorming）

```
Strategy: structured
Compliance: 40%
Pattern: Pure sequential

Checks:
  ❌ Expected parallel queries, found mostly sequential
  ⚠️ Queried 2 tools (limited coverage)
  ⚠️ Few tool calls - may indicate early filtering

Violations:
  • Expected parallel queries but got sequential execution
  • Only queried 2 tools (poor coverage)
```

## 常见问题

**Q: 为什么我的Auto策略一直选择Structured？**
A: 可能是因为大多数查询都需要广泛覆盖。检查`auto_strategy.py`的决策日志，看LLM的理由。

**Q: 验证报告显示100%合规，但结果质量不高？**
A: 合规度只衡量"是否遵循策略"，不衡量"策略是否有效"。需要结合准确率等指标综合评估。

**Q: 能否禁用验证器（提升性能）？**
A: 验证器开销很小（只是记录调用），但如果需要，可以在Router初始化时设置 `validator = None`。
