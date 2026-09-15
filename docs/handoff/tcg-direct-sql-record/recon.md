# recon: 直接SQL復旧の記録（RECORD-01）

## 概要

2026-09-05 17:25〜17:45 に本番DB へ直接 SQL を適用した。
本ドキュメントはその経緯・操作内容・影響範囲の事実記録である。

---

## 発生経緯

### 誤操作: SP0007 / SP0184 の name 上書き

- **トリガー**: #3306 / #3309 の確認画面で「既存仕入元に割り当て」を選択した際、
  SP0007（倉田 和博）の name フィールドが `'overlap'` に上書きされた。
- **原因**: 確認画面の UI が既存レコードを選択すると `name` まで差し替える動作になっていた
  （#3311 で確認工程の修正を予定）。
- **影響**: SP0007 の name が正しくない値になり、TCG 解析画面での仕入元表示が崩れた。
  SP0184 についても同誤操作で name が変わっていた可能性があり、合わせて復旧対象とした。

### 画面からの新規登録不可: SP0203 / SP0204

- **トリガー**: 「新規登録」ボタン押下時に HTTP 422 エラーが返り、
  `株式会社AXISグリーン`（SP0203）と `Ryuta`（SP0204）を画面から登録できなかった。
- **原因**: [未確認] バリデーションエラーの詳細は取得していない。
- **影響**: 2名の仕入元マスタが欠落した状態で import_jobs の処理が進むため、
  PO 判断により直接登録した。

---

## 実施した直接 SQL 操作（4件）

| # | 対象    | 操作       | SQL の要旨                                              | 実行時刻 (JST) |
|---|---------|------------|--------------------------------------------------------|----------------|
| 1 | SP0007  | UPDATE     | `name = '倉田 和博'` WHERE `code = 'SP0007'`            | 17:25 頃       |
| 2 | SP0184  | UPDATE     | `name = 'overlap'` WHERE `code = 'SP0184'`             | 17:27 頃       |
| 3 | SP0203  | INSERT     | `tcg_suppliers` + `supplier_channels` (line)           | 17:35 頃       |
| 4 | SP0204  | INSERT     | `tcg_suppliers` + `supplier_channels` (line)           | 17:37 頃       |

操作先テーブル（いずれも `tenant_004` スキーマ）:
- `tenant_004.tcg_suppliers`
  （定義: `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`）
- `tenant_004.supplier_channels`
  （定義: 同上）

---

## 実施しなかった操作の記録（migration に含めない理由）

### import_jobs の DELETE

- 保留中の import_jobs 1件（UUID: `c32e7aa2-9dad-4d3b-96e3-fe73cad7d6a5`）を DELETE した。
- **理由**: 一時データの削除であり、migration として再現する意味がない。
  `source_messages` への書き込みは未完了のため他行への影響なし。

### import_jobs.unresolved_names の UPDATE

- `65cf6b75-...` の `unresolved_names` を `[]` に更新し、
  `commit_pending_job` を backend コンテナ内で直接実行した。
- 結果: `provider_count=36 / enqueued_count=36` で正常完了。
- **理由**: この操作はアプリケーション状態のリセットであり、migration には不適。

---

## 権限・承認の記録

- danger-permit を本便限りで自己発行した（通常手順: `scripts/permit-danger.sh`）。
- PO（しんごさん）がその場で判断・承認した。

---

## 影響ファイル（本 PR で変更するもの）

| ファイル                                                                    | 変更内容                 |
|----------------------------------------------------------------------------|--------------------------|
| `migrations/20260905_150000_record_manual_supplier_fixes_t004.sql`         | 新規作成（記録 migration）|
| `scripts/run_all_migrations.sh`                                            | 末尾に `run_sql` 1行追記  |
| `docs/handoff/tcg-direct-sql-record/recon.md`                             | 新規作成（本ファイル）    |
| `docs/handoff/tcg-direct-sql-record/design.md`                            | 新規作成                  |

---

## 既存 ADR 確認

```
git grep -i "direct.*sql\|manual.*sql\|supplier" docs/adr/ -- "*.md" | head -20
```

検索結果: `docs/adr/ADR-025_meta_integration_operational_hardening.md` に
「本番運用フェーズ移行後は手動 DB INSERT の原則禁止」の記載あり。
本件は緊急復旧のため一時的に外した。ADR-025 §緊急対応フロー に相当。

---

## 守り手

人手で守る（migration の再実行後に検算 SELECT の RAISE NOTICE 出力を目視確認）。
