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
| 軽微 | webhook.py の `_persist_meta_message` の行番号（2回目の反映で :584 としたが誤り。正は :583・3回目 P1 で修正） | 軽微 | design.md §4-7 |

誤りの原因: 手元の古い写しで行番号を読んだ。以後の行番号は origin/main で読む。

## 3回目

対象 HEAD: 26b92f1a7。判定: REVISE。N1・N2・N3 と再確認 C2〜C5 は ○。

| # | 指摘 | 区分 | 反映 |
|---|---|---|---|
| P1 | `_persist_meta_message` は backend/app/routers/webhook.py:583（:584 は誤り） | 必須 | recon.md・design.md §4-7・本表2回目の軽微欄 |
| P2 | 系統B は仕入元専用の記載は docs/handoff/whatsapp-intake/README.md:49（:98 は誤り） | 必須 | design.md §8 |
| P3 | WhatsApp の推奨案は docs/handoff/whatsapp-intake/README.md:20-22（:67-73 は誤り） | 必須 | recon.md §1 |
| P4 | conversation-unification/design.md:8 の 2026-07-09 は実測日で承認日ではない | 推奨 | recon.md §1 |
| P5 | K5 に Evaluator の Discord 確認（kgi.md:16）を足す | 推奨 | design.md §6 |
| P6 | conftest.py:2044 は occurred_at を既に持つ。「無い列だけ足す」にする | 推奨 | design.md §9 便2 |
| P7 | 状態の行を更新する | 推奨 | design.md 冒頭 |

## 4回目

対象 HEAD: 62562cbc9。判定: APPROVE（設計合格）。P1〜P7 と C2〜C5 は ○。design.md・recon.md の file:line は origin/main で全件一致（ずれ0件）。

| # | 指摘 | 区分 | 反映 |
|---|---|---|---|
| Q1 | design.md §5 A と ADR-1064 の「方針が承認済み」の出典が origin/main に無い | 推奨 | 文言を「既存の設計の方針・承認の記録はその文書内に無い」に改めた |

R7（成約分析が窓口不明のリードを数えない件）は PO 判断待ちで、審査の対象外。
