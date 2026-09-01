import asyncio
import json
import logging
import re
import uuid

from fastmcp.tools import Tool

from data2mcp_v2.config import Data2McpConfig
from data2mcp_v2.server.auto_strategy import select_retrieval_strategy
from data2mcp_v2.server.strategy_catalog import DEFAULT_STRATEGIES, load_strategies
from data2mcp_v2.server.data_tools.db import init_db_agents
from data2mcp_v2.server.output_validator import OutputValidator, format_output_validation_report
from data2mcp_v2.server.prompt import SYS_PROMPT
from data2mcp_v2.server.strategy_validator import StrategyValidator, format_validation_report
from data2mcp_v2.utils.llm_api import ChatModel
from data2mcp_v2.utils.tools import end_with_message

logger = logging.getLogger(__name__)


def pretty_message_log(message):
    role = message.get("role", "unknown")
    content = message.get("content", "").strip()
    reasoning = message.get("reasoning_content", "").strip()
    if content:
        content = f"[Content]: {content}\n"
    if reasoning:
        content += f"[Reasoning]: {reasoning}\n"
    logger.debug(f"\n[Role]: {role}\n{content}{'-' * 40}")


class Router:
    def __init__(
        self,
        config: Data2McpConfig,
    ):
        self.config = config
        self.tools: list[Tool] = []
        self.tools += init_db_agents(config.agents)
        end_tool = end_with_message()
        self.tools.append(end_tool)
        # end tool指的是直接结束的动作，stop tool可能是其他有意义的动作，但是也会导致结束条件
        self.end_tool = end_tool.name
        self.stop_tools = [end_tool.name]
        self.min_tool_calls = config.min_tool_calls
        # 追踪信息增益：累积去重词数、使用过的工具集合
        self.info_tokens: set[str] = set()
        self.distinct_tools: set[str] = set()
        self.strategy_used = ""
        self._active_spec = None  # StrategySpec for current query, set in process_query_agentic
        # 追踪图表生成调用次数和路径
        self.chart_generation_count = 0
        self.generated_chart_paths: list[str] = []  # 收集本次生成的图表绝对路径
        self.llm = ChatModel(
            model_name=config.llm.model,
            model_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            timeout=config.llm.timeout_seconds,
        )

    def _should_require_charts(self, query: str) -> bool:
        """
        检测查询是否需要生成图表

        Args:
            query: 用户查询

        Returns:
            True if charts should be required
        """
        # 数据分析相关关键词
        analysis_keywords = [
            "分析", "趋势", "对比", "增长", "市场份额", "统计",
            "可视化", "图表", "growth", "trend", "analysis", "compare",
            "visualization", "chart", "market share", "statistics",
            "季度", "月度", "年度", "业绩", "表现", "performance",
            "quarterly", "monthly", "annual", "revenue", "profit"
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in analysis_keywords)

    async def route(self, query: str):
        if self.config.route_type == "agentic":
            final_text, messages = await self.process_query_agentic(query)
        return final_text, messages

    async def process_query_agentic(
        self,
        query: str,
    ):
        # 重置图表生成计数器和路径列表
        self.chart_generation_count = 0
        self.generated_chart_paths = []

        # 后端自动策略选择
        retrieval_strategy_text = self.config.retrieval_strategy or ""
        selected_strategy_key = ""
        auto_enabled = self.config.auto_select_strategy or (
            retrieval_strategy_text.strip().lower() == "auto"
        )
        if auto_enabled:
            # Merge built-in + extracted strategies for selection
            all_strategies = load_strategies()
            candidates = None
            if self.config.auto_strategy_candidates:
                candidates = {
                    key: all_strategies[key]
                    for key in self.config.auto_strategy_candidates
                    if key in all_strategies
                }
            else:
                candidates = all_strategies
            selected_key, retrieval_strategy_text = select_retrieval_strategy(
                query=query,
                config=self.config,
                chat=self.llm,
                candidates=candidates,
            )
            selected_strategy_key = selected_key
            logger.info("🎯 Auto strategy selected: %s", selected_key)
        if not selected_strategy_key and retrieval_strategy_text:
            # 优先用 config 里显式指定的 strategy_key（实验脚本传入）
            explicit_key = getattr(self.config, "strategy_key", "")
            selected_strategy_key = explicit_key if explicit_key else "manual"
        self.strategy_used = selected_strategy_key

        # 保存当前策略 spec，供产出验证使用
        all_strats = load_strategies()
        self._active_spec = all_strats.get(selected_strategy_key)

        # 初始化策略验证器
        validator = StrategyValidator(selected_strategy_key) if selected_strategy_key else None

        # 构建策略部分
        strategy_section = ""
        if retrieval_strategy_text:
            strategy_section = f"""

---

# 🎯 Retrieval Strategy (MUST FOLLOW)

{retrieval_strategy_text}

> ⚠️ **Numerical Accuracy Override**: Regardless of the strategy framework above,
> you MUST verify every key metric with explicit SQL queries before reporting it.
> Strategy structure guides *how* you organize the analysis, but all numbers must
> come from actual query results — never from estimation or inference.

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
        pretty_message_log(messages[-1])
        messages.append({"role": "user", "content": query})
        pretty_message_log(messages[-1])
        name2tool = {}
        available_tools = []
        for idx, tool in enumerate(self.tools):
            name2tool[tool.name] = idx
            available_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        logger.debug(f"Available tools: {list(name2tool.keys())}")
        final_text = []
        stop_flag = False
        try:
            tool_calls_total = 0
            while not stop_flag and len(messages) < self.config.max_turns + 2:
                request_payload = {
                    "message": messages,
                    "tools": available_tools,
                }
                response = self.llm.chat_with_retry(**request_payload)
                if hasattr(response, "error"):
                    raise Exception(
                        f"Error in OpenAI response: {response.error['metadata']['raw']}"
                    )

                response_message = response.choices[0].message
                if response_message.tool_calls:
                    tool_call_list = []
                    for tool_call in response_message.tool_calls:
                        if not tool_call.id:
                            tool_call.id = str(uuid.uuid4())
                        tool_call_list.append(tool_call)
                    response_message.tool_calls = tool_call_list
                messages.append(response_message.model_dump(exclude_none=True))
                pretty_message_log(messages[-1])
                # todo: are we need a stop condition here?
                # todo (25/11/06): i think a stop condition is much better than stop tools, we may change it later
                # content = response_message.content
                # if content and not response_message.tool_calls:
                #     final_text.append(content)
                #     stop_flag = True
                if response_message.content and not response_message.tool_calls:
                    # 如果未满足最少工具调用次数，强制继续查询
                    if self.min_tool_calls > 0 and tool_calls_total < self.min_tool_calls:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": response_message.content,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": f"You must query the database at least {self.min_tool_calls} times before concluding. "
                                           f"You have only made {tool_calls_total} tool call(s) so far. "
                                           "Please run SQL queries to verify your key numbers before giving the final answer.",
                            }
                        )
                        pretty_message_log(messages[-1])
                        continue
                    # 如果模型未调用终止工具，直接用内容结束，避免重复回复
                    final_text.append(response_message.content)
                    stop_flag = True
                    break
                tool_calls = response_message.tool_calls
                if tool_calls:
                    # 检测是否并行调用（同一轮有多个tool calls）
                    is_parallel_batch = len(tool_calls) > 1

                    for tool_call in tool_calls:
                        try:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            tool_id = tool_call.id
                            logger.info(
                                f"LLM is calling tool: {tool_name}({tool_args})"
                            )

                            # 记录到策略验证器
                            if validator:
                                validator.record_tool_call(tool_name, tool_calls_total, is_parallel_batch)

                            # 追踪图表生成调用
                            if tool_name == "chart_generation_tool":
                                self.chart_generation_count += 1
                                logger.info(f"📊 Chart generation called (count: {self.chart_generation_count})")

                            idx = name2tool.get(tool_name)
                            if idx is None:
                                raise Exception(f"Tool {tool_name} not found.")
                            assert isinstance(idx, int), (
                                "Tool index should be an integer."
                            )
                            tool_result = await asyncio.wait_for(
                                self.tools[idx].run(tool_args),
                                timeout=self.config.tool_call_timeout,
                            )
                            tool_calls_total += 1
                            self.distinct_tools.add(tool_name)
                            list_content = tool_result.content
                            result = ""
                            for item in list_content:
                                result += item.text
                            # 收集图表路径（从chart_generation_tool返回结果中提取filepath）
                            if tool_name == "chart_generation_tool":
                                import json as _json, re as _re
                                try:
                                    chart_data = _json.loads(result)
                                    if isinstance(chart_data, dict) and chart_data.get("filepath"):
                                        self.generated_chart_paths.append(chart_data["filepath"])
                                except Exception:
                                    # 尝试从文本中用正则提取.png路径
                                    for _m in _re.finditer(r'[\w/\-. ]+\.png', result):
                                        _p = _m.group(0).strip()
                                        if _p:
                                            self.generated_chart_paths.append(_p)
                            # 统计信息增益：按空白切分做粗略去重
                            for tok in result.split():
                                self.info_tokens.add(tok.lower())
                            if tool_name in self.stop_tools:
                                # 检查是否需要强制生成图表（仅在 chart_generation_tool 可用时）
                                requires_charts = self._should_require_charts(query)
                                has_chart_tool = "chart_generation_tool" in name2tool
                                min_charts_required = getattr(self.config, "min_charts_required", 2)

                                if requires_charts and has_chart_tool and self.chart_generation_count < min_charts_required:
                                    # 图表数量不足，拒绝终止
                                    logger.warning(
                                        f"⚠️ Chart requirement not met: "
                                        f"{self.chart_generation_count}/{min_charts_required} charts generated. "
                                        f"Forcing LLM to generate charts."
                                    )
                                    stop_flag = False
                                    messages.append(
                                        {
                                            "role": "assistant",
                                            "content": f"⚠️ CRITICAL: You have only generated {self.chart_generation_count} chart(s), "
                                                      f"but this data analysis task REQUIRES at least {min_charts_required} charts. "
                                                      f"You MUST call `chart_generation_tool` at least {min_charts_required - self.chart_generation_count} more time(s) "
                                                      f"before calling end_with_message. Generate appropriate visualizations (line charts for trends, "
                                                      f"bar charts for comparisons, scatter plots for correlations) and then try again.",
                                        }
                                    )
                                    pretty_message_log(messages[-1])
                                    continue  # Skip the rest of stop_flag logic

                                if self.min_tool_calls == 0:
                                    stop_flag = True
                                    final_text.append(result)
                                # 防止过早结束：同时检查最少调用次数、信息量、工具多样性
                                elif self.min_tool_calls > 0:
                                    info_count = len(self.info_tokens)
                                    distinct_tool_count = len(self.distinct_tools)
                                    min_info = getattr(
                                        self.config, "min_info_tokens", 50
                                    )
                                    min_tools = getattr(
                                        self.config, "min_distinct_tools", 2
                                    )
                                    if (
                                        tool_calls_total < self.min_tool_calls
                                        or info_count < min_info
                                        or distinct_tool_count < min_tools
                                    ):
                                        stop_flag = False
                                        messages.append(
                                            {
                                                "role": "assistant",
                                                "content": "Need more tool evidence before concluding. Continue querying tools and cross-checking.",
                                            }
                                        )
                                        pretty_message_log(messages[-1])
                                    else:
                                        stop_flag = True
                                        final_text.append(result)
                                        if requires_charts and has_chart_tool:
                                            logger.info(
                                                f"✅ Chart requirement met: {self.chart_generation_count} charts generated"
                                            )

                        except asyncio.TimeoutError:
                            logger.error(f"Tool call {tool_name} timed out.")
                            result = "Tool call timed out."
                        except Exception as e:
                            logger.error(f"Error calling tool {tool_name}: {e}")
                            result = f"Error: {str(e)}"
                        # todo: this a very temporary solution for removing think tags
                        # todo: we should have a more robust way to handle think outputs
                        result = re.sub(
                            r"<think>.*?</think>", "", result, flags=re.DOTALL
                        ).strip()
                        if len(result) > self.config.tool_call_max_length:
                            logger.warning(
                                f"Tool call result exceeded max length of {self.config.tool_call_max_length}. Truncating."
                            )
                            result = result[: self.config.tool_call_max_length]
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": result,
                            }
                        )
                        pretty_message_log(messages[-1])
            if not stop_flag:
                logger.warning(f"⚠️ Max turns ({self.config.max_turns}) reached without calling end_with_message")
                forced = self._force_final_answer(messages, query)
                if forced:
                    final_text.append(forced)
                    messages.append({"role": "assistant", "content": forced})
                else:
                    logger.error("❌ No tool results or text found in message history")
                    final_text.append("Max turns reached without conclusion. Unable to extract a complete answer.")
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            final_text.append(f"Error: {str(e)}")
            messages.append({"role": "assistant", "content": str(e)})

        # 生成过程验证报告（工具调用模式）
        if validator:
            report = validator.analyze_pattern()
            report_text = format_validation_report(report)
            logger.info("\n" + report_text)

            if report.compliance_score < 0.5:
                logger.warning(
                    f"⚠️ Low strategy compliance ({report.compliance_score:.1%})! "
                    f"LLM may not be following '{selected_strategy_key}' strategy correctly."
                )

        # 产出验证 + refinement 循环
        output_compliance_score = None
        max_refine = getattr(self.config, "max_refinement_rounds", 0)
        refine_threshold = getattr(self.config, "refinement_threshold", 0.7)

        if self._active_spec and final_text:
            ov = OutputValidator(self._active_spec, self.llm)
            for refine_round in range(max_refine + 1):  # 第0轮是首次验证
                current_answer = "\n".join(final_text)
                ov_report = ov.validate(current_answer)
                output_compliance_score = ov_report.compliance_score
                ov_report_text = format_output_validation_report(ov_report)
                logger.info(f"\n[Refinement round {refine_round}]\n" + ov_report_text)

                # 追加验证报告到消息历史（Debug Trace 可见）
                messages.append({
                    "role": "system",
                    "content": f"[产出验证 round {refine_round}]\n" + ov_report_text,
                    "_type": "output_validation",
                })

                # 分数达标或没有 checkpoints 或已到最后一轮，退出
                passed = ov_report.compliance_score >= refine_threshold
                is_last_round = refine_round >= max_refine
                if passed or is_last_round:
                    if passed:
                        logger.info(f"✅ Output compliance passed ({ov_report.compliance_score:.1%}) at round {refine_round}")
                    else:
                        logger.warning(f"⚠️ Output compliance still low ({ov_report.compliance_score:.1%}) after {refine_round} refinement round(s)")
                    break

                # 找出未通过的 checkpoints，构建反馈
                failed = [r for r in ov_report.checkpoint_results if not r.satisfied]
                if not failed:
                    # 只有 generic 分数不够，也要给反馈
                    feedback_body = (
                        f"Your answer scored {ov_report.compliance_score:.0%} compliance with the '{self._active_spec.name}' strategy. "
                        f"Gap identified: {ov_report.gaps} "
                        f"Please revise your answer to better follow the strategy. "
                        f"Do NOT call any data tools again — only rewrite the final answer based on information you already have, "
                        f"then call `{self.end_tool}` again."
                    )
                else:
                    failed_lines = "\n".join(f"- {r.checkpoint}: {r.reason}" for r in failed)
                    feedback_body = (
                        f"Your answer does NOT fully satisfy the '{self._active_spec.name}' strategy. "
                        f"The following checkpoints were NOT met:\n{failed_lines}\n\n"
                        f"Please revise your answer to address these gaps. "
                        f"Do NOT call any data tools again — only rewrite the final answer using information already retrieved, "
                        f"then call `{self.end_tool}` again."
                    )

                logger.info(f"🔄 Refinement round {refine_round + 1}: injecting feedback for {len(failed)} failed checkpoints")
                messages.append({"role": "user", "content": feedback_body})
                pretty_message_log(messages[-1])

                # 重新进入 Agent 执行循环（仅做 refinement，不允许重新查询数据）
                final_text = []
                stop_flag = False
                try:
                    while not stop_flag and len(messages) < self.config.max_turns + 2 + refine_round * 10:
                        request_payload = {"message": messages, "tools": available_tools}
                        response = self.llm.chat_with_retry(**request_payload)
                        response_message = response.choices[0].message
                        if response_message.tool_calls:
                            tool_call_list = []
                            for tc in response_message.tool_calls:
                                if not tc.id:
                                    tc.id = str(uuid.uuid4())
                                tool_call_list.append(tc)
                            response_message.tool_calls = tool_call_list
                        messages.append(response_message.model_dump(exclude_none=True))
                        pretty_message_log(messages[-1])

                        if response_message.content and not response_message.tool_calls:
                            final_text.append(response_message.content)
                            stop_flag = True
                            break

                        for tool_call in (response_message.tool_calls or []):
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            tool_id = tool_call.id
                            idx = name2tool.get(tool_name)
                            if idx is None:
                                result = f"Tool {tool_name} not found."
                            else:
                                try:
                                    tool_result = await asyncio.wait_for(
                                        self.tools[idx].run(tool_args),
                                        timeout=self.config.tool_call_timeout,
                                    )
                                    result = "".join(item.text for item in tool_result.content)
                                except Exception as e:
                                    result = f"Error: {e}"
                            result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
                            if len(result) > self.config.tool_call_max_length:
                                result = result[:self.config.tool_call_max_length]
                            if tool_name in self.stop_tools:
                                final_text.append(result)
                                stop_flag = True
                            messages.append({"role": "tool", "tool_call_id": tool_id, "content": result})
                            pretty_message_log(messages[-1])
                except Exception as exc:
                    logger.error(f"Refinement loop error: {exc}")
                    break

        self.history = messages
        self.output_compliance_score = output_compliance_score
        return "\n".join(final_text), messages

    def _extract_final_answer(self, messages: list[dict]) -> str:
        """从消息历史中提取最后一条有效的 assistant 文本内容作为最终答案。"""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                content = msg.get("content") or ""
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    texts = [
                        block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    joined = "\n".join(t for t in texts if t.strip())
                    if joined:
                        return joined
        return ""

    def _force_final_answer(self, messages: list[dict], query: str) -> str:
        """当 max_turns 触发时，强制让 LLM 基于已有工具调用结果生成最终答案。"""
        # 先尝试从历史中提取文本
        extracted = self._extract_final_answer(messages)
        if extracted:
            return extracted

        # 收集工具结果（最近 10 条，每条最多 1500 字符）
        tool_results = []
        for m in messages:
            if m.get("role") == "tool":
                content = str(m.get("content", ""))[:1500]
                tool_results.append(content)

        if not tool_results:
            return ""

        tool_summary = "\n\n---\n\n".join(tool_results[-10:])

        # 发一次额外 LLM 调用，用截断后的工具结果总结
        try:
            system_msgs = [m for m in messages if m.get("role") == "system"]
            user_msgs = [m for m in messages if m.get("role") == "user"][:1]
            force_messages = system_msgs + user_msgs + [
                {
                    "role": "user",
                    "content": (
                        "You have reached the maximum number of tool calls. "
                        "Here is the raw data retrieved from the database so far:\n\n"
                        f"{tool_summary}\n\n"
                        "Based ONLY on the data above, write your final comprehensive analytical answer "
                        "to the original question. Your answer MUST:\n"
                        "1. Directly address the question with specific findings\n"
                        "2. Include key numbers, metrics, and comparisons from the data\n"
                        "3. Provide clear conclusions and insights\n"
                        "4. Be structured with headers if the analysis has multiple parts\n\n"
                        "Do NOT call any more tools. Do NOT say you cannot answer. "
                        "Write the full analysis now based on the data already retrieved."
                    )
                }
            ]
            resp = self.llm.chat(messages=force_messages)
            content = resp.choices[0].message.content or ""
            if not content.strip():
                reasoning = getattr(resp.choices[0].message, "reasoning_content", "") or ""
                content = reasoning
            if content.strip():
                return content.strip()
        except Exception as exc:
            logger.warning(f"Force final answer LLM call failed: {exc}")

        # 最终兜底：再尝试一次更简单的 LLM 调用
        try:
            tool_texts = "\n\n".join(f"Result {i+1}:\n{r}" for i, r in enumerate(tool_results[-5:]))
            simple_messages = [
                {"role": "user", "content": f"Question: {query}\n\nDatabase results:\n{tool_texts}\n\nWrite a brief analytical answer based on these results."}
            ]
            resp2 = self.llm.chat(messages=simple_messages)
            content2 = resp2.choices[0].message.content or ""
            if content2.strip():
                return content2.strip()
        except Exception:
            pass

        # 绝对兜底：直接返回工具结果拼接
        logger.warning("Falling back to raw tool results as final answer")
        return f"[Data Analysis Results]\n\n{tool_summary}"

    async def aclose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
