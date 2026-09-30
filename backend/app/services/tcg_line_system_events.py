"""
LINE お知らせ（システムイベント）判定を1か所にまとめる表。

- PC 用パーサ（tcg_line_import_svc.py）とスマホ用パーサ（両方の呼び出し元）が
  同じ13パターンの表を使うことで、判定方法の重複・食い違いを防ぐ。
- 判定対象は display_name + " " + 本文の1行目（1行目が空なら display_name のみ）。
  旧 PC 実装（_SYSTEM_EVENT_RE, display_name + 本文全体に対する search）と同じ結合方式で、
  行全体一致（^...$）にすることで「ウェビナーに参加しました」等の業務文を誤判定しない。
- 出典: docs/handoff/line-parser-unify/recon.md（Q1/Q8/Q13）、design.md §3 C1、
  デプロイ済み SHA 5f32ca89b710b0dc0e2f4b456527f4ac1d0808bc 時点の PC 実ファイル調査。
"""
from __future__ import annotations

import re

# 各パターンは「表示名 + 本文1行目」の連結文字列に対して re.match（^ 前提）で判定する。
# 全て行全体一致（$ で終端を固定）。
SYSTEM_EVENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # --- 既存4種（旧 _SYSTEM_EVENT_RE がカバーしていた範囲。表現をそのまま踏襲） ---
    ("join", re.compile(r"^.+?がグループに参加しました。?$")),
    ("invite", re.compile(r"^.+?をグループに招待しました。?$")),
    ("invite_cancel", re.compile(r"^.+?招待をキャンセルしました。?$")),
    ("recall", re.compile(r"^.+?がメッセージの送信を取り消しました。?$")),

    # --- すり抜け8種（PC 実ファイルで判定漏れが確認された文言。recon Q8） ---
    # 1. 招待＋しばらくお待ちください（招待の直後に続く定型文が末尾につき、旧実装の $ 一致に失敗していた）
    ("invite_wait", re.compile(
        r"^.+?をグループに招待しました。招待中の友だちが参加するまでしばらくお待ちください。?$"
    )),
    # 2. グループから削除しました
    ("removed", re.compile(r"^.+?をグループから削除しました。?$")),
    # 3. グループを退会しました
    ("left", re.compile(r"^.+?がグループを退会しました。?$")),
    # 4. アナウンスしました（<u>タグ付き。本番実例は全件 <u>...</u> 形式）
    ("announce", re.compile(r"^.+?が<u>アナウンスしました</u>。?$")),
    # 5. グループ通話が開始されました
    #    本文自体に送信者名は含まれない（display_name にのみ現れる）ため、
    #    display_name + 本文1行目 の連結文字列では先頭に任意の名前が付く。
    ("call_start", re.compile(r"^.+?グループ通話が開始されました。?$")),
    # 6. グループ通話が終了しました
    ("call_end", re.compile(r"^.+?グループ通話が終了しました。?$")),
    # 7. 新しいノートを作成しました（同上、本文に送信者名なし）
    ("note_created", re.compile(r"^.+?新しいノートを作成しました。?$")),
    # 8. LINE WORKS からトークに参加しました（1行目のみで判定。2行目の括弧書きは対象外）
    ("line_works_join", re.compile(r"^.+?からトークに参加しました。?$")),
    # 9. グループ名を「...」に変更しました（recon Q8/Q13 で本番実例1件を確認済み）
    ("name_changed", re.compile(r"^.+?グループ名を[「『].+?[」』]に変更しました。?$")),
]


def match_system_event(display_name: str, body: str) -> str | None:
    """LINE のお知らせ（システムイベント）文言に一致するか判定する。

    判定対象は display_name + " " + 本文の1行目（1行目が空文字なら display_name のみ）。
    一致すればパターンのラベルを、一致しなければ None を返す。
    """
    first_line = body.split("\n", 1)[0]
    combined = f"{display_name} {first_line}" if first_line else display_name
    for label, pattern in SYSTEM_EVENT_PATTERNS:
        if pattern.match(combined):
            return label
    return None
