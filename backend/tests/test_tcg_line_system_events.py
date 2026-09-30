"""
tcg_line_system_events.match_system_event の単体テスト（DB 不要）。

- 15 パターンそれぞれの一致例（実ファイルの文言の形。個人名は仮名に置換。recon.md Q8/Q13、
  スマホ由来2文型は recon 追補5）
- 一致しない例（業務文の誤判定防止）
- LINE WORKS 参加は本文1行目のみで一致すること（2行目の括弧書きは対象外）
"""
from __future__ import annotations

from app.services.tcg_line_system_events import match_system_event

# ─────────────────────────────────────────────────────────────────────────────
# 13パターンの一致例
# ─────────────────────────────────────────────────────────────────────────────


def test_match_join():
    assert match_system_event("田中花子", "がグループに参加しました。") == "join"


def test_match_invite():
    assert match_system_event("山田太郎", "田中花子をグループに招待しました。") == "invite"


def test_match_invite_cancel():
    assert match_system_event("山田太郎", "田中花子への招待をキャンセルしました。") == "invite_cancel"


def test_match_recall():
    assert match_system_event("山田太郎", "がメッセージの送信を取り消しました。") == "recall"


def test_match_invite_wait():
    """招待＋しばらくお待ちください（旧実装が末尾一致に失敗していたすり抜けパターン）。"""
    assert (
        match_system_event(
            "山田太郎",
            "田中花子をグループに招待しました。招待中の友だちが参加するまでしばらくお待ちください。",
        )
        == "invite_wait"
    )


def test_match_removed():
    assert match_system_event("山田太郎", "田中花子をグループから削除しました。") == "removed"


def test_match_left():
    assert match_system_event("田中花子", "がグループを退会しました。") == "left"


def test_match_announce():
    assert match_system_event("山田太郎", "が<u>アナウンスしました</u>。") == "announce"


def test_match_call_start():
    assert match_system_event("グループ通話", "グループ通話が開始されました") == "call_start"


def test_match_call_end():
    assert match_system_event("グループ通話", "グループ通話が終了しました。") == "call_end"


def test_match_note_created():
    assert match_system_event("ノート", "新しいノートを作成しました。") == "note_created"


def test_match_line_works_join():
    """LINE WORKS 参加は本文1行目だけで一致する（2行目の括弧書きは対象外）。"""
    body = (
        "「LINE WORKS」からトークに参加しました。\n\n"
        "(グループ機能のノート/アルバム/イベント/投票には対応していません。)"
    )
    assert match_system_event("スタッフ ビジネス版LINE", body) == "line_works_join"


def test_match_name_changed():
    assert match_system_event("山田太郎", "グループ名を「新グループ名」に変更しました。") == "name_changed"


# ─────────────────────────────────────────────────────────────────────────────
# スマホ由来の2文型（recon 追補5。表の出典が PC 実ファイルのみだったため漏れていた）
# ─────────────────────────────────────────────────────────────────────────────


def test_match_note_posted():
    assert match_system_event("一真", "一真がノートに投稿しました。") == "note_posted"


def test_match_note_posted_android_format():
    """スマホ形式（表示名＋本文）の組み合わせでも一致すること。"""
    assert match_system_event("一真", "がノートに投稿しました。") == "note_posted"


def test_match_voice_call_start():
    assert match_system_event("伊藤晴彦", "グループ音声通話が開始されました。") == "voice_call_start"


def test_match_voice_call_start_android_format():
    """スマホ形式（表示名＋本文）の組み合わせでも一致すること。"""
    assert match_system_event("グループ", "グループ音声通話が開始されました") == "voice_call_start"


def test_no_match_note_summary_business_text():
    """「ノートに在庫をまとめました」は業務投稿でお知らせと誤判定しない。"""
    assert match_system_event("山田太郎", "ノートに在庫をまとめました") is None


def test_no_match_voice_explanation_business_text():
    """「音声で説明しました」は業務投稿でお知らせと誤判定しない。"""
    assert match_system_event("山田太郎", "音声で説明しました") is None


def test_pattern_count_is_fifteen():
    from app.services.tcg_line_system_events import SYSTEM_EVENT_PATTERNS

    assert len(SYSTEM_EVENT_PATTERNS) == 15


# ─────────────────────────────────────────────────────────────────────────────
# 一致しない例（誤判定防止）
# ─────────────────────────────────────────────────────────────────────────────


def test_no_match_whatnot_webinar_business_text():
    """「Whatnot ウェビナーに参加しました」を含む業務文はお知らせと誤判定しない。"""
    assert (
        match_system_event(
            "山田太郎",
            "Whatnot ウェビナーに参加しました。詳細は資料をご確認ください。",
        )
        is None
    )


def test_no_match_price_change_business_text():
    assert match_system_event("山田太郎", "価格を変更しました。ご確認ください。") is None


def test_no_match_box_closing_business_text():
    assert match_system_event("山田太郎", "OP-14 BOX 〆") is None


def test_no_match_fixed_phrase_only_on_second_line():
    """本文2行目にだけ定型文がある投稿は誤判定しない（1行目のみが判定対象）。"""
    body = "商品案内です\nがグループに参加しました。"
    assert match_system_event("山田太郎", body) is None
