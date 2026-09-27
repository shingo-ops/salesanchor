# design: エラーログAPIパス二重prefix修正

## 修正内容

| 対象 | 修正前 | 修正後 |
|------|--------|--------|
| `tcg_analysis_dashboard.py:358` | `"/api/v1/tcg/extraction-errors"` | `"/tcg/extraction-errors"` |
| `ExtractionErrorLogPanel.tsx:50` | `api.get("/api/v1/tcg/extraction-errors?...")` | `api.get("/tcg/extraction-errors?...")` |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| CI全緑 | GitHub Actions で確認 |
| APIが404でなく401を返す | `curl -s -o /dev/null -w "%{http_code}" https://api.salesanchor.jp/api/v1/tcg/extraction-errors` → `401` |

## 影響範囲

呼び出し元: `ExtractionErrorLogPanel.tsx` のみ（grep確認済み）

## 外部事例

ルーターprefixとエンドポイントパスの二重定義はFastAPIの一般的なバグパターン。
修正パターン: エンドポイント側からプレフィックスを除去。

## 守り手

本修正後、同パターンの再発を防ぐには `include_router` 時の prefix と
エンドポイント定義を合わせてレビューすること。

## 戻し方

`"/tcg/extraction-errors"` → `"/api/v1/tcg/extraction-errors"` に戻す。
フロント側も同様に戻す。
