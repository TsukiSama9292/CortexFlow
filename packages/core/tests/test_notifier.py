"""Tests for the Notifier module."""

from __future__ import annotations

from unittest.mock import patch

from cortexflow.config.settings import settings
from cortexflow.reporter.notifier import Notifier


class TestNotifier:
    @patch("apprise.Apprise")
    async def test_notifier_init_with_urls(self, mock_apprise_class):
        """測試 Notifier 是否正確讀取設定並加入 URL。"""
        mock_apprise_instance = mock_apprise_class.return_value

        with patch.object(settings, "notification_urls", "slack://token,tgram://bot"):
            notifier = Notifier()
            assert notifier.apobj == mock_apprise_instance
            # 檢查是否呼叫了兩次 add
            assert mock_apprise_instance.add.call_count == 2

    @patch("apprise.Apprise")
    async def test_notify_success(self, mock_apprise_class, sample_report_content):
        """測試發送通知的邏輯。"""
        mock_apprise_instance = mock_apprise_class.return_value
        mock_apprise_instance.notify.return_value = True

        with patch.object(settings, "notification_urls", "slack://test"):
            notifier = Notifier()
            result = await notifier.notify(sample_report_content)

            assert result is True
            assert mock_apprise_instance.notify.called
            # 檢查標題是否包含報告標題
            args, kwargs = mock_apprise_instance.notify.call_args
            assert sample_report_content.title in kwargs["title"]

    @patch("apprise.Apprise")
    async def test_notify_no_urls(self, mock_apprise_class, sample_report_content):
        """測試當沒有設定 URL 時不發送通知。"""
        with patch.object(settings, "notification_urls", ""):
            notifier = Notifier()
            result = await notifier.notify(sample_report_content)
            assert result is False
            assert not mock_apprise_class.return_value.notify.called
