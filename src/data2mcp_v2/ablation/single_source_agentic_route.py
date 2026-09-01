import json
import logging
import os

from hydra import compose, initialize_config_dir
from tqdm import tqdm

from data2mcp_v2.server.router import Router
from data2mcp_v2.utils.config import omega_conf_to_dataclass

looger = logging.getLogger(__name__)


async def main():
    data_path = "./data/benchmark/unified_bench.json"
    output_path = "./output/single_source_agentic_route_results.json"

    target_source = ["spider", "metaqa"]
    end_idx = -1
    ans = []
    with open(data_path) as f:
        questions = json.load(f)["questions"]
    # get the model from config
    with initialize_config_dir(
        config_dir=os.path.abspath("./config/ablation"), version_base=None
    ):
        cfg = compose(
            config_name=target_source[0],
        )
    config = omega_conf_to_dataclass(cfg)
    output_path = output_path.replace(".json", f"_{config.llm.model}.json")

    for source in tqdm(target_source, desc="Sources", position=0):
        target_question = []
        for q in questions:
            if q["source"] in [source]:
                target_question.append(q)
        target_question = target_question[:end_idx]
        with initialize_config_dir(
            config_dir=os.path.abspath("./config/ablation"), version_base=None
        ):
            cfg = compose(
                config_name=target_source[0],
            )
        config = omega_conf_to_dataclass(cfg)
        router = Router(config)
        for q in tqdm(
            target_question, desc=f"Questions from {source}", position=1, leave=False
        ):
            query = q["question"]
            final_text, messages = await router.route(query)
            temp_q = q.copy()
            temp_q["final_text"] = final_text
            temp_q["messages"] = messages
            ans.append(temp_q)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(ans, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
