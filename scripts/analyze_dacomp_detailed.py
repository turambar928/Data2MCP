"""
详细分析DAComp结果 - 找出真正成功的案例
"""
import json

# 加载预测
with open("output/dacomp_predictions.json", "r") as f:
    preds = json.load(f)

print("=" * 80)
print("DAComp 详细分析")
print("=" * 80)

categories = {
    "真正成功（有数据分析）": [],
    "数据缺失": [],
    "超时": [],
    "工具未调用": [],
    "其他错误": []
}

for pred in preds:
    instance_id = pred["instance_id"]
    final_text = pred["final_text"]
    messages = pred.get("raw_messages", [])

    # 检查是否有tool调用
    tool_calls = [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]

    if "Max turns" in final_text:
        categories["超时"].append(instance_id)
    elif any(kw in final_text.lower() for kw in ["not available", "does not contain", "cannot", "no data", "缺少", "不存在"]):
        categories["数据缺失"].append(instance_id)
    elif not tool_calls:
        categories["工具未调用"].append(instance_id)
    elif len(final_text) > 200:  # 有实质内容
        categories["真正成功（有数据分析）"].append(instance_id)
    else:
        categories["其他错误"].append(instance_id)

print("\n分类统计:")
print("-" * 80)
for cat, items in categories.items():
    print(f"{cat}: {len(items)}")
    if items and len(items) <= 10:
        print(f"  案例: {', '.join(items)}")

print(f"\n真实成功率: {len(categories['真正成功（有数据分析）'])} / {len(preds)} = {len(categories['真正成功（有数据分析）']) / len(preds) * 100:.1f}%")

# 查看一个真正成功的案例
if categories["真正成功（有数据分析）"]:
    example_id = categories["真正成功（有数据分析）"][0]
    example = next(p for p in preds if p["instance_id"] == example_id)

    print("\n" + "=" * 80)
    print(f"成功案例示例: {example_id}")
    print("=" * 80)
    print(f"问题: {example['question'][:200]}...")
    print(f"\n回答: {example['final_text'][:500]}...")
    print("=" * 80)

# 保存真正成功的案例
successful = [p for p in preds if p["instance_id"] in categories["真正成功（有数据分析）"]]
with open("output/dacomp_successful_cases.json", "w") as f:
    json.dump(successful, f, ensure_ascii=False, indent=2)

print(f"\n✅ 成功案例已保存到: output/dacomp_successful_cases.json")
