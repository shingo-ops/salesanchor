# design — extraction-ranking

**仕事名**: extraction-ranking
**日付**: 2026-09-25
**対象ADR**: ADR-138 / ADR-027 / ADR-144

---

## 目的

抽出タブに提供者・商品のワーストランキング（トップ3 + 詳細展開）を追加する。
提供者別抽出成功率の低い上位3件と、商品別照合率の低い上位3件を可視化し、
オペレーターが改善優先度を判断できるようにする。

---

## 対象・対象外

### 対象
- backend: `GET /extraction-product-ranking` 1エンドポイント追加
- frontend: `AnalysisDashboardPanel.tsx` 抽出タブへのランキングセクション追加
- frontend: `AnalysisDashboardPanel.css` ランキングカードCSS追加
- i18n: `ja.json` / `en.json` 各15キー追加

### 対象外
- 他タブ（import / analysis / distribution）の変更
- DBスキーマ変更・新テーブル作成
- 既存エンドポイントの変更

---

## 変更前後

| 区分 | 変更前 | 変更後 |
|------|--------|--------|
| 抽出タブ構成 | KPIカード + 提供者テーブル + トレンドグラフ + エラーテーブル | 上記 + ワースト提供者トップ3 + ワースト商品トップ3 |
| 商品別照合率API | 存在しない | `GET /extraction-product-ranking?days=N` 追加 |
| i18nキー数（抽出タブ） | 既存のみ | +15キー（ja/en両方） |

---

## 関連ADR

- **ADR-138**: 分析ダッシュボード全体設計 — 抽出タブはここで定義された構造に従う
- **ADR-027**: UI i18n強制 — 全UI文字列は `t("key")` 経由。ja/en同一キー必須
- **ADR-144**: UIガバナンス — Card / Badge / DataTable 金型使用。色直値・生input禁止

---

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 抽出タブにワースト提供者トップ3が表示される | ブラウザで抽出タブを開き、ランキングカードが3件表示されることを確認 |
| 抽出タブにワースト商品トップ3が表示される | 同上、商品ランキングセクション |
| 「詳しく見る」で全件テーブルが展開される | ボタンクリックでDataTableが表示されることを確認 |
| i18nキーがja/en両方に存在 | CI lint通過 |
| デザイントークンのみ使用 | CI UI governance gate通過 |
| 新APIが正しいデータを返す | `/extraction-product-ranking?days=30` のレスポンス確認 |

---

## 外部事例

該当なし（既存 `FunnelReasonsPage.tsx` の `frr-rank` パターンを踏襲。
`frontend/src/pages/dashboard/FunnelReasonsPage.tsx:72` / `FunnelReasonsPage.css:86`）

---

## 守り手

- i18n lint（CI）: ja/en 両方にキーが存在しないとブロック
- UI governance gate（CI）: 色直値・生input・非金型コンポーネント使用でブロック
- process-artifacts gate（CI）: 触るファイルが PR 本文に全列挙されていないとブロック

---

## recon参照

`docs/handoff/extraction-ranking/recon.md` — 不明点ゼロ確認済み（全5件解消）
