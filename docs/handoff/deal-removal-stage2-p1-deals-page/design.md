# design — deal-removal stage2-P1 deals page

**対象ADR**: ADR-121  
**recon**: docs/handoff/deal-removal-stage2-p1-deals-page/recon.md  
**日付**: 2026-07-21  
**担当**: Planner

---

## 0. 全体

`/deals` ページ（一覧・編集）とその導線を frontend から除去する。backend は変更しない。

---

## 1. 外部・過去事例の参照と我々への応用

- `deal-removal-track-a` は dashboard の可視参照外しを先に整理していた。今回も同様に、見える導線だけを外し、backend を巻き込まない。

---

## 2. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `/deals` 一覧・編集ページがフロントから消えている | `rg -n "DealsPage|DealEditPage|DealFormFields|pages/deals" frontend/src/` がテスト文字列 1 件を除き 0 |
| `/deals` 導線が残っていない | `rg -n '\"/deals\"|/deals/' frontend/src/` が 0 |
| frontend のビルドが通る | `npm run build` |
| shell の既存検証が壊れていない | Playwright desktop-shell.spec.ts / mobile-shell.spec.ts |

---

## 3. recon / ADR 相互参照

- recon: `docs/handoff/deal-removal-stage2-p1-deals-page/recon.md`
- ADR: `ADR-121`

---

## 4. 弊害対策

- `ManagementCenterPage` の `/deals` 導線だけを外し、`DesktopShell` の権限項目は触らない。
- ページ本体 3 ファイルは削除するが、`statusPresentation.test.ts` の文字列テストは残す。

## 5. 維持の仕組み

- 守り手: .github/workflows/process-artifacts-gate.yml
- 対象: recon/design の欠落、/deals 削除の宣言漏れ、実 diff との不整合
