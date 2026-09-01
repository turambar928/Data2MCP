"""
将Data2MCP预测结果转换为DAComp官方评估格式

官方格式要求：
agent_results/<model_name>/
  ├── dacomp-001/
  │   ├── dacomp-001.md        # 最终答案
  │   └── dacomp-001-traj.txt  # 轨迹/日志
  ├── dacomp-002/
  │   ├── dacomp-002.md
  │   └── dacomp-002-traj.txt
  └── ...
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict


def convert_messages_to_trajectory(messages: List[Dict]) -> str:
    """将消息历史转换为轨迹文本"""
    trajectory_lines = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # 跳过system消息（太长）
        if role == "system":
            trajectory_lines.append(f"[System Message {i}]: (omitted for brevity)")
            continue

        # 格式化消息
        trajectory_lines.append(f"\n{'='*80}")
        trajectory_lines.append(f"[{role.upper()} {i}]")
        trajectory_lines.append(f"{'='*80}")

        # 添加内容
        if content:
            trajectory_lines.append(content)

        # 添加tool calls
        if "tool_calls" in msg:
            trajectory_lines.append("\n[TOOL CALLS]:")
            for tool_call in msg["tool_calls"]:
                func_name = tool_call.get("function", {}).get("name", "unknown")
                func_args = tool_call.get("function", {}).get("arguments", "{}")
                trajectory_lines.append(f"  - {func_name}: {func_args}")

    return "\n".join(trajectory_lines)


def convert_predictions_to_official_format(
    predictions_path: str,
    output_dir: str,
    model_name: str = "data2mcp_v2"
):
    """转换预测结果为官方格式"""
    predictions_path = Path(predictions_path)
    output_dir = Path(output_dir)

    # 加载预测结果
    with open(predictions_path, "r", encoding="utf-8") as f:
        predictions = json.load(f)

    print(f"加载了 {len(predictions)} 个预测结果")

    # 创建模型目录
    model_dir = output_dir / model_name
    model_dir.mkdir(parents=True, exist_ok=True)

    converted_count = 0

    for pred in predictions:
        instance_id = pred["instance_id"]
        final_text = pred["final_text"]
        raw_messages = pred.get("raw_messages", [])

        # 创建instance目录
        instance_dir = model_dir / instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)

        # 写入.md文件（最终答案）
        md_path = instance_dir / f"{instance_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(final_text)

        # 写入-traj.txt文件（轨迹）
        traj_path = instance_dir / f"{instance_id}-traj.txt"
        trajectory = convert_messages_to_trajectory(raw_messages)
        with open(traj_path, "w", encoding="utf-8") as f:
            f.write(f"Instance: {instance_id}\n")
            f.write(f"Question: {pred['question']}\n")
            f.write(f"\n{'='*80}\n")
            f.write("EXECUTION TRAJECTORY\n")
            f.write(f"{'='*80}\n\n")
            f.write(trajectory)
            f.write(f"\n\n{'='*80}\n")
            f.write("FINAL ANSWER\n")
            f.write(f"{'='*80}\n\n")
            f.write(final_text)

        converted_count += 1
        if converted_count % 10 == 0:
            print(f"已转换 {converted_count}/{len(predictions)} 个实例...")

    print(f"\n✅ 成功转换 {converted_count} 个实例到: {model_dir}")
    print(f"\n目录结构:")
    print(f"{model_dir}/")
    for instance_dir in sorted(model_dir.iterdir())[:3]:
        if instance_dir.is_dir():
            print(f"  ├── {instance_dir.name}/")
            for f in sorted(instance_dir.iterdir()):
                print(f"  │   ├── {f.name}")
    if len(list(model_dir.iterdir())) > 3:
        print(f"  └── ... ({len(list(model_dir.iterdir()))} total instances)")

    return str(model_dir)


def main():
    parser = argparse.ArgumentParser(description="Convert Data2MCP predictions to DAComp official format")
    parser.add_argument(
        "--predictions",
        type=str,
        default="output/dacomp_predictions_deepseek-v3.json",
        help="Path to predictions JSON file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/benchmark/DAComp/dacomp-da-files/evaluation_suite/agent_results",
        help="Output directory for converted results"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="data2mcp_v2",
        help="Model name for the output directory"
    )

    args = parser.parse_args()

    convert_predictions_to_official_format(
        predictions_path=args.predictions,
        output_dir=args.output_dir,
        model_name=args.model_name
    )


if __name__ == "__main__":
    main()
