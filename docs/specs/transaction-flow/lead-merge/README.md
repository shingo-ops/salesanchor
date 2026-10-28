# リードをまとめる（lead-merge）

> この文書は何か（専門用語なしの1行）:
> 同じお客さまが2件のリードに分かれたとき、1件にまとめる機能を、受信箱からも安全に使えるようにする仕様書の表紙。

- 親（表紙）: [取引フロー README](../README.md)（K1「全ての子は lead にぶら下がる」を守る子テーマ）
- 区分（STANDARD-WORKFLOW §1.8）: **拡張**（ADR-119 の統合を直し、入口を受信箱に足す）
- 日付: 2026-10-28
- PO: しんご
- ステータス: あるべき姿 = PO 発言転記（2026-10-28）／ KGI = 本書の案（PO の決定3件から導出）／ 設計 = 設計審査済み（自己審査）
- 関連 ADR: [ADR-1049](../../../adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md)（本件の決定・Amends ADR-119）、[ADR-119](../../../adr/ADR-119-lead-channels-and-lead-merge.md)、ADR-098（自動で同一人物と判定しない）、ADR-095（同じ事実は1か所）
- 議事録: [docs/handoff/inbox-brushup/README.md](../../../handoff/inbox-brushup/README.md)

## 構成

| ファイル | 中身 |
|---|---|
| [ideal-state.md](./ideal-state.md) | PO の言葉（原文のまま） |
| [kgi.md](./kgi.md) | 合格条件（数と ○×） |
| [lead-merge-recon.md](../../../handoff/inbox-brushup/lead-merge-recon.md) | 今の作り（ファイル:行） |
| [design.md](./design.md) | 直し方・画面・試験・大きさの基準・維持の仕組み |

## 境界

- 対象: 統合の処理（`merge_leads`）、統合の窓（`MergeLeadModal`）、受信箱カルテ下の「⋯」メニュー。
- 対象外: リードの削除（`delete_lead`）、FK の無い4表への FK 追加、窓口の記録が無い 49 件の結び付け方。いずれも PO に未確認のため別の回で扱う。
