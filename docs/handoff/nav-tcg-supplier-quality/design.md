# design — nav-tcg-supplier-quality（SaaS管理者メニュー削減）

**対象ADR**: ADR-154, ADR-144  
**recon**: docs/handoff/nav-tcg-supplier-quality/recon.md  
**日付**: 2026-09-04  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回はサイドメニューの項目削減とデッドページ削除のみ。UI コンポーネント新設・API 追加なし。外部事例の参照は不要と判断。ADR-154（GAS→Python 段階移植方針）の清掃フェーズとして、不要ページを除去する定石操作。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| SaaS管理者メニューが2項目（解析精度管理・為替レート管理）のみ表示される | Evaluator（Playwright: サイドバー要素数確認） |
| 削除4ページへのルートが App.tsx に存在しない | `grep -n "super-admin/masters\|super-admin/inbound\|super-admin/phase-switch\|super-admin/inventory-offers" frontend/src/App.tsx` → 0件 |
| `tsc && vite build` が 0 エラーで完了する | CI `frontend-build` ジョブ green |
| 削除キーが ja.json / en.json に残存しない | `grep -n "superAdminMasters\|superAdminInbound\|superAdminPhaseSwitch\|superAdminInventoryOffers" frontend/src/locales/*.json` → 0件 |
| ParseReviewPage ルート（`/super-admin/inbound/:id/review`）が保持されている | `grep -n "inbound/:id/review" frontend/src/App.tsx` → 1件 |

---

## 技術 How・KPI

- KPI: `tsc` エラー 0 件 / ビルド成功 / process-artifacts gate green
- `DesktopShell.tsx`: `saasAdminItems` を5項目→2項目に変更（ADR-144 UIガバナンス準拠・既存 `NavItem` 型を使用）
- `App.tsx`: 4ページの import・standalone route・nested route を削除。ParseReviewPage は保持
- 翻訳ファイル: 削除4キーを除去。`superAdminTcgSupplierQuality` 表示名を「解析精度管理」に更新
- `routeTitles.ts`: 削除ルート3件を除去（`/super-admin/masters` 他）
- backend は一切変更しない（`super_admin_phase_switch.py` は ParseReviewPage が使用中のため残置）

---

## 弊害・トレードオフ

- 削除ページへの直接URLアクセスは 404 になる。影響範囲: super_admin ユーザーのみ。メニューから辿れなくなるため実害は軽微
- ParseReviewPage が phase-switch バックエンドAPIを参照しているため backend は削除不可。将来 ParseReviewPage を削除する際に backend も一緒に削除すること

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `DesktopShell.tsx` saasAdminItems を2項目に変更 | Generator |
| 2 | `App.tsx` 4ページの import・route を削除（ParseReviewPage 保持） | Generator |
| 3 | `locales/ja.json` / `en.json` 削除4キー除去・表示名更新 | Generator |
| 4 | `routeTitles.ts` 削除ルート除去 | Generator |
| 5 | `LLMBudgetTab.tsx` 削除済みページへのコメント参照を除去 | Generator |
| 6 | `tsc && vite build` で 0 エラー確認 | Generator |

---

## 継続

- 完了後の監視: ビルドが削除ファイルの import を検知する（tsc エラー）。追加の監視設定不要
- 次フェーズへの引き継ぎ: ParseReviewPage を削除する際は backend/app/routers/super_admin_phase_switch.py も一緒に削除すること

---

## 維持の仕組み

守り手: 人手で守る — ビルド（`tsc`）が削除ファイルへの import を検出する。`saasAdminItems` の項目数をテストで強制する仕組みは存在しないため、PRレビュー時に目視確認する。ADR-154 の清掃フェーズ完了後はこの仕組みの保守は不要。
