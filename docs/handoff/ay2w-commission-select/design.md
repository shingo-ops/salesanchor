# AY-2w 設計: 報酬パネルの担当者選択を金型 SelectControl へ移す

- 状態: 設計審査済み（Fable r1 REVISE → r2 APPROVE、LOW-A〜C 反映済み）・PO 承認済み（2026-10-14「y」）・PO 承認済み（方向）。実装は release/ay2w-commission-select
- PO 決定: 2026-10-14「y」（CommissionPanel の select を、表の見た目統一と切り離して先に共通部品へ移す。表はいまの見た目のまま）
- 基準: f353bb437（origin/main、WT /Users/tanizawashingo/worktrees/salesanchor/release-ay2w-commission-select）
- 調査根拠: docs/handoff/ay2w-commission-select/recon.md（生出力 /tmp/CC報告ファイル/ssot-ay2w/recon/）
- 対象 ADR: ADR-144（UI 部品ガバナンス・金型）、ADR-067（デザイントークン）、ADR-027（i18n）
- 前例: §AW-2b（docs/specs/design-system/design.md:2156-2180、生 select 53件を SelectControl children モードへ逐語移管）

## 1. 目的
frontend/src/components/CommissionPanel.tsx:209-225 の生 `<select>`（className なし・ブラウザ既定の見た目）を、金型 `SelectControl`（frontend/src/components/Select.tsx）へ移す。ADR-144 の「生 select 禁止」に合わせ、残る保留 1 件（docs/specs/design-system/design.md:2056）を解消する。表（data-table・列幅・横スクロール）は触らない。

## 2. 変更契約（製品コード）
対象は frontend/src/components/CommissionPanel.tsx の1ファイルのみ（試験は §5 の1ファイル）。

変更前（:209, :225）:
```tsx
                        <select
                          aria-label={`${label}${t("commission.assignedStaff")}`}
                          ...（:210-224 は不変）
                        </select>
```
変更後:
```tsx
                        <SelectControl
                          size="sm"
                          aria-label={`${label}${t("commission.assignedStaff")}`}
                          ...（:210-224 は逐語で不変）
                        </SelectControl>
```
- children モードを使う（空の選択肢 `value=""` =「未割当」を onChange で null として扱う現行動作を変えないため。options モードの placeholder は使わない）。
- `size="sm"`: 同じ行の解除ボタンが `<Button size="sm">`（:232）であり、表内の高さをそろえる。`fullWidth` は付けない（列幅・表の横幅に影響させない）。`appearance` は既定（bare）。
- import を1行追加: frontend/src/components/CommissionPanel.tsx:20 の直後に `import { SelectControl } from "./Select";`（手本 frontend/src/components/CompanyContactSelector.tsx:31 と同じ書き方）。
- 触らない: aria-label・data-testid・value・disabled・onChange・option 群・staffOptions・表・th の inline 幅・Button・i18n キー・CSS ファイル。新規トークン・新規 CSS・ui-allow コメントは追加しない。

## 3. 見た目の変化（意図した変化）
ブラウザ既定 → 金型 sm（frontend/src/components/FormField.css:75-92 の bare 規則と :137-147 の sm 規則。矢印 SVG・padding・font-sm・min-height var(--comp-input-height-sm)、disabled は :104-112）。これは他の 117 利用と同じ見た目にそろえる意図した変化。
- 767px 以下では frontend/src/components/FormField.css:443-449 の `@media (max-width:767px)` により `.comp-select__control` の min-height が `--comp-input-height-mobile`（44px、frontend/src/tokens.css:482）になる。390px で select が解除ボタン（Button sm）より高くなるのは金型の既定どおりの**意図した変化**であり、停止条件ではない（B1 は横 overflow のみ、B2 は型と DOM 属性のみを判定する）。
- 1280px では sm 規則（FormField.css:137-147）で行内ボタンと高さがおおむねそろう。実測値を PR の表に載せる。

## 4. 想定分岐（実装者は実物で確認し、記録して判断を仰ぐ）
- B1 横 overflow（Fable r1 の見立てでは停止が起こり得る。停止したら PO に1件で聞く）: 390px 幅・英語で、表を含む画面の横 overflow（document scrollWidth − clientWidth、および commission-table の scrollWidth）を変更前後で実測する。変更後が変更前より 1px でも大きければ、CSS で直さずに NEEDS_DECISION で停止（PO は「表はいまの見た目のまま」とした。表の修正は表統一便の範囲）。
- B2 SelectControl に渡した `size` が型エラーになる、または children モードで value/onChange/disabled/aria-label/data-testid が select 要素に届かない（DOM で確認）場合は停止。
- B3 frontend/scripts・check:all・ui-governance・design-token ratchet のいずれかが fail したら停止（迂回しない）。
- B4 既存の CommissionPanel 関連試験（frontend/src/components/SharedButtonMigration.test.tsx:90-108）が落ちたら停止。

## 5. 試験
frontend/src/components/SharedButtonMigration.test.tsx に CommissionPanel の試験を1件追加する（既存 :90-108 の render と通信 mock の型に合わせる。型設定・既存の期待は緩めない）。既存 fixture は全役割 staff_id=2（:22）、担当者は user_id=2 の1名のみ（:42）、mock.post の既定は throw（:48）なので、**新しい試験の中だけで**次を上書きする（既存試験の fixture は変えない）:
  - /staff の応答を user_id 2 と 3 の2名にする
  - mock.post を、呼ばれた URL と body を記録して解決する deferred 実装にする
- `commission-staff-<任意の役割>` が combobox で、class に `comp-select__control` と `comp-select__control--sm` を持つ。
- その select で空の選択肢（未割当）以外の担当者を選ぶと、既存の割り当て処理（handleAssign が呼ぶ API）が該当 staff_id で呼ばれる。空の選択肢を選ぶと null で呼ばれる（現行の onChange の挙動の固定）。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| 製品差分は CommissionPanel.tsx のタグ名2か所・`size="sm"`・import 1行のみ | `git diff origin/main...HEAD -- frontend/src/components/CommissionPanel.tsx` の全行を列挙して照合 |
| 生 select が CommissionPanel.tsx に 0 件 | `git grep -n "<select" -- frontend/src/components/CommissionPanel.tsx` が 0 件 |
| DOM の属性・選択肢が不変 | 変更前後で select 要素の aria-label・data-testid・value・disabled・option（value と文字列）を実測し差分 0（ja/en） |
| 意図した見た目の変化を提示 | 1280px と 390px、ja/en、ライト/ダーク で select の computed style（width・height・padding・font-size・background-image・border）を変更前後で実測し PR に表で記載 |
| 表の横 overflow が増えない（B1） | 390px・英語で document と commission-table の scrollWidth/clientWidth を変更前後で実測。後 ≤ 前 |
| 試験 | §5 の追加試験と既存試験が通る |
| 新規トークン・直書き 0 | check:all、check:new-tokens、design-token ratchet、ui-governance |
| 品質 | tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、PR の必須 CI |
| 本番 | 反映後の本番 JS に `commission-staff-` を含むチャンクで comp-select__control が使われている（grep）、app と API health が 200 |

### 実測の手順（B1・DOM 属性・computed style 共通）
既存の E2E 基盤を使う。新しい仕組みは作らない。
1. 基盤: frontend/playwright.config.ts（webServer が `npm run dev` を起動、:81-98）、認証回避 frontend/tests-e2e/utils/auth.ts の `installAuthBypass(page)`、通信 mock frontend/tests-e2e/utils/api-mock.ts の `mockApi(page, mocks)`（`/api/v1/.*` を route、:55,:123）。手本は frontend/tests-e2e/orders-list.spec.ts と frontend/tests-e2e/utils/common-mocks.ts。
2. 測定用 spec は一時ファイルとして frontend/tests-e2e/ay2w-measure.spec.ts に置いて実行し、**コミットしない**（実行後 mv で /tmp/CC報告ファイル/ssot-ay2w/impl/ へ退避し、git status が空であることを確認）。
3. 画面の開き方: route `/commissions`（frontend/src/App.tsx:240 → frontend/src/pages/commissions/CommissionsPage.tsx）。mock する API（実物の呼び出し元）:
   - GET /me/permissions（frontend/src/hooks/usePermissions.ts:25）: `orders.update` を含める（CommissionsPage.tsx:60 の条件）。common-mocks.ts:13-39 の `ALL_PERMISSIONS` には無いので `"GET /me/permissions": { permissions: [...ALL_PERMISSIONS, "orders.update"] }` の形で上書きする
   - GET /commissions/monthly（CommissionsPage.tsx:77-78,:97-98）: 空でよい正常応答（未定義だと api-mock.ts が 404 で fail-fast し error 表示が出る）
   - GET /financials/orders（CommissionsPage.tsx:120-122）: items 1 件以上
   - GET /orders/{id}/commissions（CommissionPanel.tsx:89-92）: 役割のうち少なくとも1つに staff_id あり、1つは null
   - GET /staff?per_page=100（CommissionPanel.tsx:89-92）: user_id を持つ担当者 2 名以上、うち1名は英語で長い姓名（例 20 文字以上）
   - そのほか画面の描画で呼ばれる API は common-mocks.ts の既定を使う。足りない API があれば実物の呼び出し元 file:line を記録して mock に加える。
   - 操作: `commissions-assign-<order_id>`（CommissionsPage.tsx:231）をクリックして CommissionPanel を開く。
4. 条件: 幅 390（vl-mobile-390 と同じ viewport）と 1280、言語 ja / en、テーマ ライト / ダーク。変更前（origin/main の CommissionPanel.tsx）と変更後で同じ spec・同じ fixture を実行する。
5. 記録: document.documentElement の scrollWidth/clientWidth、`[data-testid=commission-table]` の scrollWidth/clientWidth、各 select の getBoundingClientRect と computed style（width・height・min-height・padding・font-size・background-image・border）、aria-label・data-testid・value・disabled・option の value と文字列。fixture・生出力 JSON・スクショは /tmp/CC報告ファイル/ssot-ay2w/impl/ に保存し、要約を docs/handoff/design-system-recon/evidence-20260910/ay2w-acceptance.md に書く。
6. 分岐: 認証回避が現在の認証方式（ADR-1013 の自社ログイン）で効かずに画面が出ない場合は、回避策を自作せず BLOCKED で停止して報告する。

## 7. 代替案
- A children モード + size="sm"（採用）: 現行の未割当＝空の選択肢の挙動を逐語で保てる。行内のボタンと高さがそろう。
- B options モード + placeholder: placeholder は required 時に disabled になる等、空選択の意味が金型側の仕様に依存し、現行の「未割当に戻す」操作が変わるおそれ → 不採用。
- C fullWidth: 列幅 45% いっぱいに広がり表の横幅計算へ影響しうる。PO の「表はいまの見た目のまま」に反するおそれ → 不採用。
- D 表統一便まで待つ: PO が n を選ばなかった → 不採用。

## 8. リスクと戻し方
- 見た目の変化は select 1 種（役割の数の行）に限られる。意図した変化として PR に前後表を載せる。
- 横 overflow の悪化は B1 で検出して停止する。
- 戻し方: merge commit の revert（DB・API・backend 影響なし）。

## 外部・過去事例の参照と我々への応用
- 過去: §AW-2b（design.md:2156-2180）で生 select 53 件を children モードで逐語移管し、保留 10 件の 1 つがこの CommissionPanel だった。本便は同じ逐語移管を保留 1 件に適用する。§AJ（design.md:1252-1270）の 390px 横 overflow 測定を B1 の基準に使う。
- 外部事例: 不要（自社の金型への置き換え。自社実物の前後比較が直接の根拠）。

## 維持の仕組み
- 守り手: frontend/src/components/Select.tsx・frontend/src/components/FormField.css（金型の正本）と、docs/CC_UI_GOVERNANCE.md（ADR-144）。
- 守り手2: §5 で追加する試験（class と onChange の挙動を固定）。scripts/check-ui-governance.js は pages/ 配下のみ対象（:37 `PAGES_DIR`）で components/ は検出しない点を design.md 残件に記録する（検出範囲の拡大は既存の PO 判断事項「CI 検出範囲」に含める）。

## 9. 文書の更新（Opus が行う）
- docs/specs/design-system/design.md: AY-2v の本番反映記録、§AY-2w 節の追加、:2056 の保留行を「AY-2w で移管」に更新。§AJ・§AW-2b の過去記録の本文は書き換えない。

## 相互参照
- recon: docs/handoff/ay2w-commission-select/recon.md
- 証跡: docs/handoff/design-system-recon/evidence-20260910/ay2w-*（実装時に作成）
