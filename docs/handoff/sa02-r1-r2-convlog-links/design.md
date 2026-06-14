# Phase 3 設計 — SA-02 残課題 R1/R2: conversation_logs contact_id / company_id 補完

**対象ADR**: ADR-096  
**recon**: docs/handoff/sa02-r1-r2-convlog-links/recon.md  
**日付**: 2026-06-14  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

ADR-096 の既存パターンを応用:

- **既存パターン（ADR-096 company_id 補完）**: `_get_company_id_for_lead(db, lead_id)` が `deals` テーブルから `company_id` を補完する実装が `conv_log_writer.py:61` および `conv_log_writer.py:107-121` に存在する。今回の R1 はこのパターンをそのまま `contacts` テーブルへ応用する（`_get_contact_id_for_lead`）。
- **既存パターン（ADR-096 手動記録）**: `conv_logs.py` の `create_conv_log` で deals/company_id 補完が webhook 経由では行われていたが手動記録では欠落していた（R2）。webhook 経由と手動記録の INSERT 列を統一することで `v_company_stats` 集計の整合性を確保する。
- **ADR-072 遵守**: `db.commit()` 直後に `reset_tenant_context()` を呼ぶパターンは既存実装に準拠（変更なし）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `write_conversation_log()` に `contact_id` パラメータがある | `inspect.signature()` テスト（`test_conv_log_writer.py::test_signature_has_required_params`） |
| `contact_id` が INSERT SQL に含まれる | `test_conv_log_writer.py::test_write_conversation_log_explicit_contact_id`（call_args確認） |
| `lead_id` あり・`contact_id` 省略時に自動補完される | `test_conv_log_writer.py::test_write_conversation_log_auto_resolves_contact_id` |
| `lead_id=None` で両ヘルパーが呼ばれない | `test_conv_log_writer.py::test_write_conversation_log_no_lead_id` |
| 手動記録 INSERT に `company_id` が含まれる | `test_conv_logs_router.py::test_create_conv_log_company_id_in_insert_params` |
| audit_log に `company_id` が含まれる | `test_conv_logs_router.py::test_create_conv_log_company_id_in_audit_log` |
| `company_id=None` でも 201 を返す | `test_conv_logs_router.py::test_create_conv_log_no_company_id_still_returns_201` |
| `_get_contact_id_for_lead` がインポートできる | `test_conv_log_writer.py::test_import` |
| `_get_contact_id_for_lead` が contact なしで None を返す | `test_conv_log_writer.py::test_get_contact_id_no_contact` |
| `_get_contact_id_for_lead` が contact ありで id を返す | `test_conv_log_writer.py::test_get_contact_id_found` |

---

## 技術 How・KPI

**KPI**:
- R1: 新規自動ログ（webhook/DM）で `contact_id` が既存 contact ありの場合に NULL にならない（`_get_contact_id_for_lead` が1行返すとき）
- R2: 手動記録で `company_id` が deals ありの場合に NULL にならない（`_get_company_id_for_lead` が1行返すとき）
- R3: 対象外（`v_company_stats` 本番データ確認は R1/R2 マージ後の別タスク）

**技術選択**:
- `contact_id` の自動解決: `contacts WHERE lead_id=X ORDER BY is_primary_contact DESC, id ASC LIMIT 1`（primary contact 優先、次点は最初に登録されたもの）
- 後方互換: `contact_id: int | None = None` でオプション引数化（既存呼び出し元への変更不要）

---

## 弊害・トレードオフ

| リスク | 対策 |
|--------|------|
| `_get_contact_id_for_lead` が contacts 未登録リードで None を返す | NULL 許容列のため問題なし。保存は継続される |
| 手動記録でも `_get_company_id_for_lead` が deals SELECT を1回追加 | 1 SELECT のみ。パフォーマンス許容範囲 |
| シグネチャ変更で呼び出し元が壊れる | `contact_id` はオプション引数（default=None）。後方互換あり |
| 既存テストの `db.execute` 呼び出し回数への影響 | `test_discord_inbox.py::test_dm_writer_creates_new_lead` の side_effect を8件に更新 |

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md 作成（docs/handoff/sa02-r1-r2-convlog-links/recon.md） | Generator |
| 2 | design.md 作成（本ファイル） | Generator |
| 3 | R1実装: `_get_contact_id_for_lead()` 追加・`write_conversation_log()` 拡張 | Generator |
| 4 | R2実装: `conv_logs.py` に `_get_company_id_for_lead` 追加 | Generator |
| 5 | テスト更新: `test_conv_log_writer.py`（8→12件）・`test_conv_logs_router.py`（8→12件）・`test_discord_inbox.py` side_effect 修正 | Generator |
| 6 | pytest full suite 実行・PASS確認 | Generator |
| 7 | CI確認（Backend Tests・Process Artifacts Gate） | Generator |

---

## 継続

- R1/R2 マージ後: R3 Stage 2（`v_company_stats` 本番データ確認）を Shingo GO 付きで実施
- 旧データ backfill（マージ前に作成された NULL レコードの補完）はこの PR 対象外
- 旧データ backfill の必要性は本番での NULL 率確認後に判断（R3 タスクで追記）
