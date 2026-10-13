# design: 請求書詳細と報酬ページの入力欄6件の標準化（AY-2o）

recon 相互参照: docs/handoff/sales-doc-commission-inputs/recon.md
以下は設計書 ay2o-design.md の内容をそのまま転記する。実装結果は docs/specs/design-system/design.md の「AY-2o 実装結果」に記録。

#### AY-2o 請求書詳細と報酬の入力欄6件の標準化（2026-10-13）

mode: handoff。§AY の一行入力を金型へ移す便の続き。PO 原文（2026-10-13）「後で反映させるので並行して進めている金型の部品に置き換える作業を進めてくれ」、同日の離席時の一任「フロントエンドのパーツもデザイントークンとデザインシステム を遵守して、金型登録のないハードコードを禁止する。…PRマージ、デプロイまで完走させてくれ」。GO は ADR-1003 の委任に基づき Claude Opus が発行する。

現在地（origin/main 0aef04b30。調査全文は /tmp/CC報告ファイル/ssot-ay2o/recon-raw.md と recon-b.md）:
- 生のテキスト系 input は金型本体を除き 51 件（保留 22）。今回の6件は保留ではなく、ページ側の ref 使用0、ui-allow なし。
- A1 frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:241 `<input readOnly value={invoice.paypal_approval_url} style={{ flex: 1, padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", fontSize: "var(--font-sm)" }} />`。PayPal の顧客支払い URL の読み取り専用表示。親 :236 は flex・gap space-2・alignItems center、兄弟は :242 ButtonLink size="md"（h36）。表示条件は paypal_approval_url が真かつ status≠paid。試験の参照0。
- A2 同 :290-291 `<input style={{ width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }} value={voidReason} onChange={…} placeholder={t("invoices.voidReasonPlaceholder")} />`。無効化理由の入力（無効化ボタンで開くフォーム）。親は block。試験 frontend/src/components/CommerceNavigationButtonMigration.test.tsx:98-102 が placeholder で参照。
- B1/B2 frontend/src/pages/commissions/CommissionsPage.tsx:141,153、B3/B4 frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:277,289。`<label>年:<input type="number" … style={{ width: "var(--input-width-year)", marginLeft: "var(--space-2)" }} data-testid="…"/></label>`（月は --input-width-month）。月次集計の年・月。親 label、その親は flex・gap space-2・alignItems center。testid は commissions-year/-month、monthly-year/-month（参照0）。同じ設定ページの表 :208 SelectControl・:221 TextFieldControl type=number はどちらも金型 md（h39.6）。
- 6件に当たる CSS 規則は0（祖先に .form-group 等なし）。現状の見た目は A がブラウザ既定 Arial＋inline、B がブラウザ既定（padding 0・2px inset・角0・Arial 13.33px・h19）。
- A1/A2 の `1px solid var(--border)` は金型を通らない枠の直書き（px 1件ずつ）。
- トークン: --input-width-year 90px（tokens.css:429）、--input-width-month 60px（:433）。

設計判断（設計者、2026-10-13）:
- 6件とも TextFieldControl の standard・md（size 指定なし）。理由: 一般フォームは標準（PO 方針、AY-2m・AY-2n と同じ）。B3/B4 は同じ画面の表の入力（:208・:221）が md なので、同画面で高さがそろう。B1/B2 は B3/B4 の複製なので同じ扱い。
- inline style は配置だけ残し外観を消す（AY-2e・AY-2n の規則）:
  - A1: `{{ flex: 1 }}`（padding・borderRadius・border・fontSize を削除）
  - A2: `{{ width: "100%" }}`（padding・borderRadius・border を削除）
  - B1〜B4: 変更なし（width トークンと marginLeft はどちらも配置）
- 新トークンなし。i18n・testid・属性は逐語保持（A1 に aria-label を足すことはしない＝i18n キー追加になり本便の範囲外）。
- 月の欄 60px は md だと内容幅 34px（左右余白 12px×2＋枠 2px）。値「12」が切れないことを実測で確認する。切れた場合は実装を止めて報告（幅トークンの変更は並びを変えるので設計者が判断し直す）。

AY-2o 変更契約:
1. InvoiceDetailPage.tsx:241 の `<input` を `<TextFieldControl` に、style を `{{ flex: 1 }}` に。readOnly・value は逐語、属性の順も変えない。
2. InvoiceDetailPage.tsx:290 の `<input` を `<TextFieldControl` に、style を `{{ width: "100%" }}` に。value・onChange・placeholder は逐語、順も変えない。
3. CommissionsPage.tsx:141,153 と CommissionSettingsPage.tsx:277,289 の `<input` を `<TextFieldControl` に。type・value・min・max・onChange・style・data-testid は逐語、順も変えない。
4. import: 3ファイルに TextFieldControl の import が無ければ既存の並びに合わせて追加（CommissionSettingsPage.tsx と InvoiceDetailPage.tsx は既に import 済みか実物で確認し、重複させない）。
5. 変えないもの: 上記以外の要素、ButtonLink・Button、label、親の div、CSS、トークン、i18n、試験・e2e、backend。既存の試験が落ちたら試験を直さず止まって報告。
6. design.md（docs/specs/design-system/design.md）に AY-2n の本番反映の記録、本節、実装結果を追記。recon.md・design.md を docs/handoff/sales-doc-commission-inputs/ に置く（AY-2n の docs/handoff/inventory-search-input/ と同じ型）。

前後表（予定。実画面で確定）:
| 対象 | 変わる項目 |
|---|---|
| A1・A2 | 余白 8px → 8px 12px、文字 Arial 13.6/13.33px → inherit 14.4px、line-height normal → 1.5、角 4px → var(--comp-input-radius)、高さ 33 → 約39.6。枠の色・太さは同じ値（1px var(--border)）だが金型経由になる |
| B1〜B4 | 余白 0 → 8px 12px、枠 2px inset → 1px solid var(--border)、角 0 → var(--comp-input-radius)、文字 Arial 13.33px → inherit 14.4px、高さ 19 → 約39.6。幅 90/60px は変化なし |
| 並び | A1 と ButtonLink、B の年・月と label の文字は横に並んだまま（縦中心の差 ±2px 以内） |

受入:
| 基準 | 検証方法 |
|---|---|
| 金型に変わる | 開発モードの build と preview（偽ログイン・API モック、/tmp/CC報告ファイル/ssot-ay2o/ay2o-measure.cjs）で /invoices/3・/commissions・/commission-settings を幅1280・1440、DPR2 で開き、6件に class comp-field__input があることを DOM で記録。前後のスクリーンショット |
| 幅・並び | 6件の left・width の差 ±1px 以内（A1 は flex なので兄弟 ButtonLink の left・width も ±1px）。A1 と ButtonLink、B の各欄と親 label の縦中心の差が after で ±2px 以内。top・height は記録のみ |
| 文字が切れない | B の年に 2026・月に 12、A1 に既定のダミー URL、A2 に 30 文字の理由を入れ、scrollWidth ≤ clientWidth。月の欄は focus・hover 状態（数字の上下ボタンが出る状態）のスクリーンショットも撮り、設計者が目視で「12」が欠けないことを確認 |
| 動作 | A2: 無効化ボタンで開き、文字を入れて値が入る、キャンセルで閉じる（前後同じ）。B: 年・月を変えると月次集計の API 呼び出しの query が変わる（前後同じ URL） |
| 横はみ出し | document の scrollWidth == clientWidth（前後とも） |
| 試験 | 単体試験の全件成功（CommerceNavigationButtonMigration.test.tsx を含む）。testid・placeholder の保持を grep で確認 |
| 品質 | generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI 必須がすべて成功 |
| 本番 | Deploy 成功。本番 JS に該当画面の testid（commissions-year・monthly-year）と comp-field__input、旧 inline の `border:"1px solid var(--border)"` を持つ input 定義が 0。app と /api/health が 200 |

外部事例: 不要（既存の金型 TextFieldControl を前例 AY-2k・AY-2m・AY-2n と同じ型で使う）。

維持の仕組み:
- 守り手: CommerceNavigationButtonMigration.test.tsx（A2 placeholder）、TextField.test.tsx、scripts/check-ui-governance.js（pages の生 input の増加を検出。ただし number 型は検出対象外＝:87-90）、frontend-check。
- 守っていないもの: type=number の生 input は check-ui-governance.js が検出しない（別便で検出範囲の拡張を検討）。一覧画面の検索欄5件（search 変種か standard かの方針判断が要る）、AND/OR の生 button、保留 22 件。
- 切戻し: 本 PR の merge commit を revert（DB 影響なし）。

改訂1（2026-10-13、Fable 設計審査1回目 REVISE への対応。本文と食い違う所は改訂1が優先）:
- LOW-1 行番号の訂正: A1 の親の flex div は InvoiceDetailPage.tsx:240（:236 は表示条件）。number 型を検出しない根拠は scripts/check-ui-governance.js:213-218 isDetectableInput（:87-90 ではない）。トークンは frontend/src/tokens.css:429・:433。
- LOW-2 import の確定: CommissionsPage.tsx だけに `import { TextFieldControl } from "../../components/TextField";` を追加する（既存 import 文の並びに合わせ、実際の相対パスは同ファイルの他の components import と同じ書き方に従う）。InvoiceDetailPage.tsx:19 と CommissionSettingsPage.tsx:18 は import 済みなので触らない。
- HIGH-1 計測手順の固定（before もこの手順で取り直す）:
  1. 計測スクリプト /tmp/CC報告ファイル/ssot-ay2o/ay2o-measure.cjs を複製して ay2o-measure2.cjs を作り、次を足す。
     - B の4欄: 年に fill("2026")、月に fill("12") を入れてから scrollWidth・clientWidth・getBoundingClientRect を記録。
     - 月の欄: focus 状態と hover 状態のそれぞれで、欄の周り（要素の矩形＋上下左右 8px）を切り出したスクリーンショットを撮る（幅1280・1440、DPR2）。
     - A2: 無効化ボタンで開き、30 文字の理由（例「テスト用の無効化理由です。三十文字ちょうどになるように調整す」＝30文字。実際の文字数を記録）を fill、scrollWidth・clientWidth・value を記録。その後キャンセルで閉じ、A2 が DOM から消えたことを記録。
     - API の記録: page.route で記録する URL を pathname だけでなく pathname＋search（query 込み）にする。B は年・月を変えた後に呼ばれた月次集計 API の URL を記録。
  2. 実装担当は、新しい作業ツリーで「変更前のコード」のまま build・preview して before を取り、次に変更を入れて同じスクリプトで after を取る。出力先は /tmp/CC報告ファイル/ssot-ay2o/before2/ と after/。
  3. 判定: 月「12」・年「2026」・A2 の30文字・A1 の URL で scrollWidth ≤ clientWidth（A1 だけは URL の長さ次第で切れて表示されるのが readOnly の一行欄の通常動作なので、before と after で scrollWidth>clientWidth の真偽が同じであることを基準にする。before の実測では 1020/1020・1180/1180 で切れていない）。月 focus/hover の画像で「12」の2文字が欠けずに見えることを設計者が目視で判定。API の URL（query 込み）が before と after で同一。
  4. 分岐（LOW-3）: 月「12」が after で切れた場合は実装を commit せずに止めて報告する。設計者が次のどちらかを選び直す — (a) 月だけ size="sm"（同じ画面の md と高さがそろわなくなる）、(b) --input-width-month を広げる（前後表と並びが変わる）。担当は自分で選ばない。
- MEDIUM-1 本番の判定文字列の差し替え: 本番の main JS で (1) `padding:"var(--space-2)",borderRadius:"var(--radius-sm)",border:"1px solid var(--border)"` の並びが 0 件（現在 frontend/src では :241・:290 の2件だけがこの並び。実装後に git grep で 0 件を確認してから本番でも 0 件を確認）、(2) `commissions-year`・`monthly-year`・`comp-field__input` がそれぞれ1件以上。3画面は App.tsx で静的 import なので main chunk で判定できる。
- LOW-4 記録: A1 は readOnly のまま。金型に readonly 専用の見た目は無く、前後とも通常の入力欄と同じ見た目（変化なし）。
- 基準 SHA: 実装時に origin/main を取り直して記録する。

Architect 審査（AY-2o）: 1回目 REVISE（Fable）→ 改訂1 → 2回目 APPROVE（2026-10-13）。Fable は AI の審査で、PO 承認や人のレビューではない。

## 維持の仕組み
- 守り手: frontend/src/components/CommerceNavigationButtonMigration.test.tsx（A2 placeholder）、frontend/src/components/TextField.test.tsx、scripts/check-ui-governance.js（生 input の増加を検出。ただし type=number は検出対象外＝:213-218）、.github/workflows/frontend-check.yml。
- 守っていないもの: type=number の生 input（別便で検出範囲の拡張を検討）、一覧画面の検索欄5件（search 変種か standard かの方針判断が要る）、AND/OR の生 button、保留 22 件。
- 切戻し: 本 PR の merge commit を revert（DB への影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要。既存の金型 TextFieldControl を、前例（AY-2k #4125 の明細入力欄、AY-2m #4181、AY-2n #4223）と同じ型で使うため。前例からの応用: 外観の inline style（padding・borderRadius・border・fontSize）は消し、配置（flex・width・marginLeft）だけ残す（AY-2e の「金型移行は見た目を変え、並びは変えない」）。幅トークンを持つ type=number は AY-2k の qty/weight が前例。

## 関係する ADR
- ADR-144（UI ガバナンス）: 生 input を金型へ移す本便の根拠。docs/adr/ADR-144-ui-component-governance.md、docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン強制）: 新トークンなし。docs/adr/ADR-067-design-token-enforcement.md。
- ADR-027（UI 国際化）: placeholder・label は既存の t() キーを逐語で保持。docs/adr/ADR-027-ui-internationalization.md。
- ADR-1003（GO の委任）: GO は Claude Opus が発行。docs/adr/ADR-1003-go-delegation-to-opus.md。
- 相互参照: recon は docs/handoff/sales-doc-commission-inputs/recon.md。
