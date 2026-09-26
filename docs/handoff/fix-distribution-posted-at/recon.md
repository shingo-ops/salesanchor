# recon: fix-distribution-posted-at

## 調査日時
2026-09-24

## 問題
配信クエリが `sm.received_at`（最古メッセージ日付）を `posted_at` として出力している。Android版データでは `received_at` にプロバイダグループ内の最古メッセージ timestamp が設定されるため、投稿日時が古く表示される。

## 対象ファイル

- `backend/app/services/tcg_distribution_svc.py:215` — SELECT文で `sm.received_at` を `posted_at` にエイリアス

## 全 received_at 使用箇所の洗い出し

```
grep -n "received_at" backend/app/services/tcg_distribution_svc.py
```

結果: 1箇所のみ（行215）

```
grep -rn "received_at" backend/app/services/ --include="*.py"
grep -rn "received_at" backend/app/routers/ --include="*.py"
```

- `backend/app/services/tcg_distribution_svc.py:215` — 配信出力の SELECT（今回の変更対象）
- `backend/app/services/tcg_analysis_dashboard_svc.py:378` — ダッシュボード用 MAX(sm.received_at)（変更対象外）
- `backend/app/services/tcg_line_import_svc.py:306` — インポート時の received_at 書き込み（変更対象外・触らない）
- `backend/app/services/tcg_import_progress.py:160` — インポート進捗確認クエリ（変更対象外）
- `backend/app/services/tcg_supplier_quality_svc.py:84` — 仕入元品質クエリの ORDER BY（変更対象外）
- 各ルーター — purchase_orders / parse_review / super_admin_inbound 等（変更対象外）

## DB カラム確認

`source_messages` テーブル:
- `received_at TIMESTAMPTZ` — プロバイダグループ内の最古メッセージ timestamp（Android では古くなる）
- `line_posted_at TIMESTAMPTZ` — 実際の LINE メッセージ投稿日時（ADR-134参照）

`line_posted_at` は `pmg-import-delivery-ssot` で追加済みカラムであり、`backend/app/services/tcg_line_import_svc.py:436` の INSERT文で既に書き込まれている。

## 関連ADR

- ADR-134-design-site-delivery.md — 配信機能の設計
- docs/handoff/pmg-import-delivery-ssot/design.md — line_posted_at カラム追加の設計
- docs/handoff/db-ssot-sheet-recon/sheet-design.md:182 — received_at と line_posted_at の差異の実証記録
