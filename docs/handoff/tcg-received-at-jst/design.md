# Phase 3 設計 — tcg-received-at-jst

**対象ADR**: ADR-154
**recon**: docs/handoff/tcg-received-at-jst/recon.md
**日付**: 2026-09-05
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例: backend/tcg_migration/MIGRATION_LOG.md（2026-09-04 手動取り込み実施記録）にて、同プロジェクト内の手動スクリプト `tcg_line_ingest.py` が `JST = timezone(timedelta(hours=9))` + `.replace(tzinfo=JST)` で同一問題を解決済み → 我々への応用: API サービス側も同じパターンで統一する

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| JST 定数が +09:00 である | `pytest tests/test_tcg_line_import.py::test_jst_constant_is_plus9` |
| `"2026-09-03 01:19:00"` を変換した datetime の utcoffset が +09:00 である | `pytest tests/test_tcg_line_import.py::test_received_at_parsed_as_jst_not_utc` |
| DB に渡す received_at パラメータの tzinfo が +09:00 である | `pytest tests/test_tcg_line_import.py::test_received_at_stored_as_jst_in_insert` |

---

## 技術 How・KPI

- KPI: 新規取り込み後の `posted_at` 列が LINE エクスポートの時刻と一致する（0h ずれ）
- 技術選択: `timezone(timedelta(hours=9))` を定数化（手動スクリプトと同一作法・ADR-154 GAS 再現準拠）

---

## 弊害・トレードオフ

- 影響範囲は `import_line_export` API 経由の新規取り込み分のみ
- 手動スクリプト分50件（既存 JST 保存済み）・移行306件（NULL）は変化なし
- 配信 SQL の `AT TIME ZONE 'Asia/Tokyo'` は現状維持（JST aware で保存することで正常動作）

---

## 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | `JST = timezone(timedelta(hours=9))` 定数追加 | Generator |
| 2 | `.replace(tzinfo=JST)` に変更（1行） | Generator |
| 3 | テスト3件追加（RED→GREEN 確認済み） | Generator |

---

## 維持の仕組み

守り手: backend/tests/test_tcg_line_import.py（test_received_at_stored_as_jst_in_insert が DB パラメータの tzinfo を毎回検証）

---

## 継続

- 完了後の監視: 次回取り込み後に配信シートの `posted_at` 列を目視確認
- 移行306件の NULL 解消は別タスク（GAS 側にソースデータなし・優先度低）
