# design.md：便1b — 会話ログの背骨必須化

> この文書は何か（素人向け1行説明）：全ての会話ログが必ず lead（親）に紐づいて保存されるよう、唯一の穴（送信エコー経路）を塞ぎ、古い宛名なし1件に遡って lead を作り、DBに鍵をかける変更手順書。

- 親: docs/specs/transaction-flow/README.md（K1/K2・KGI承認2026-07-02）／兄弟: 便1a（PR #2743・EV-20260703-001）
- recon: /tmp/recon_ben1b.txt（2026-07-03。呼び出し元4経路のうち Meta echo のみ lead=None 許容と特定。本番NULL: tenant_004=1件(2026-05-14 meta_messenger)・tenant_006=3件(DEMO)）

## KPI（○×・数値）
P1 echo経路: 未知PSIDのecho受信で outbound lead が1件作成され conv に紐づく（テスト1本 green）
P2 writerガード: write_conversation_log(lead_id=None) が ValueError（負のテスト green）
P3 backfill: tenant_004 conv lead_id NULL 1→0・[便1b]遡及lead=1件
P4 制約: tenant_004 conversation_logs.lead_id is_nullable=NO／tenant_006 はNOTICEスキップ
P5 既存テスト全緑・受信経路(Meta/Discord/手動)の非破壊

## 変更（§3〜§5参照）／触らない範囲: Discord/手動経路・conv_logs検索API・翻訳系・便2以降
## 外部・過去事例: 便1a（条件付きSET NOT NULL・遡及逆造成）と同型。fail-loud guard は conv_log_writer 既述の設計思想（ADR-096）に整合。
## 維持の仕組み
- 守り手: migrations/20260703_020000_conv_backbone_ben1b.sql（DB制約）＋ backend/tests/test_conv_backbone_ben1b.py（負のテスト常時CI: .github/workflows の pytest 系）
- 対象: lead に繋がらない会話ログが作れてしまうこと（K1/K2崩壊）

## 実装メモ
- echo の穴埋めは webhook.py の Meta echo 経路に限定する。
- backfill は tenant_004 の orphan 1 件を回収し、tenant_006 は NULL が残るため NOTICE でスキップする。
- `backend/app/services/tenant.py` は `conversation_logs` 生成経路を持たないため、grep 結果は 0 件だった。
