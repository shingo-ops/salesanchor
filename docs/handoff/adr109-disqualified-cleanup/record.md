# ADR-109 'disqualified' 値の変換記録

## 事象

2026-08-31 デプロイ [124/193] で `migrate_adr109_status_codes.py` が終了コード 1 で中断。

```
[Pre-check] tenant_006: 想定外の status 値 'disqualified' を検出。
マッピングを定義せずに移行することはできません。
```

## 原因

`tenant_006.leads.status` に `'disqualified'` が存在していた。
`_ALL_KNOWN_VALS`（ADR-109 の7状態 ∪ STATUS_MAP の旧値10件 = 17件）に含まれない非標準値。

### いつ入ったか

特定の INSERT migration はなし。
2026-07-26 コミット `98ba6555` で `backend/app/routers/goals.py:427` に以下が追加された:

```sql
COUNT(*) FILTER (WHERE status NOT IN ('out_of_scope', 'disqualified')) AS total
```

このコードが `disqualified` を認識していたことから、deals廃止前の段階で
tenant_006 の実データに `disqualified` ステータスが存在していたと判断する。
（ADR-109 施行 2026-06-04 より前に入力されたデータとみられる。）

## 対処判断

**案A: STATUS_MAP に `("disqualified", "out_of_scope")` を追加して変換する。**

- ADR-109 は7状態のみを定義。`disqualified` は ADR 外の非標準値。
- `goals.py` は `out_of_scope` と `disqualified` を同じ除外フィルタ
  `NOT IN ('out_of_scope', 'disqualified')` で扱っている。
- 変換後は `out_of_scope` として集計されるため、KPI への影響はゼロ。
- バックアップ確認: deploy.yml による自動バックアップ済み。

**PO GO: 2026-08-31（Shingo）**

承認内容:
> migrate_adr109_status_codes.py の STATUS_MAP に ("disqualified", "out_of_scope") を追加し、
> 変換対象行をログに記録する。
> 根拠: ADR-109 は7状態のみを定義。disqualified は非標準値であり、
> goals.py で out_of_scope と同じ除外フィルタに含まれるため集計に影響しない。
> バックアップ確認: デプロイ前自動バックアップあり（deploy.yml）。

## 変換実績

変換対象テナント: tenant_006  
変換行数・IDは deploy ログの `[AUDIT]` 行を参照すること（PR マージ後の deploy.yml ログ）。

## goals.py との関係

- `goals.py:427` の `NOT IN ('out_of_scope', 'disqualified')` は変換完了後も機能する
  （`disqualified` は DB から消えるため、フィルタの該当行は0件になるが集計への影響なし）
- 将来 `goals.py` の `'disqualified'` 参照を除去する場合は別 PR で実施すること

## 関連ファイル

- `scripts/migrate_adr109_status_codes.py` — STATUS_MAP 追加・AUDIT ログ追加
- `backend/app/routers/goals.py:427` — `disqualified` を参照する集計フィルタ
- `docs/adr/ADR-109-leads-status-ssot-immutable-codes.md` — 7状態の定義元
