"""Notifier — 多渠道通知發送器（基於 Apprise）。."""

from __future__ import annotations

from typing import TYPE_CHECKING

import apprise
from loguru import logger

from cortexflow.config.settings import settings

if TYPE_CHECKING:
    from cortexflow.core.schema import ReportContent


class Notifier:
    """封裝 Apprise 以發送多渠道通知。."""

    def __init__(self) -> None:
        """初始化 Apprise。."""
        self.apobj = apprise.Apprise()
        if settings.notification_urls:
            urls = [u.strip() for u in settings.notification_urls.split(",") if u.strip()]
            for url in urls:
                self.apobj.add(url)
            logger.debug("Notifier 已初始化，共 {count} 個渠道", count=len(urls))

    async def notify(self, report: ReportContent) -> bool:
        """發送通知。."""
        if not settings.notification_urls:
            return False

        title = f"🚀 CortexFlow 情報摘要: {report.title}"

        # 建立簡短摘要
        body_parts = []
        if report.key_points:
            body_parts.append("📌 核心洞察:")
            for pt in report.key_points[:3]: # 只取前三點
                body_parts.append(f"• {pt}")

        if report.links:
            body_parts.append(f"\n🔗 完整報告連結: {report.links[0]}")

        body = "\n".join(body_parts)

        try:
            # apprise 的 notify 是同步的，但在 async 環境中執行通常沒問題，
            # 若有延遲疑慮可使用 run_in_executor。
            # 這裡我們先簡單調用。
            result = self.apobj.notify(
                title=title,
                body=body,
            )
            if result:
                logger.info("通知已成功發送至所有頻道")
            else:
                logger.warning("通知發送失敗（可能渠道配置有誤）")
            return bool(result)
        except (ValueError, RuntimeError) as e:
            logger.error("發送通知時發生連線或參數錯誤: {error}", error=e)
            return False
        except Exception as e:  # noqa: BLE001
            logger.error("發送通知時發生非預期錯誤: {error}", error=e)
            return False
