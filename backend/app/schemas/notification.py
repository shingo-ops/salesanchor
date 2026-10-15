from __future__ import annotations

"""通知の種類の SSOT（design.md §3-1）。"""

from enum import Enum


class NotificationEventType(str, Enum):
    """通知の種類の SSOT。

    ここに無い値は API が拒否する。送信元が存在しない種類を増やしてはいけない
    （recon §6: customer_created / deal_won / invoice_issued は送信元ゼロのため除外）。
    値は notification_channels.event_types に JSON 配列として保存され、
    送信時は LIKE '%値%' の部分一致で照合される（notifications.py:112）ため、
    **ある値が他の値の部分文字列になってはいけない**。
    """

    lead_assigned = "lead_assigned"                      # 商談の担当アサイン（本 PR 新設）
    meta_message_received = "meta_message_received"      # 既存: webhook.py:938-947
    tcg_distribution_error = "tcg_distribution_error"    # 既存: tcg_distribution_svc.py:857-866
