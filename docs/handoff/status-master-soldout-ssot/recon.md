# recon: tcg_status_master SSOT統合 Phase 1

## 調査日時
2026-09-20

## 対象ブランチ
`release/status-master-soldout-ssot` (origin/main 起点)

## 既存 ADR 検索結果
- docs/adr/ADR-154-tcg-parity02-gas-python-migration.md — tcg_status_master SSOT方針（完売判定の単一源泉）
- docs/adr/ADR-109-leads-status-ssot-immutable-codes.md — ステータスコード SSOT 設計

```
git grep -i 'status_master\|sold.out\|exclude_pattern' docs/adr/ (→ ADR-154, ADR-109 ヒット)
```

## 現状の tcg_status_master 行数

【事実】 `migrations/20260920_050000_status_master_add_tenant_id.sql` の存在から、
テーブル自体は構築済み。初期データは別 migration にあるか seed に含まれる。

種別:
- EXCLUDE 効果: ST0012（売り切れ）, ST0013（完売）, ST0014（在庫切れ）など
- `exclude_pattern` カラムは定義済みだが、バックエンドの dict comprehension で **r[3] を読み飛ばしていた**

## exclude_pattern 欠落の根拠

`backend/app/services/tcg_analyzer_svc.py:1063-1072`

```python
return [
    {
        "canonical": r[1],
        "search_pattern": r[2] or "",
        # r[3] = exclude_pattern が欠落していた
        "priority": r[4],
        "match_type": r[5],
        "effect": r[6],
    }
    for r in rows
]
```

SQL では `SELECT status_id, canonical, search_pattern, exclude_pattern, priority, match_type, effect`（7列）を返しているにもかかわらず、dict に `exclude_pattern`（r[3]）が含まれていなかった。

## 不足している完売ワード

`backend/app/services/tcg_analyzer_svc.py:1102-1112`（resolve_status_v2 の EXCLUDE ループ）はマスタ駆動のため、以下のワードが DB に存在しない場合は判定されない:

| ワード | 起票根拠 |
|--------|----------|
| `sold` | C18 handoff |
| `売切` | C38 handoff |
| `SOLD OUT` | C38 handoff |
| `一旦ストップ` | C92 handoff |
| `〆` | C92 handoff |
| `ストップ` | C92 handoff |

## 除外パターン欠落

ST0012「売り切れ」: `exclude_pattern = ''` → 「売り切れの場合がございます」も誤判定
ST0013「完売」: `exclude_pattern = ''` → 「予告なく完売となる場合」も誤判定

## 変更ファイル一覧（file:line）

| ファイル | 変更 |
|---------|------|
| `migrations/20260921_000000_status_master_soldout_ssot.sql` | 新規作成: INSERT 6行 + UPDATE 2行 |
| `backend/app/services/tcg_analyzer_svc.py:1063-1072` | dict に `"exclude_pattern": r[3] or ""` 追加 |
| `backend/app/services/tcg_analyzer_svc.py:1111-1112` | EXCLUDE ループに exclude_pattern チェック追加 |
| `scripts/run_all_migrations.sh:720-722` | 新 migration のエントリ追加 |

## 触らない範囲

- `resolve_status_v2` の EXCLUDE ループのロジック（priority sort・memo_exact判定）は変更しない
- OUTPUT / DEFAULT エントリの処理は変更しない
- フロントエンドは変更なし
- 他の migration ファイルは変更なし
