# design — dist01-release-date（Release Date 列追加・発売日降順ソート）

参照: `docs/handoff/dist01-release-date/recon.md`

## KGI / 検証基準

| 基準 | 検証方法 |
|------|---------|
| スプレッドシートの11列目が "Release Date" ヘッダーで書き込まれる | `run_distribution` 後にシート1行目 K列を確認 |
| Release Date 列に日付文字列（例: `2025-08-01`）または空文字が書き込まれる | シート2行目以降の K列を目視確認 |
| 発売日が新しい順（NULLS LAST）で並ぶ | 先頭3行の Release Date を確認し降順になっていること |
| 提供者列（旧10列目）が12列目に移動している | シート L列が提供者名であること |

## 修正方針

`tcg_distribution_svc.py` を3箇所修正する（他ファイル・他関数への影響なし）。

```python
# 1. DIST_HEADERS: "Status" の後に "Release Date" を追加
DIST_HEADERS = [..., "Status", "Release Date", "提供者"]

# 2. SELECT: release_date カラムを追加
COALESCE(p.release_date::text, '') AS release_date,

# 3. ORDER BY: 発売日降順に変更
ORDER BY p.release_date DESC NULLS LAST, ts.name NULLS LAST, p.code NULLS LAST

# 4. 返却リスト: row["release_date"] を追加
[..., row["status"], row["release_date"], row["provider"]]
```

## 影響範囲

- 修正箇所: `backend/app/services/tcg_distribution_svc.py` の4箇所
- `DIST_HEADERS` の参照先: `_write_to_target_sync`（同ファイル内）のみ
- スプレッドシートの列数が10→11に変わるため、既存シートを上書きする場合は旧フォーマットとの並びに注意
- `fetch_preview_data` は別関数・別クエリのため影響なし

## 戻し方

`"Release Date"` 行を `DIST_HEADERS` から削除し、SELECT と ORDER BY と返却リストを元に戻す（4箇所）。

## 維持の仕組み

- `DIST_HEADERS` 定数と `fetch_output_rows` の SELECT/返却リストを常に同数・同順で管理する
- 列追加時は `DIST_HEADERS`・SELECT・返却リストの3点セットを同時に変更する（ADR-154 §出力形式）
- `p.release_date` は `tcg_products` テーブルの列。商材マスタ更新で自動反映される
