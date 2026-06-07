from __future__ import annotations

import pytest

from cortexflow.core.errors import (
    CortexFlowError,
    ExtractError,
    FetchError,
    FilterError,
    NormalizeError,
    ReportError,
    StageError,
)


class TestErrorHierarchy:
    def test_base_error(self):
        e = CortexFlowError("base error")
        assert str(e) == "base error"

    def test_stage_error(self):
        e = StageError("stage1", "something broke")
        assert e.stage == "stage1"
        assert "[stage1]" in str(e)

    def test_stage_error_with_cause(self):
        cause = ValueError("original")
        e = StageError("stage1", "wrapped", cause=cause)
        assert e.cause is cause

    def test_fetch_error(self):
        e = FetchError("reddit", "API timeout")
        assert e.source == "reddit"
        assert "[Fetch(reddit)]" in str(e)

    def test_normalize_error(self):
        e = NormalizeError("bad data")
        assert "[Normalize]" in str(e)

    def test_extract_error(self):
        e = ExtractError("https://example.com", "connection failed")
        assert e.url == "https://example.com"
        assert "[Extract(https://example.com)]" in str(e)

    def test_filter_error(self):
        e = FilterError("LLM call failed")
        assert "[Filter]" in str(e)

    def test_report_error(self):
        e = ReportError("write failed")
        assert "[Report]" in str(e)

    def test_isinstance_relationships(self):
        assert issubclass(StageError, CortexFlowError)
        assert issubclass(FetchError, StageError)
        assert issubclass(NormalizeError, StageError)
        assert issubclass(ExtractError, StageError)
        assert issubclass(FilterError, StageError)
        assert issubclass(ReportError, StageError)

    def test_raise_and_catch_base(self):
        with pytest.raises(CortexFlowError):
            raise FetchError("github", "timeout")

    def test_raise_and_catch_specific(self):
        with pytest.raises(ExtractError) as exc_info:
            raise ExtractError("https://x.com", "parse error")
        assert exc_info.value.url == "https://x.com"
