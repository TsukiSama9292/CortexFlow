"""Stage 2: 標準化層 — 去重與資料品質檢查。."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from datasketch import MinHash, MinHashLSH
from loguru import logger

if TYPE_CHECKING:
    from cortexflow.core.schema import Article


class Normalizer:
    """跨渠道資料標準化與去重。."""

    def __init__(self, threshold: float = 0.8, num_perm: int = 128) -> None:
        """初始化 Normalizer。 .

        Args:
            threshold: Jaccard 相似度閾值，超過此值視為重複。
            num_perm: MinHash 置換次數。
        """
        self.threshold = threshold
        self.num_perm = num_perm

    def deduplicate(self, articles: list[Article]) -> list[Article]:
        """以 URL + MinHash LSH 進行進階去重。."""
        seen_urls: set[str] = set()
        seen_hashes: set[str] = set()
        lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        unique: list[Article] = []

        for article in articles:
            # 1. URL 精確去重
            if article.url and article.url in seen_urls:
                continue
            if article.url:
                seen_urls.add(article.url)

            # 2. 內容去重
            text = (article.text or article.title or "").strip()
            if not text:
                continue

            # 對於短內容，使用精確 Hash 去重
            if len(text) < 100:
                h = str(hash(text.lower()))
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                unique.append(article)
                continue

            # 對於長內容，使用 MinHash LSH 模糊去重
            m = self._get_minhash(text)

            # 查詢 LSH 是否存在相似內容
            result = lsh.query(m)
            if result:
                logger.debug("發現重複文章 (LSH): {title}", title=article.title)
                continue

            # 插入 LSH 以供後續比對
            lsh.insert(article.id, m)
            unique.append(article)

        logger.info("去重完成: 原有 {old} 篇，剩餘 {new} 篇", old=len(articles), new=len(unique))
        return unique

    def _get_minhash(self, text: str) -> MinHash:
        """計算文字的 MinHash 簽名。."""
        m = MinHash(num_perm=self.num_perm)

        # 簡單的分詞與清理
        text = text.lower()
        # 移除非字母數字字元
        text = re.sub(r"[^\w\s]", "", text)
        # 以 3-shingle 為單位 (3個字組成一組)
        shingles = [text[i : i + 3] for i in range(len(text) - 2)]

        for s in set(shingles):
            m.update(s.encode("utf8"))
        return m
