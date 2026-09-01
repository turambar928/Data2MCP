from pathlib import Path

from hydra import compose, initialize_config_dir

from data2mcp_v2.config import Data2McpConfig
from data2mcp_v2.server.strategy_catalog import load_strategies
from data2mcp_v2.utils.config import omega_conf_to_dataclass


ROOT = Path(__file__).resolve().parents[1]


def test_default_config_composes():
    with initialize_config_dir(config_dir=str(ROOT / "config"), version_base=None):
        raw_config = compose(config_name="config")

    config = omega_conf_to_dataclass(raw_config)
    assert isinstance(config, Data2McpConfig)
    assert config.agents.agent_configs


def test_strategy_catalog_has_builtin_strategies():
    strategies = load_strategies()
    assert "crisp_dm" in strategies
    assert all(spec.full_text for spec in strategies.values())
