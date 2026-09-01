import argparse
import json
import os
from enum import Enum
from pathlib import Path

from hydra import compose, initialize_config_dir
from tqdm import tqdm

from data2mcp_v2.config import EvaluationConfig
from data2mcp_v2.evaluation.fuzzy_mathch import llm_fuzzy_match
from data2mcp_v2.evaluation.scorer import question_scorer
from data2mcp_v2.utils.config import omega_conf_to_dataclass


class JudgeType(str, Enum):
    DAB_Scorer = "dab_scorer"
    LLM_Fuzzy_Match = "llm_fuzzy_match"


def report_results(scored_path: Path, judge_type: JudgeType) -> None:
    """report statistics"""
    with open(scored_path) as f:
        results = json.load(f)
    total = len(results)
    print(f"Total Samples: {total}")
    print(f"Judge Type: {judge_type.value}")
    print(f"Error Cases: {sum(1 for item in results if not item['final_text'])}")
    if judge_type == JudgeType.LLM_Fuzzy_Match:
        correct_cnt = sum(1 for item in results if item["fuzzy_match_score"] == 1.0)
        incorrect_cnt = sum(1 for item in results if item["fuzzy_match_score"] == 0.0)
        print(f"Correct: {correct_cnt} ({correct_cnt / total:.2%})")
        print(f"Incorrect: {incorrect_cnt} ({incorrect_cnt / total:.2%})")
    elif judge_type == JudgeType.DAB_Scorer:
        score_sum = sum(item["dab_score"] for item in results)
        avg_score = score_sum / total
        print(f"Total DAB Score: {score_sum}")
        print(f"Average DAB Score: {avg_score:.2f}")


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pred_path",
        type=str,
        required=True,
        help="Path to the prediction JSON file.",
    )
    parser.add_argument(
        "--judge_type",
        type=str,
        required=True,
        choices=[jt.value for jt in JudgeType],
        help="Type of judge to use.",
    )
    parser.add_argument(
        "--golden_key",
        type=str,
        default="answer",
        help="Key for the golden answer in the JSON file.",
    )
    return parser


if __name__ == "__main__":
    parser = arg_parser()
    args = parser.parse_args()
    pred_path = Path(args.pred_path)
    judge_type = JudgeType(args.judge_type)
    golden_key = args.golden_key
    if judge_type == JudgeType.LLM_Fuzzy_Match:
        with initialize_config_dir(
            config_dir=os.path.abspath("data2mcp_v2/config/evaluation"),
            version_base=None,
        ):
            cfg = compose(
                config_name="default",
            )
        evaluation_config: EvaluationConfig = omega_conf_to_dataclass(cfg)
        output_path = (
            pred_path.parent
            / "score"
            / pred_path.name.replace(
                ".json", f"_fuzzy_matched_{evaluation_config.llm.model}.json"
            )
        )
    elif judge_type == JudgeType.DAB_Scorer:
        output_path = (
            pred_path.parent
            / "score"
            / pred_path.name.replace(".json", f"_{judge_type.value}.json")
        )
    os.makedirs(output_path.parent, exist_ok=True)
    if output_path.exists():
        print(
            f"{judge_type.value} results already exist at {output_path}, reporting stats..."
        )
        report_results(output_path, judge_type)
        exit(0)
    stop_error_cnt = 0
    with open(pred_path) as f:
        results = json.load(f)
    for item in tqdm(results):
        pred = item["final_text"]
        reference = item[golden_key]
        question = item["question"]
        if judge_type == JudgeType.LLM_Fuzzy_Match:
            if not pred:
                stop_error_cnt += 1
                score = 0.0
                response = "no answer generated"
            else:
                score, response = llm_fuzzy_match(
                    evaluation_config, pred, reference, question
                )
            item["fuzzy_match_score"] = score
            item["fuzzy_match_model"] = evaluation_config.llm.model
            item["fuzzy_match_response"] = response
        elif judge_type == JudgeType.DAB_Scorer:
            if not pred:
                stop_error_cnt += 1
                score = 0
            else:
                score = question_scorer(pred, reference)
            item["dab_score"] = int(score)
    print(f"Total {stop_error_cnt} cases with no answer generated.")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"Evluation save to {output_path}")
    report_results(output_path, judge_type)
