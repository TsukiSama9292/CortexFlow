"""CortexFlow 日誌模組 — 基於 loguru 的結構化日誌系統。."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logger(verbose: bool = False, log_file: str | None = None) -> None:
    """配置 loguru 日誌。

    Args:
        verbose: 是否啟用 DEBUG 層級日誌。
        log_file: 日誌檔案輸出路徑。
    """
    # 移除預設處理器
    logger.remove()

    # 配置標準輸出（僅顯示重要資訊，除非 verbose）
    level = "DEBUG" if verbose else "INFO"
    
    # 控制台輸出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        level=level,
        format=console_format,
        colorize=True,
    )

    # 如果有指定日誌檔案
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            level="DEBUG",  # 檔案日誌一律記錄 DEBUG 以上
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week",
            compression="zip",
        )

    logger.debug("日誌系統初始化完成（Level: {level}）", level=level)
