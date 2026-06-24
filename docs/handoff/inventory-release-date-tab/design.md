# Phase 3 設計 — inventory-release-date-tab

**対象ADR**: ADR-093
**recon**: docs/handoff/inventory-release-date-tab/recon.md
**仕事名**: inventory-release-date-tab（/inventory に発売日順ソート＋tcg_typeタブを追加）
**変更種別**: API小改修＋フロント改修のみ（migrations/・deploy.yml・本番scripts 不変＝危険変更なし）
**日付**: 2026-06-24

---

## 1. KGI / KPI（受入基準）

KGI: /inventory が tcg_typeタブ（初期=ポケモンカード）で切替でき、既定で発売日の新しい順に並ぶ。

| KPI | 基準（○×・POが画面で判定） | 判定方法 |
|---|---|---|
| 1 | タブが表示され初期表示が「ポケモンカード」 | 画面目視 |
| 2 | タブ切替でその種別の行に絞り込まれる | 画面目視 |
| 3 | 「発売日」列が表示されソート対象になっている | 画面目視 |
| 4 | 既定の並びが発売日 新しい順（最新が上・NULL末尾） | 画面目視 |
| 5 | 既存の列ソート・絞り込み・仕入元表示が従来どおり | 画面目視 |
| 6 | 差分に migrations/・run_all_migrations.sh・deploy.yml が出ない | gh pr diff --name-only |

補足: 同一発売日の行は副キー `i.id ASC`（recon: inventory_offers.py L296）で安定。☆順の上書きは別テーマ。

## 2. 設計（recon の各 file:line に対応）

バックエンド inventory_offers.py:
- `_VIEW_SELECT`（recon L96-107）末尾に `p.release_date AS release_date` を追加。
- `_SORT_COLUMNS`（recon L121-133）に `"release_date": "p.release_date"` を追加。
- sort Query（recon L192）の pattern に `release_date` を追加し、default を `release_date` に変更。
- ORDER BY（recon L296）は NULLS LAST 既存のため変更なし。

フロント InventoryPage.tsx:
- `InventoryRow`（recon L18-35）に `release_date: string | null` を追加。
- sortField 初期（recon L90）`"name"→"release_date"`、sortDir 初期（recon L91）`"asc"→"desc"`。
- activeTab state 新設（初期 `"pokemon_booster_box"`）。params に `tcg_type=activeTab`（all時は未送信）を追加。load 依存に activeTab を追加。
- タブUI（先頭「すべて」＋ tcgTypes をマスタ順）を表上部に描画。
- sortTh に「発売日」列追加、ボディに `<td>{it.release_date ?? "-"}</td>` 追加。i18n（ja/en）にラベル追加。

触らない範囲: migrations/・run_all_migrations.sh・deploy.yml／tcg_type WHERE（recon L216-218）／GET /products/tcg-types。

## 3. 検収結果（実出荷）

| 項目 | 基準 | 結果 |
|---|---|---|
| 差分純度 | 4ファイル・migrations/deploy.yml なし | ○（inventory_offers.py / InventoryPage.tsx / ja.json / en.json）|
| 実装差分 | KPI1-4 の実装行が差分に存在 | ○（release_date / activeTab / pokemon_booster_box / sortField / releaseDate を確認）|
| 既存CI | pytest（SQLite+PG RLS）緑 | ○（0 failed）|
| 発売日順の自動テスト | sort=release_date 降順・NULL末尾を検証 | 未投入（共有テストDBのスキーマ土台問題により本PRから除外。土台整備後に別途）|
| KPI1-5 画面確認 | 初期=ポケモン／既定=発売日新しい順／既存機能健在 | マージ後にPO目視で確認 |

## 4. 外部・過去事例

- 過去事例（社内）: ADR-093 が /inventory を全オファー明細ビューとして確定。本改修はその上に「既定並び」と「種別タブ」を足すもので、ビューの責務は不変。
- 外部事例（一般UI）: 在庫・物販一覧では「新着（発売日）降順を既定」「カテゴリ/種別タブで切替」は標準構成。回転の速いTCG新弾を上位に出す運用に合致。
- 残課題（バックログ）: (1) 共有テストDB土台の整備＋発売日順自動テスト再投入、(2) ☆優先提供者（Yの仕上げ・定義→migration→実装の別テーマ）。
