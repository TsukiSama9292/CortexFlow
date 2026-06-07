from __future__ import annotations

from cortexflow.core.schema import Article
from cortexflow.normalizer.normalizer import Normalizer


class TestNormalizer:
    def test_empty_list(self):
        n = Normalizer()
        assert n.deduplicate([]) == []

    def test_single_article(self, sample_article):
        n = Normalizer()
        result = n.deduplicate([sample_article])
        assert len(result) == 1
        assert result[0].id == sample_article.id

    def test_duplicate_urls(self):
        n = Normalizer()
        articles = [
            Article(
                id="a1",
                source="github",
                source_id="r1",
                url="https://example.com/1",
                text="content one",
            ),
            Article(
                id="a2",
                source="github",
                source_id="r2",
                url="https://example.com/1",
                text="content two",
            ),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 1

    def test_duplicate_content_fingerprint(self):
        n = Normalizer()
        shared_prefix = "A" * 100 + "unique suffix"
        articles = [
            Article(
                id="a1",
                source="github",
                source_id="r1",
                url="https://example.com/1",
                text=shared_prefix + " version 1",
            ),
            Article(
                id="a2",
                source="github",
                source_id="r2",
                url="https://example.com/2",
                text=shared_prefix + " version 2",
            ),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 1

    def test_different_content_same_url_prefix(self):
        n = Normalizer()
        articles = [
            Article(
                id="a1",
                source="github",
                source_id="r1",
                url="https://example.com/1",
                text="First article content here",
            ),
            Article(
                id="a2",
                source="github",
                source_id="r2",
                url="https://example.com/2",
                text="Second article content here",
            ),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 2

    def test_fingerprint_case_insensitive(self):
        n = Normalizer()
        articles = [
            Article(
                id="a1",
                source="github",
                source_id="r1",
                url="https://example.com/1",
                text="Hello World",
            ),
            Article(
                id="a2",
                source="github",
                source_id="r2",
                url="https://example.com/2",
                text="hello world",
            ),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 1

    def test_empty_text_skipped(self):
        n = Normalizer()
        articles = [
            Article(id="a1", source="github", source_id="r1", text=""),
            Article(id="a2", source="github", source_id="r2", text=""),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 0

    def test_many_articles(self, sample_articles):
        n = Normalizer()
        result = n.deduplicate(sample_articles)
        assert len(result) == len(sample_articles)

    def test_preserves_order(self):
        n = Normalizer()
        articles = [
            Article(id="a1", source="github", source_id="r1", url="https://a.com", text="first"),
            Article(id="a2", source="github", source_id="r2", url="https://b.com", text="second"),
            Article(id="a3", source="github", source_id="r3", url="https://a.com", text="first"),
        ]
        result = n.deduplicate(articles)
        assert len(result) == 2
        assert result[0].id == "a1"
        assert result[1].id == "a2"

    def test_minhash_lsh_fuzzy_deduplicate(self):
        """測試 MinHash LSH 是否能抓到高度相似但不完全相同的內容。"""
        n = Normalizer(threshold=0.8)

        # 兩段非常相似的長文本
        text1 = "This is a very long text about AI agents and intelligence. " * 10
        text2 = "This is a very long text about AI agents and intelligence! " * 10

        articles = [
            Article(id="a1", source="github", source_id="s1", url="https://u1.com", text=text1),
            Article(id="a2", source="github", source_id="s2", url="https://u2.com", text=text2),
        ]

        result = n.deduplicate(articles)
        # 因為相似度很高 (>0.8)，應該被去重
        assert len(result) == 1
