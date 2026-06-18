# SA-02 段階2 移行 事前確認チェックリスト（Shingo GO前）

> **このチェックリストは Shingo が GO を出す前に確認するものです。**
> 実行手順は `design.md §本番実行チェックリスト` を参照してください。

---

## 過去の試行履歴

| 試行 | 日時 | 結果 | 原因 | 対応PR |
|------|------|------|------|--------|
| R1 | 2026-06-15 | ❌ inserted=0 | asyncpg + SET LOCAL 非互換 | #2217 |
| R2 | 2026-06-15 | ❌ inserted=0 | f-string 内 JSON literal が format 指定子として解釈 | #2232 |
| R3 | 2026-06-16 | ✅ 完了（coverage 100%・errors=0） | — | #2254/#2270 |

> R1・R2 ともに DB への変更は 0 件。ロールバック不要。

---

## GO前確認項目

### コード・テスト

- [ ] PR #2232 がマージ済み（f-string 修正・テスト 15 件 PASS）
- [ ] `backend/tests/test_sa02_stage2_preflight.py` 全 15 件 PASS（CI 確認済み）
  - `test_no_raw_json_literal_in_fstring` — JSON literal 直書きがないこと
  - `test_insert_sql_contains_jsonb_build_object` — jsonb_build_object が使われること
  - `test_fstring_insert_sql_compiles_without_error` — exec しても ValueError が出ないこと

### スクリプト確認

- [ ] `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:191` が `jsonb_build_object()` を使っていること（JSON literal 直書きがないこと）
- [ ] `--dry-run` フラグを VPS で実行し、対象件数が妥当であること
- [ ] dry-run が途中でエラーなく完了すること（asyncpg・SQL エラーが出ないこと）

### 環境確認

- [ ] VPS が正常稼働中（docker compose ps で全コンテナ GREEN）
- [ ] 直前の backup / snapshot を確認済み（不要だが念のため）
- [ ] ロールバック手順 `rollback.md` を読んだ

### リスク確認

- [ ] 移行は conversation_logs への追加のみ（meta_messages は変更しない）
- [ ] 冪等性確認済み（ON CONFLICT DO NOTHING で再実行可）
- [ ] analysis._source = 'sa02_stage2_migration' でロールバック対象を正確に特定できる

---

## GO 宣言

Shingo が確認した場合は、以下にコメントして PR #2232 に GO 記録を残してください。

```
GO: Shingo YYYY-MM-DD
SA-02 段階2 移行実行を承認します。
```

---

## R3 完了記録（2026-06-16）

| 項目 | 結果 |
|------|------|
| 実行日時 | 2026-06-16 |
| errors | 0 |
| rollback | 未実行・不要 |
| tenant_004 (highlife-jpn) | meta_total=5 / conv_from_meta=5 / coverage=100% / gap=0 |
| tenant_006 (tenant-review) | meta_total=10 / conv_from_meta=14 / coverage=140% / gap=-4 |
| tenant_006 gap=-4 の説明 | 前回 R3 で挿入済み 4 件が残っているためで、未移行ではない |
| analysis->>'_source'='sa02_stage2_migration' 合計 | tenant_004=5 / tenant_006=14 / total=19 |
| deploy/main反映 | 未実行（#2254/#2270 は develop merge済み・追加本番作業は不要） |

> **#2272 は validate-pr-ownership 修正 PR であり、SA-02 完了記録とは無関係。**
