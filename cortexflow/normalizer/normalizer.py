"""Stage 2: 標準化層 — 去重與資料品質檢查。"""

from __future__ import annotations

from cortexflow.core.schema import Article


class Normalizer:
    """跨渠道資料標準化與去重。"""

    def deduplicate(self, articles: list[Article]) -> list[Article]:
        """以 URL + content fingerprint 進行去重。"""
        seen_urls: set[str] = set()
        seen_fingerprints: set[str] = set()
        unique: list[Article] = []

        for article in articles:
            # URL 去重
            if article.url and article.url in seen_urls:
                continue
            if article.url:
                seen_urls.add(article.url)

            # Content fingerprint 去重（取前 100 字的 hash）
            text_fp = article.text[:100].strip().lower()
            if not text_fp:
                continue
            if text_fp in seen_fingerprints:
                continue
            seen_fingerprints.add(text_fp)

            unique.append(article)

        return unique
