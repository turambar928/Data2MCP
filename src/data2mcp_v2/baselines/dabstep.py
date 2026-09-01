import argparse
import json
import logging
import os

from hydra import compose, initialize_config_dir
from tqdm import tqdm

from data2mcp_v2.server.router import Router
from data2mcp_v2.utils.config import omega_conf_to_dataclass

looger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="DABStep Baseline")
    parser.add_argument(
        "--data_path",
        type=str,
        default="./data/benchmark/DABStep/tasks/all.jsonl",
        help="Path to the input data file",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="./output/dab_step.json",
        help="Path to the output result file",
    )
    parser.add_argument(
        "--end_idx",
        type=int,
        default=-1,
        help="Index to stop processing data",
    )
    args = parser.parse_args()
    return args


async def main():
    args = parse_args()
    data_path = args.data_path
    output_path = args.output_path
    end_idx = args.end_idx
    ans = []
    data = []
    with open(data_path) as f:
        for line in f:
            data.append(json.loads(line))
    # get the model from config
    with initialize_config_dir(
        config_dir=os.path.abspath("./config/baselines"), version_base=None
    ):
        cfg = compose(
            config_name="dab_step",
        )
    config = omega_conf_to_dataclass(cfg)
    data_tag = data_path.split("/")[-1].replace(".jsonl", "")
    output_path = output_path.replace(".json", f"_{data_tag}.json")
    output_path = output_path.replace(".json", f"_{config.llm.model}.json")

    target_question = data[:end_idx]
    router = Router(config)
    for q in tqdm(target_question, position=0, leave=False):
        query = f"{q['question']}\n{q['guidelines']}"
        final_text, messages = await router.route(query)
        q["final_text"] = final_text
        q["messages"] = messages
        ans.append(q)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(ans, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
