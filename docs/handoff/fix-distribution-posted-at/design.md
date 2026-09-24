# design: fix-distribution-posted-at

## 対象ADR
ADR-134-design-site-delivery.md

## 関連recon
docs/handoff/fix-distribution-posted-at/recon.md

## 問題と方針

### 現状
`tcg_distribution_svc.py:215` の SELECT文:
```sql
COALESCE(TO_CHAR(sm.received_at AT TIME ZONE 'Asia/Tokyo', 'YYYY-MM-DD HH24:MI:SS'), '') AS posted_at
```

### 原因
Android 版データのインポートでは `received_at` にプロバイダグループ内の最古メッセージ timestamp が設定される（`tcg_line_import_svc.py:306`）。これは SQR-05 で文書化された挙動。

### 修正
```sql
COALESCE(TO_CHAR(sm.line_posted_at AT TIME ZONE 'Asia/Tokyo', 'YYYY-MM-DD HH24:MI:SS'), '') AS posted_at
```

`line_posted_at` は実際の LINE メッセージ投稿日時を保持する（`pmg-import-delivery-ssot` で追加済み）。

## 変更箇所

| ファイル | 行 | 変更前 | 変更後 |
|---------|---|-------|-------|
| `backend/app/services/tcg_distribution_svc.py` | 215 | `sm.received_at` | `sm.line_posted_at` |

## 影響範囲

- 変更対象: 配信出力の `posted_at` フィールド（スプレッドシート書き込み・プレビュー API 双方）
- 変更しない: `received_at` カラム自体・import 側の書き込み処理・他サービス

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| Android 版データの配信 `posted_at` が正しい LINE 投稿日時を表示する | 配信プレビューで Android 取込データの `posted_at` が `line_posted_at` の値と一致することを目視確認 |
| iOS 版データの `posted_at` は変化しない | iOS 取込データで `received_at` ≒ `line_posted_at` のため影響なし（実証: db-ssot-sheet-recon/sheet-design.md:182） |

## 外部・過去事例の参照と我々への応用

- docs/handoff/db-ssot-sheet-recon/sheet-design.md:182 に「9時/10時の架空2投稿で既存 build_provider_entries を単独実行し、本文 new・received_at=9時・line_posted_at=10時を3/3確認」の実証記録あり。今回の修正はこの実証に基づく。
- Android と iOS で timestamp の設定方法が異なる問題は SQR-05 として既知の挙動。`line_posted_at` はその差異を吸収するために追加されたカラム。

## 維持の仕組み

- 守り手: tcg_distribution_svc.py の配信クエリをレビューする際、`posted_at` の元カラムが `line_posted_at` であることを確認する
- `received_at` カラムは削除しないため、将来必要があれば元に戻せる（ロールバック: 行215を `sm.received_at` に戻す）
