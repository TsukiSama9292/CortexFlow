"""CortexFlow 設定載入器 — 支援從 cortexflow.toml 載入預設值。."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_config(config_path: str = "cortexflow.toml") -> dict[str, Any]:
    """載入 TOML 設定檔並回傳字典。.

    Args:
        config_path: 設定檔路徑。

    Returns:
        包含設定項的字典。若檔案不存在則回傳空字典。
    """
    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except Exception:  # noqa: BLE001
        # 設定檔格式錯誤時忽略，使用預設值
        return {}


def get_pipeline_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """從完整的設定字典中提煉出 pipeline 相關的預設值。."""
    pipeline_cfg = config.get("pipeline", {})

    # 對應 argparse 的參數名稱
    mapping = {
        "sources": "sources",
        "max_results_per_source": "max_results",
        "relevance_threshold": "threshold",
        "output_format": "output_format",
        "output_path": "output",
    }

    defaults: dict[str, Any] = {}
    for cfg_key, arg_key in mapping.items():
        if cfg_key in pipeline_cfg:
            defaults[arg_key] = pipeline_cfg[cfg_key]

    return defaults
