# design.md — 取引額の SSOT 化（v_company_stats 一本化）／ Generator 実装指示

- 対応recon: `docs/handoff/company-stats-ssot/recon.md`（2026-06-12）
- PO決定（2026-06-12）: 「取引額累計」の公式定義 ＝ **入金済み・取消なしの請求書合計**
  （`paid_at IS NOT NULL AND voided_at IS NULL`。ADR-108 の定義を全アプリの正とする）

## ゴール
顧客ごとの取引額系の数値が、全画面で同一の計算式（公式定義）・同一の出所（v_company_stats）になる。

## 実装内容

### 1. v_company_stats の定義修正（migration）
- 新 migration で view を再作成（CREATE OR REPLACE）。
  集計フィルタを `status != 'cancelled'` から
  `paid_at IS NOT NULL AND voided_at IS NULL` へ変更
  （migrations/20260604_100000_create_company_stats_view.sql:48 の後継）。
- view の他のカラム（会話数・最終会話等）の定義は変えない（取引額系フィルタのみ）。
- テナント分離（RLS/スキーマ）の挙動が現行と同一であることを確認。

### 2. カルテの計算をAPI経由に置換
- InboxKartePanel.tsx:558-575 のクライアント側全件フェッチ＋手元集計を撤去し、
  修正後の v_company_stats 由来の値を API で受け取って表示する。
- API の載せ方（既存カルテ用レスポンスへの追加 or companies 系の流用）は
  既存のAPIパターンに従って Generator 判断。新規の独自集計SQLは書かない（必ず view 経由）。
- 「取引実績なし」表示（合計ゼロ・該当なし時）の挙動は現行どおり維持（ADR-108）。

### 3. テスト新設（現状ゼロ）
- バックエンドに v_company_stats の集計テストを追加。最低限のケース:
  paid（数える）／未払い issued（数えない）／voided（数えない）／cancelled（数えない）／
  複数請求書の合算／請求書ゼロ件（取引実績なし）／他テナント不可視。
- カルテ表示のE2E（既存 karte-gate）が API モックで通ること。

### 4. 視覚ゲートとの整合（注意）
- カルテの実績サマリーは値の「出所」が変わるだけで見た目は不変が原則。
- renderKarte() の API モックに stats 相当の追加が必要なら更新する。
- 視覚回帰（toHaveScreenshot）が差分を出した場合、レイアウト不変なら
  モックデータ起因。見た目を変えないこと（ベースライン更新はShingo承認後のみ）。

### 5. ADR 起案（What/Why の記録）
- 小さなADRを新規作成: 「取引額集計の SSOT ＝ v_company_stats（公式定義: 入金済み・取消なし）」。
  Why: 画面間の金額不一致の解消・定義変更を1か所に。関連: ADR-108 / ADR-120 / ADR-109。
  番号は docs/adr/ の次の空きを確認して採番。

## Scope外（混ぜない）
- analytics / goals の「売上」（orders ベース）は**別概念（受注ベース）として現状維持**。
  ただし画面上の呼称が「取引額累計」と紛らわしくないかは報告に一言添える（修正は別タスク）。
- 通貨換算・期間集計の高度化は対象外。

## 表示値の変化（想定内・周知事項)
- 会社詳細ページの取引額は、未入金・取消分が除外されるため**小さく（正しく）なる**。
  これは修正であってバグではない。before/after の例を1テナント分、報告に含める。

## 危険カテゴリの扱い（必須）
- migration（view 再作成）を含む＝危険カテゴリ。
- develop マージは CI 緑で可。**本番適用（main→デプロイ）は Shingo の明示 GO 後**。
  素振り（本番相当環境で before/after の数値比較）を報告し GO を依頼すること。

## 外部・過去事例の参照と我々への応用

- 事例1: Django/Rails 系プロジェクトでの「集計ロジック散在」→「ビュー/スコープ一本化」  
  → 我々への応用: v_company_stats を唯一の集計 SSOT とし、フロント側集計を廃止する
- 事例2: ADR-108 でのカルテ再設計（paid_at IS NOT NULL AND voided_at IS NULL を公式定義化）  
  → 我々への応用: ビュー定義をこの ADR に揃える（ADR-136 として記録）

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| v_company_stats フィルタが `paid_at IS NOT NULL AND voided_at IS NULL` に変更されている | DB で `pg_get_viewdef` 確認 |
| カルテのクライアント側全件フェッチ集計が撤去されている | `InboxKartePanel.tsx` に `/invoices?lead_id=` が残っていないこと |
| バックエンドに v_company_stats 集計テストが 8 シナリオ以上ある | `pytest backend/tests/test_company_stats.py` 全 PASS |
| カルテの見た目が不変（視覚ゲート緑） | karte-visual-gate Playwright テスト PASS |
| ADR-136 が作成済みで README 索引に反映されている | `docs/adr/ADR-136-company-stats-ssot.md` 存在確認 |

## 実装 ADR

- ADR-136: `docs/adr/ADR-136-company-stats-ssot.md`（本 PR で新規作成）
- 参照: `docs/handoff/company-stats-ssot/recon.md`、PR #2020
