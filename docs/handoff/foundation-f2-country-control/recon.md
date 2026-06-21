# recon — Foundation F2 国の統制

**仕事名**: Foundation F2 国の統制
**日付**: 2026-06-21
**対象ADR**: PR-F2 / 国の統制
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/country_codes.py:16-70` | 国名 / alpha-2 を ISO 3166-1 alpha-2 へ寄せる共通ヘルパーが存在する |
| `backend/app/schemas/lead.py:116-135` | `LeadCreate.country` が追加され、入力時に `parse_country_code()` で正規化される |
| `backend/app/schemas/lead.py:170-195` | `LeadUpdate.country` も同様に正規化され、更新時に統制される |
| `backend/app/routers/leads.py:149-175` | `public.countries` に存在する alpha-2 のみを通す追加検証がある |
| `backend/app/routers/leads.py:379-417` | リード新規作成時に `country` を `public.countries` 検証後に保存している |
| `backend/app/routers/leads.py:482-483` | リード更新時も `country` を検証してから保存している |
| `frontend/src/components/CountryCombobox.tsx:38-54` | `GET /api/v1/countries` を取得して選択肢を組み立てている |
| `frontend/src/components/CountryCombobox.tsx:66-85` | 選択値は alpha-2 を保持し、表示は国名 + code にしている |
| `frontend/src/pages/leads/LeadEditPage.tsx:70-118` | フルページ編集で country を読み書きする |
| `frontend/src/pages/leads/LeadEditPage.tsx:205-211` | リード編集画面に国コンボボックスを差し込んでいる |
| `frontend/src/pages/leads/LeadFormFields.tsx:1-95` | Drawer 編集フォームにも country コンボボックスがある |
| `frontend/src/pages/leads/LeadsPage.tsx:67-90` | リスト作成 / 編集 state に country を追加している |
| `frontend/src/pages/leads/LeadsPage.tsx:163-207` | 新規作成 / Drawer 更新時に country を保存している |
| `frontend/src/pages/leads/LeadsPage.tsx:362-369` | リード作成モーダルに country コンボボックスを差し込んでいる |
| `scripts/migrate_20260621_020000_backfill_lead_country.py:42-99` | 既存 `lead.country` を ISO alpha-2 に backfill し、変換不能は NULL 化する |
| `scripts/migrate_20260621_020000_backfill_lead_country.py:123-167` | アクティブテナント全件を走査し、JSON レポートを出力する |
| `scripts/run_all_migrations.sh:411-415` | F1 countries master の後に F2 backfill migration を登録している |
| `backend/tests/test_lead_country_control.py:35-163` | SQLite で country 保存の正規化、PG/RLS で backfill と共有 master 可読性を検査する |
| `frontend/tests-e2e/lead-country-control.spec.ts:65-113` | country combobox が `/api/v1/countries` を読み、dark mode でも alpha-2 保存できることを確認する |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | FK での強制が必要か | まずは保存時バリデーション + backfill を優先し、移行後に採否を判定 | ✅ 解消済み |
| 2 | 既存 lead.country の汚れ値の件数 | backfill 実行時に JSON レポートへ出す | ✅ 解消済み |
| 3 | 会社住所 / registration 側を今回も統制対象に含めるか | 今回は含めない（lead のみ） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 標準ワークフロー確認

- `docs/handoff/foundation-f1-countries-master/recon.md`
- `docs/handoff/foundation-f1-countries-master/design.md`
- `docs/handoff/foundation-f2-country-control/recon.md`
- `docs/handoff/foundation-f2-country-control/design.md`

---

## GO記録

- 発行者: 未発行
- 日時: 未発行
- GO原文: 未発行
- バックアップ確認: 追加のみのため、backfill 前に別途 GO 後の実施を想定

---

## 補足

- 本PRは lead.country の統制と backfill を扱う。
- `frontend/src/constants/countries.ts` と `public.countries` の値は PR-F1 で一致済み。
