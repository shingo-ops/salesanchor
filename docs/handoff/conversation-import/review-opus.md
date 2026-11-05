# 設計審査の記録（会話ファイルの取り込み）

同じ Opus による審査で、独立した第三者の審査ではない。

## 1回目（2026-11-06・クラウドの Opus・対象 337d873cc）

判定: REVISE（直す必要あり）

| # | 指摘 | 区分 | 反映 |
|---|---|---|---|
| M1 | 画像の送信（leads.py:2412）にも返信の見張りが要る | 必須 | design.md §4-6・§6・§9 |
| M2 | 試験用の表の形 7ファイルに is_manual 等の列を足す | 必須 | design.md §9・§7 R8 |
| M3 | 新しい router は tenant_table_ref を使い、commit 後に reset_tenant_context（ADR-072） | 必須 | design.md §4-5 |
| M4 | 「前のメッセージを読む」で足した分が控えの上書きで消える | 推奨 | design.md §4-8・§6 |
| M5 | 成約分析は窓口が messenger/instagram のリードしか数えない | 推奨 | 事実を確かめた（recon §11）。PO 判断待ち（design.md §7 R7） |
| M6 | 予備の SELECT と before の行が無いときの返事 | 推奨 | design.md §4-8・§6 |

## 2回目（2026-11-06・クラウドの Opus・対象 b044483b4）

判定: REVISE。M1・M3・M4・M5・M6 は ○。M2 は ×（8つ目のファイルの漏れ）。

| # | 指摘 | 区分 | 反映 |
|---|---|---|---|
| N1 | 試験用の表の形は8ファイル（backend/tests/test_outbound_draft_send.py:94 が漏れ）。conftest.py は :156 | 必須 | design.md §9・§7 R8、recon §11 |
| N2 | reset_tenant_context は dependencies.py:339（:166 は誤り） | 必須 | design.md §4-5、recon §11 |
| N3 | 既存の試験 test_messages.py:335-354 が古い順を前提にしている | 推奨 | design.md §7 R4・§9 便1 |
| 軽微 | webhook.py:583 は :584 | 軽微 | design.md §4-7 |

誤りの原因: 手元の古い写しで行番号を読んだ。以後の行番号は origin/main で読む。

## 3回目

（再審査の後に書く）
