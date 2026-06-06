"""Pipeline 階段錯誤類型定義。.

每個 Stage 有獨立的例外類型，確保錯誤可被精確捕捉與隔離。
"""

from __future__ import annotations


class CortexFlowError(Exception):
    """基礎例外。."""


class StageError(CortexFlowError):
    """某個 Stage 執行期間的錯誤。."""

    def __init__(self, stage: str, message: str, cause: Exception | None = None) -> None:
        """初始化階段錯誤。."""
        self.stage = stage
        self.cause = cause
        super().__init__(f"[{stage}] {message}")


class FetchError(StageError):
    """Stage 1 資料採集錯誤。."""

    def __init__(self, source: str, message: str, cause: Exception | None = None) -> None:
        """初始化採集錯誤。."""
        self.source = source
        super().__init__(stage=f"Fetch({source})", message=message, cause=cause)


class NormalizeError(StageError):
    """Stage 2 標準化錯誤。."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """初始化標準化錯誤。."""
        super().__init__(stage="Normalize", message=message, cause=cause)


class ExtractError(StageError):
    """Stage 3 內容提取錯誤。."""

    def __init__(self, url: str, message: str, cause: Exception | None = None) -> None:
        """初始化提取錯誤。."""
        self.url = url
        super().__init__(stage=f"Extract({url})", message=message, cause=cause)


class FilterError(StageError):
    """Stage 4 LLM 過濾錯誤。."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """初始化過濾錯誤。."""
        super().__init__(stage="Filter", message=message, cause=cause)


class ReportError(StageError):
    """Stage 5 輸出錯誤。."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """初始化輸出錯誤。."""
        super().__init__(stage="Report", message=message, cause=cause)
