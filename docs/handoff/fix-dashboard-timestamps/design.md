# design: ダッシュボード時刻表示JST修正

## 問題
AnalysisDashboardPanelの3タブで時刻がUTCの生ISO文字列で表示されていた。

| 箇所 | 修正前 | 修正後 |
|------|--------|--------|
| ImportTab `latest_import_at` | `2026-09-25T11:28:09.000Z` | `2026年9月25日 20:28` |
| ExtractionTab `created_at`（エラー表） | `2026-09-25T11:28:09.000Z` | `2026年9月25日 20:28` |
| DistributionTab `last_distributed_at`（通常＋staleバッジ） | `2026-09-25T11:28:09.000Z` | `2026年9月25日 20:28` |

## 対応方針
`toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })` で統一フォーマット。値が null/undefined の場合は "-" を返す。

## KGI/KPI
- KGI: 3箇所全てで日本時間フォーマット（YYYY年M月D日 HH:mm）が表示される
- KPI: null値は "-" で表示され、エラーが出ない

| 基準 | 検証方法 |
|------|----------|
| 生ISO文字列が表示されない | ブラウザでダッシュボード各タブを開いて確認 |
| JST時刻が正しく表示される | UTC時刻と9時間差であることを目視確認 |
| null値は "-" と表示 | APIがnullを返すケースでの表示を確認 |

## 影響範囲
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` 1ファイルのみ
- 変更は6行（+6/-6）の純粋な表示フォーマット変更
- データ取得ロジック・APIレスポンス・バックエンドへの影響なし

## 外部・過去事例の参照と我々への応用

`toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })` はブラウザ標準API（Intl.DateTimeFormat）。依存ライブラリ不要。
MDN Web Docs に仕様記載あり。他タブ（CompanyTabContent 等）でも同パターンを使用済みであり、プロジェクト内に先行実装あり。

## 戻し方
`git revert 10803b896` で即時ロールバック可能。

## 維持の仕組み

守り手: なし（表示のみの変更・自動テストなし）
将来的に AnalysisDashboardPanel のテストを追加する際、時刻フォーマットのアサーションを含めることを推奨。
