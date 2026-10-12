# recon: ダッシュボード時刻表示JST修正

## 調査ブランチ
release/fix-dashboard-timestamps (cherry-pick from release/dashboard-tab-separation commit 10803b896)

## 変更対象ファイル
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` L758 — ImportTabContent: data.latest_import_at を生ISO文字列からJSTフォーマットに変更
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` L1114 — ExtractionTabContent: エラーテーブルの created_at に renderCell を追加（JST変換）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` L1740-1747 — DistributionTabContent: last_distributed_at を通常表示・staleバッジ両方でJSTフォーマット

## 削除するファイル
なし

## 関連ADR
- なし（UI表示の細部修正）

## 現状把握
AnalysisDashboardPanel.tsx 内で3箇所が生のISO文字列（例: `2026-09-25T11:28:09Z`）をそのまま表示していた。
他の日時表示はすでに toLocaleString("ja-JP", { timeZone: "Asia/Tokyo", ... }) でフォーマット済みだったが、この3箇所が漏れていた。
