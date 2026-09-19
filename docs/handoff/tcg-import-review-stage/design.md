# Phase 3 設計 — tcg-import-review-stage

**対象ADR**: ADR-154
**recon**: docs/handoff/tcg-import-review-stage/recon.md
**日付**: 2026-09-05
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例: AWS Kinesis / Kafka の Dead Letter Queue（処理できないメッセージを別キューに退避し後から再処理する）→ 我々への応用: 未解決仕入元がいる場合は `source_messages` を書かず `pending_review` に退避し、解決後に commit で再処理する
- 事例: GitHub の Draft PR → Ready for Review フロー（人間の確認ゲートを設けてから本線に統合）→ 我々への応用: 取り込みを保留し、仕入元を全員登録してから commit エンドポイントで確定する

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| 未解決仕入元が 1 件以上のとき source_messages が 1 件も書かれない | `pytest tests/test_tcg_line_import.py::test_import_unresolved_does_not_write_source_messages` |
| 未解決 0 件のときは従来どおり source_messages が書かれエンキューされる | `pytest tests/test_tcg_line_import.py::test_import_zero_unresolved_writes_source_messages` |
| 解決済み仕入元が混在していても未解決が 1 件でも保留になる | `pytest tests/test_tcg_line_import.py::test_import_partial_unresolved_also_blocks` |
| 保留時に pending_messages と unresolved_names が import_jobs に保存される | `pytest tests/test_tcg_line_import.py::test_import_unresolved_stores_pending_messages` |
| 窓計算が JST 基準であること（旧 UTC 基準 33h を是正） | `pytest tests/test_tcg_line_import.py::test_compute_window_jst_basis` |
| 24h 超の pending_review ジョブが discarded に更新される | `pytest tests/test_tcg_line_import.py::test_discard_stale_pending_jobs_calls_update` |

---

## 技術 How・KPI

- KPI: 未解決仕入元がいるときの取り込み後に source_messages 件数が増えない（0 件）
- 技術選択: import_jobs に `review_status`（TEXT NOT NULL DEFAULT 'ok'）+ `pending_messages`（JSONB）を追加して保留状態を管理する。別テーブルにしない（ADR-154 の SSoT 方針）
- JST 定数: `JST = timezone(timedelta(hours=9))` を使用（#3305 で追加済み・ZoneInfo を使わず統一）

---

## 弊害・トレードオフ

- 未解決仕入元がいる場合、解決済みの分も含めて全件保留になる（意図した挙動・partial import の複雑さを避けるため）
- 保留ジョブは 24h で自動破棄。その後は再アップロードが必要
- `pending_messages` の JSONB は大きくなりうるが、24h で NULL クリアされる

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration: import_jobs に 5 列追加 | Generator |
| 2 | svc: import_line_export に未解決分岐を追加 | Generator |
| 3 | router: resolve / commit / pending エンドポイント追加 | Generator |
| 4 | task: 破棄タスク + celery beat 登録 | Generator |
| 5 | test: 9 件追加（48 件 GREEN） | Generator |

---

## 維持の仕組み

守り手: backend/tests/test_tcg_line_import.py（test_import_unresolved_does_not_write_source_messages が保留時の source_messages 非書き込みを毎回検証）

---

## 継続

- 完了後の監視: 次回取り込み時に review_status='pending_review' が正しく返るか目視確認
- 次フェーズ: フロントエンド確認画面（別 PR）
