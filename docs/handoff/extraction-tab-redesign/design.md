# Design: 抽出タブ 3段構成リデザイン

**対象ADR**: ADR-027（i18n強制）・ADR-067（デザイントークン強制）・ADR-144（UIガバナンス）
**recon**: docs/handoff/extraction-tab-redesign/recon.md
**日付**: 2026-09-28
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：今回は同リポジトリ内のインポートタブ（ImportTabContent）の3段構成パターンを踏襲する内部リデザインのため、外部事例の参照は不要と判断

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 正常性カード・推移グラフ・総数テーブルの3段が表示される | ブラウザで抽出タブを開き目視確認 |
| インポートタブに影響がない | ブラウザでインポートタブを開き目視確認 |
| ハードコード日本語ゼロ | `grep -n "[\u3040-\u9fff]" frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` で変更行に一致なし |
| 色直値ゼロ | `grep -n "#[0-9a-fA-F]" frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` で変更行に一致なし |
| TypeScript型エラーなし | tsc --noEmit PASS |
| i18n完全（ADR-027） | check-i18n-missing-keys.js PASS |

---

## 設計方針

抽出タブを9要素混在から3段構成（正常性カード→推移グラフ→総数テーブル）にリデザインする。
バックエンドAPIは変更しない（SSOT遵守）。インポートタブと同じレイアウトパターンに統一する。

## 変更範囲

| 層 | 変更 |
|---|---|
| frontend component | ExtractionTabContent を3段構成に全面書き換え（858行→93行） |
| frontend style | 未使用ランキングCSS 13件削除 |
| i18n ja | 抽出タブ用キー10件追加 |
| i18n en | 同上（英語） |
| backend | 変更なし |

## 新しい3段構成

| 段 | 内容 | 金型 |
|---|---|---|
| 1. 正常性カード | 総数・成功率・エラー件数（信号灯） | Card metric + Badge |
| 2. 推移グラフ | 成功率・エラー率の日別推移 | recharts LineChart |
| 3. 総数テーブル | 日別の抽出総数・成功・エラー | DataTable compact |

---

## 維持の仕組み

守り手: check-i18n-missing-keys.js（i18n完全性）・tsc --noEmit（TypeScript型安全）・UI governance gate（ADR-144 金型遵守）
