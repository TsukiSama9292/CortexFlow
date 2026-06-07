from __future__ import annotations

from typing import TYPE_CHECKING

from cortexflow.config.loader import get_pipeline_defaults, load_config

if TYPE_CHECKING:
    from pathlib import Path


def test_load_config_not_found() -> None:
    """測試當設定檔不存在時。"""
    config = load_config("non_existent.toml")
    assert config == {}


def test_load_config_success(tmp_path: Path) -> None:
    """測試成功載入 TOML。"""
    toml_file = tmp_path / "cortexflow.toml"
    toml_file.write_text(
        """
[pipeline]
sources = ["github"]
max_results_per_source = 5
""",
        encoding="utf-8",
    )

    config = load_config(str(toml_file))
    assert config["pipeline"]["sources"] == ["github"]
    assert config["pipeline"]["max_results_per_source"] == 5


def test_get_pipeline_defaults_full() -> None:
    """測試完整設定轉換。."""
    config = {
        "pipeline": {
            "sources": ["github", "lobsters"],
            "max_results_per_source": 50,
            "relevance_threshold": 3.0,
            "output_format": "markdown",
            "output_path": "custom.md",
        }
    }
    defaults = get_pipeline_defaults(config)
    assert defaults["sources"] == ["github", "lobsters"]
    assert defaults["max_results"] == 50
    assert defaults["threshold"] == 3.0
    assert defaults["output_format"] == "markdown"
    assert defaults["output"] == "custom.md"


def test_get_pipeline_defaults_empty() -> None:
    """測試空設定。."""
    assert get_pipeline_defaults({}) == {}


def test_load_config_invalid_format(tmp_path: Path) -> None:
    """測試當設定檔格式錯誤時。."""
    toml_file = tmp_path / "invalid.toml"
    toml_file.write_text("invalid = { [", encoding="utf-8")

    config = load_config(str(toml_file))
    assert config == {}


def test_get_pipeline_defaults_partial() -> None:
    """測試部分設定。."""
    config = {"pipeline": {"max_results_per_source": 10}}
    defaults = get_pipeline_defaults(config)
    assert defaults == {"max_results": 10}
