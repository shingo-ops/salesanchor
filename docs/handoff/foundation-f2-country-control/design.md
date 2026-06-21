# Phase 3 設計 — Foundation F2 国の統制

**対象ADR**: PR-F2 / 国の統制
**recon**: `docs/handoff/foundation-f2-country-control/recon.md`
**日付**: 2026-06-21
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例: `public.countries` の共有マスタ（PR-F1）を消費側で利用する。
  応用: `LeadEditPage` / `LeadsPage` の country 入力を `GET /api/v1/countries` へ切り替え、保存は ISO alpha-2 に統制する。
- 事例: 既存の `parse_country_code()` 正規化ロジック。
  応用: lead 入力と backfill を同じ解決規則で揃え、入力値の揺れを吸収する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| リード入力画面で country がコンボボックスになる | Playwright E2E |
| 保存される country が ISO alpha-2 になる | backend pytest |
| 既存 lead.country が backfill で正規化される | backend pytest + migration 実行 |
| 変換不能値が NULL になり件数が報告される | backfill レポート確認 |
| `public.countries` の共有読み取りを壊さない | PG/RLS pytest |

---

## 技術 How・KPI

- KPI: リード country 入力の SSOT 化
- 技術選択: 共有国マスタ API を読み、保存前に `parse_country_code()` と `public.countries` で二段階検証する

---

## 弊害・トレードオフ

- FK をこの PR で強制すると backfill 前の既存汚れ値で migration が失敗しやすい
- そのためまずは保存時バリデーション + backfill を優先し、FK 強制は別途採否を判断する

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | CountryCombobox で `GET /api/v1/countries` を消費 | Generator |
| 2 | lead.country の保存時統制（alpha-2 + public.countries 照合） | Generator |
| 3 | 既存 lead.country の backfill 実行・レポート化 | Generator |
| 4 | backend pytest / Playwright / process-artifacts gate の確認 | Evaluator |

---

## 継続

- 完了後の監視: backfill レポートの unresolved 件数を確認
- 次フェーズへの引き継ぎ: 会社住所 / registration の country 統制は別PR

---

## 標準ワークフロー確認

- `docs/handoff/foundation-f2-country-control/recon.md`
- `docs/handoff/foundation-f2-country-control/design.md`

---

## GO記録

- 発行者: 未発行
- 日時: 未発行
- GO原文: 未発行
- バックアップ確認: 未発行
