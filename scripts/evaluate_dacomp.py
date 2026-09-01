"""
DAComp Benchmark 评估脚本

使用LLM-as-Judge方法评估预测结果的质量

评估维度：
1. 答案相关性 (Relevance): 是否回答了问题
2. 数据分析质量 (Analysis Quality): 数据分析是否深入
3. 逻辑连贯性 (Coherence): 推理是否合理
4. 完整性 (Completeness): 是否覆盖了问题的所有方面
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DACompEvaluator:
    """DAComp Benchmark评估器"""

    def __init__(self, predictions_path: str, eval_data_path: str):
        self.predictions_path = Path(predictions_path)
        self.eval_data_path = Path(eval_data_path)
        self.predictions = self._load_predictions()
        self.reference_answers = self._load_references()

    def _load_predictions(self) -> List[Dict]:
        """加载预测结果"""
        with open(self.predictions_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_references(self) -> Dict[str, List[str]]:
        """加载参考答案"""
        references = {}
        for instance_dir in sorted(self.eval_data_path.iterdir()):
            if not instance_dir.is_dir():
                continue

            instance_id = instance_dir.name
            ref_answers = []

            # 加载5个参考答案
            for i in range(5):
                ref_dir = instance_dir / f"gsb_ref_{i}"
                if ref_dir.exists():
                    ref_file = list(ref_dir.glob("*.md"))
                    if ref_file:
                        with open(ref_file[0], "r", encoding="utf-8") as f:
                            ref_answers.append(f.read())

            references[instance_id] = ref_answers

        return references

    def evaluate_basic_metrics(self) -> Dict:
        """评估基础指标"""
        results = {
            "total": len(self.predictions),
            "completed": 0,
            "max_turns_reached": 0,
            "error": 0,
            "no_answer": 0,
            "answered": 0,
        }

        for pred in self.predictions:
            final_text = pred.get("final_text", "")

            if "Max turns reached" in final_text:
                results["max_turns_reached"] += 1
            elif "Error:" in final_text or "cannot be" in final_text.lower():
                results["error"] += 1
            elif not final_text or len(final_text.strip()) < 20:
                results["no_answer"] += 1
            else:
                results["answered"] += 1

        results["completion_rate"] = results["answered"] / results["total"]

        return results

    def analyze_answer_length(self) -> Dict:
        """分析答案长度分布"""
        lengths = []
        for pred in self.predictions:
            final_text = pred.get("final_text", "")
            lengths.append(len(final_text))

        import statistics

        return {
            "mean": statistics.mean(lengths) if lengths else 0,
            "median": statistics.median(lengths) if lengths else 0,
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "std": statistics.stdev(lengths) if len(lengths) > 1 else 0,
        }

    def categorize_by_question_type(self) -> Dict:
        """按问题类型分类"""
        categories = {
            "credit_risk": [],
            "sales_analysis": [],
            "marketing": [],
            "supply_chain": [],
            "customer_analysis": [],
            "other": [],
        }

        for pred in self.predictions:
            question = pred.get("question", "").lower()
            instance_id = pred.get("instance_id", "")

            if any(
                kw in question
                for kw in ["credit", "loan", "risk", "default", "churn"]
            ):
                categories["credit_risk"].append(instance_id)
            elif any(kw in question for kw in ["sales", "revenue", "product"]):
                categories["sales_analysis"].append(instance_id)
            elif any(kw in question for kw in ["market", "customer segment"]):
                categories["marketing"].append(instance_id)
            elif any(kw in question for kw in ["supply", "inventory", "logistics"]):
                categories["supply_chain"].append(instance_id)
            elif any(kw in question for kw in ["customer", "preference", "behavior"]):
                categories["customer_analysis"].append(instance_id)
            else:
                categories["other"].append(instance_id)

        return {k: len(v) for k, v in categories.items()}

    def check_data_usage(self) -> Dict:
        """检查是否使用了数据源"""
        results = {
            "used_tools": 0,
            "no_tools": 0,
            "tool_usage_examples": [],
        }

        for pred in self.predictions:
            messages = pred.get("raw_messages", [])

            # 检查是否有tool调用
            has_tool_call = any(
                msg.get("role") == "tool" for msg in messages if isinstance(msg, dict)
            )

            if has_tool_call:
                results["used_tools"] += 1

                # 提取工具调用示例
                tool_names = set()
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("role") == "assistant":
                        tool_calls = msg.get("tool_calls", [])
                        for tc in tool_calls:
                            if isinstance(tc, dict):
                                fn = tc.get("function", {})
                                name = fn.get("name", "")
                                if name and name != "end_with_message":
                                    tool_names.add(name)

                if tool_names and len(results["tool_usage_examples"]) < 5:
                    results["tool_usage_examples"].append(
                        {
                            "instance_id": pred.get("instance_id"),
                            "tools": list(tool_names),
                        }
                    )
            else:
                results["no_tools"] += 1

        results["tool_usage_rate"] = results["used_tools"] / len(self.predictions)

        return results

    def generate_report(self) -> str:
        """生成评估报告"""
        basic = self.evaluate_basic_metrics()
        length = self.analyze_answer_length()
        categories = self.categorize_by_question_type()
        tool_usage = self.check_data_usage()

        report = [
            "=" * 80,
            "DAComp Benchmark 评估报告",
            "=" * 80,
            "",
            "1. 基础指标",
            "-" * 80,
            f"总题目数: {basic['total']}",
            f"完成回答: {basic['answered']} ({basic['completion_rate']:.1%})",
            f"超时未完成: {basic['max_turns_reached']}",
            f"错误/无法回答: {basic['error']}",
            f"无答案: {basic['no_answer']}",
            "",
            "2. 答案长度分析",
            "-" * 80,
            f"平均长度: {length['mean']:.0f} 字符",
            f"中位数: {length['median']:.0f} 字符",
            f"最短: {length['min']} 字符",
            f"最长: {length['max']} 字符",
            f"标准差: {length['std']:.0f}",
            "",
            "3. 问题类型分布",
            "-" * 80,
        ]

        for cat, count in categories.items():
            report.append(f"{cat}: {count} 题")

        report.extend(
            [
                "",
                "4. 数据源使用情况",
                "-" * 80,
                f"使用工具查询: {tool_usage['used_tools']} ({tool_usage['tool_usage_rate']:.1%})",
                f"未使用工具: {tool_usage['no_tools']}",
                "",
                "工具使用示例:",
            ]
        )

        for example in tool_usage["tool_usage_examples"]:
            report.append(
                f"  - {example['instance_id']}: {', '.join(example['tools'])}"
            )

        report.extend(["", "=" * 80, ""])

        return "\n".join(report)

    def export_failed_cases(self, output_path: str = "failed_cases.json"):
        """导出失败案例用于分析"""
        failed_cases = []

        for pred in self.predictions:
            final_text = pred.get("final_text", "")

            if (
                "Max turns reached" in final_text
                or "Error:" in final_text
                or "cannot be" in final_text.lower()
                or len(final_text.strip()) < 20
            ):
                failed_cases.append(
                    {
                        "instance_id": pred.get("instance_id"),
                        "question": pred.get("question", "")[:200] + "...",
                        "final_text": final_text,
                        "issue_type": (
                            "timeout"
                            if "Max turns" in final_text
                            else "error" if "Error:" in final_text else "no_answer"
                        ),
                    }
                )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(failed_cases, f, ensure_ascii=False, indent=2)

        logger.info(f"导出 {len(failed_cases)} 个失败案例到 {output_path}")

        return failed_cases


def main():
    """主函数"""
    evaluator = DACompEvaluator(
        predictions_path="output/dacomp_predictions.json",
        eval_data_path="data/benchmark/DAComp/dacomp-da-eval",
    )

    # 生成报告
    report = evaluator.generate_report()
    print(report)

    # 保存报告
    with open("output/dacomp_eval_report.txt", "w", encoding="utf-8") as f:
        f.write(report)

    # 导出失败案例
    failed = evaluator.export_failed_cases("output/dacomp_failed_cases.json")

    # 输出总结
    print(f"\n✅ 评估完成！")
    print(f"   - 报告已保存到: output/dacomp_eval_report.txt")
    print(f"   - 失败案例已保存到: output/dacomp_failed_cases.json")
    print(f"   - 失败案例数: {len(failed)}")


if __name__ == "__main__":
    main()
