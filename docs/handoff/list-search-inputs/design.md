# design: 一覧画面の検索欄5件の標準化（AY-2p）

recon 相互参照: docs/handoff/list-search-inputs/recon.md
以下は設計書 ay2p-design.md の内容をそのまま転記する（本文＋改訂1＋改訂2。食い違う所は新しい改訂が優先）。実装結果は docs/specs/design-system/design.md の「AY-2p 実装結果」に記録。

#### AY-2p 一覧画面の検索欄5件の標準化（2026-10-14）

mode: handoff。§AY の一行入力を金型へ移す便の続き。PO 決定（2026-10-13）: 一覧画面の検索欄5件は「普通の入力欄の型（TextFieldControl standard・md）」にそろえる（検索用の型 variant="search" は使わない）。PO の y 回答による。GO は ADR-1003 の委任に基づき Claude Opus が発行する。

現在地（origin/main d39e251。調査全文は /tmp/CC報告ファイル/ssot-ay2p/recon-raw.md・recon-fieldw.md・recon-searchbar.md、実測は before/measure-before.json と before-table.txt）:
- S1 frontend/src/pages/companies/CompaniesPage.tsx:387-393 `<input type="text" className="search-input field-h-md field-w-md" placeholder={t("companies.searchPlaceholder")} value onChange>`（ContentToolbar left 内）。TextFieldControl import 済み（:30）。
- S2 frontend/src/pages/contacts/ContactsPage.tsx:282-288 `<input type="text" … className="search-input field-h-md field-w-sm">`。直前 :276 に SelectControl field-w-sm。import 済み（:33）。
- S3 frontend/src/pages/inventory/InventoryPage.tsx:384-395 `<input type="search" className="field-h-md field-w-md" data-testid="inventory-search" … onKeyDown>`。兄弟は Button sm ×3。import なし。
- S4 frontend/src/pages/orders/OrdersFilterBar.tsx:32-40 `<input type="search" className="field-h-md field-w-md" aria-label={t("orders.title")} placeholder={t("common.search")} data-testid="orders-search-input">`。e2e 6件が testid で参照（orders-list.spec.ts:154,222 他）。import なし。
- S5 frontend/src/pages/products/ProductsPage.tsx:218-219 親 `<div className="search-bar" style={{display:"flex",gap:"var(--space-4)",alignItems:"center"}}>`、`<input className="field-h-md field-w-sm" type="text" placeholder={t("common.search")} value onChange>`。import なし。
- 5件とも ref・ui-allow なし。`.search-input` に当たる CSS 規則は0（死にクラス）。
- 変更前の見た目: S1〜S4 はブラウザ既定（padding 0・2px inset・角0・13.33px）、高さ 36（field-h-md の min-height）。S5 は components.css:56-65 `.search-bar input`（1px・角4px・min-width 280px）で幅 280（field-w-sm 160 は min-width に負けている）。
- 重要な事実: TextFieldControl は className を input 自身に付ける（TextField.tsx:43-50）。`.comp-field__input{width:100%}`（FormField.css:47-62）は field-size.css より後に読み込まれ詳細度が同じ (0,1,0) なので、`field-w-*` が負ける。実測で `comp-field__input field-w-md` の幅は 301.8（280 にならない）。SelectControl は前例 AW-2b（#4033）の複合セレクタ `.comp-select__control.field-w-*`（field-size.css:13-16）で同じ問題を解決済み。TextFieldControl に field-w-*/field-h-* を渡す既存箇所は 0 件（325 タグ走査）。
- `.search-bar` は ProductsPage の div と、ConditionsPage・ProductCategoriesPage・StatusMasterPage・SuppliersPage・UnitsPage の form（計6）で使う共有クラス。規則は components.css:50-65 のみ（margin-bottom space-4 と `.search-bar input` の外観）。`.search-bar input` は (0,1,1) で `.comp-field__input` に勝つ。

設計判断（設計者、2026-10-14）:
1. 5件とも TextFieldControl standard・md（size 指定なし）。PO 決定どおり。
2. 幅を守るため field-size.css の幅規則に `.comp-field__input.field-w-sm/md/lg` を併記する（AW-2b の select と同じ型。既存の利用0なので影響は本便の5件だけ）。新トークンなし。
3. S5 は親 div の className "search-bar" を外し、input の幅クラスを field-w-sm → field-w-md にする。理由: `.search-bar input` が金型の外観（角4px 等）を上書きするため金型に移らない。共有の components.css は他5画面が使うので触らない。field-w-md（280）にすると現在の実幅 280 が保たれる。外した結果 margin-bottom space-4 も消える（ツールバー内の縦位置が変わる。現状の右スロットとの縦中心差 8px が縮む見込み。実測で記録）。
4. その他の属性は逐語保持（`search-input`・`field-h-md` も残す。どちらも after では効果なし＝死にクラス・min-height 36 < 39.6 だが、外す変更は本便の範囲外）。type="search"・data-testid・aria-label・onKeyDown も保持。
5. 高さは 36 → 39.6 に変わる。兄弟のボタン（28/36）とは高さがそろわないが、同じ行の SelectControl は既に 39.6 で同じ状態。縦中心は flex center でそろう（受入で確認）。

AY-2p 変更契約:
1. frontend/src/components/field-size.css の幅3規則のセレクタ列に `.comp-field__input.field-w-sm`・`…-md`・`…-lg` を追加。12行のコメントに「TextFieldControl の width:100% より優先（§AY AY-2p）」を足す。値・他の規則は変えない。
2. S1〜S4: `<input` を `<TextFieldControl` に。属性・順は逐語。S3・S4・S5 のファイルに `import { TextFieldControl } from "<既存 components import と同じ相対パス書式>/components/TextField";` を既存の並びに合わせて追加（S1・S2 は import 済みなので触らない）。
3. S5: :218 の div から `className="search-bar"` だけ削除（style は残す）。:219 を `<TextFieldControl className="field-h-md field-w-md" type="text" placeholder={t("common.search")} value=… onChange=… />`（field-w-sm→md 以外は逐語）。
4. 変えないもの: components.css、FormField.css、TextField.tsx、tokens、i18n、試験・e2e、兄弟要素、他の5画面の search-bar、backend。既存試験が落ちたら試験を直さず止まって報告。
5. docs: docs/specs/design-system/design.md に AY-2o 本番反映の記録と本節・実装結果を追記。recon.md・design.md を docs/handoff/list-search-inputs/ に置く（AY-2o と同じ型）。証跡は docs/handoff/design-system-recon/evidence-20260910/ay2p-*。

前後表（予定。実画面で確定）:
| 対象 | 変わる項目 |
|---|---|
| S1〜S4 | 余白 0 → 8px 12px、枠 2px inset → 1px solid var(--border)、角 0 → var(--comp-input-radius)、文字 13.33px → 14.4px、高さ 36 → 39.6。幅（280/160/280/280）は変化なし |
| S5 | 角 4px → var(--comp-input-radius)、高さ 36 → 39.6、ツールバー内の縦位置（margin-bottom 消失）。幅 280・余白・枠は同じ値 |

受入:
| 基準 | 検証方法 |
|---|---|
| 金型に変わる | 開発モード build＋preview（偽ログイン・API モック、/tmp/CC報告ファイル/ssot-ay2p/ay2p-measure.cjs、before と同じスクリプト）で5画面×幅1280・1440・DPR2。5件に class comp-field__input があることを DOM で記録。前後のスクリーンショット（設計者が目視） |
| 幅 | 5件の width が before と ±1px（280/160/280/280/280）。left も ±1px（S5 は margin 消失で left は不変の見込み、top は記録のみ） |
| 並び | 各欄と同じ行の兄弟（ボタン・select）の縦中心差が after で ±2px 以内（S5 の右スロットは記録し、before 8.00 からの変化を報告） |
| 動作 | 文字入力で value が入り、一覧 API の URL（pathname+search）が before と同一。S3 は Enter で検索が走る（before と同じ URL） |
| 横はみ出し | document の scrollWidth == clientWidth（前後とも） |
| 他画面に影響なし | field-size.css 変更の影響確認として SelectControl の field-w-sm（連絡先 select 160）が after も 160。git grep で `.comp-field__input` と field-w-* を併用する箇所が本便の5件だけ |
| 試験 | 単体試験の全件成功。e2e の orders-search-input（6件）の testid・placeholder（/検索/）を grep で保持確認。horizontal-overflow.spec.ts の対象 /inventory・/orders は計測の横はみ出しで代替 |
| 品質 | generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook、CI 必須がすべて成功 |
| 本番 | Deploy 成功。本番 CSS に `.comp-field__input.field-w-md`、本番 JS に `orders-search-input` と `inventory-search` があり comp-field__input と同じ要素定義。app と /api/health が 200 |

外部事例: 不要（既存の金型 TextFieldControl と field-size の複合セレクタを、前例 AW-2b・AY-2k〜2o と同じ型で使う）。

維持の仕組み:
- 守り手: TextField.test.tsx、e2e orders-*.spec.ts（testid）、horizontal-overflow.spec.ts、scripts/check-ui-governance.js（pages の生 input 増加の検出）、frontend-check。
- 守っていないもの: `.search-bar input`（components.css:56-65）を使う他5画面の form 内入力は生 input/旧外観のまま（別便）。死にクラス search-input と効果のない field-h-md の除去（別便）。type=number の生 input は check-ui-governance.js:213-218 が検出しない。
- 切戻し: 本 PR の merge commit を revert（DB 影響なし）。

改訂1（2026-10-14、Fable 設計審査 r1 APPROVE の MEDIUM/LOW 反映。本文と食い違う所は改訂1が優先）:
- MEDIUM-1: 幅 768px 未満では FormField.css:443-448 の min-height 44px が field-h-md に勝つため、S1〜S5 の高さは 36→44 になる（打ち消さない＝金型のモバイル既定どおり）。前後表に追記扱い。受入に幅375・DPR2 で5画面の検索欄 height を前後記録する（after は 44±1 を合格、横はみ出し scrollWidth==clientWidth も幅375で前後記録）。
- MEDIUM-2: S1・S3 は左スロットに 39.6 の select が無く、ContentToolbar（ContentToolbar.css:12 min-height 36）が 36→約39.6 に伸び、表の開始位置が約3.6px 下がる見込み。受入に5画面の .content-toolbar の height と一覧（表）先頭の top を前後記録し、差を報告する（S2・S4 は差 ±1px、S1・S3 は +4px 以内、S5 は margin 消失分を記録のみ）。
- LOW-2: 本番の判定を一義にする。本番 JS で生 input のまま残る形 `"input",{type:"search",className:"field-h-md field-w-md"` が 0 件（before の build で S3・S4 の2件あることを実装担当がローカル build で先に確認し、after build で 0 件を確認）。加えて `.comp-field__input.field-w-md` が本番 CSS に1件以上。
- LOW-3: S3・S4・S5 の import は `import { TextFieldControl } from "../../components/TextField";`（S4 は frontend/src/pages/orders/ 配下で同じ深さであることを実物で確認）。
- 基準 SHA: 実装時に origin/main を取り直して記録する。

改訂2（2026-10-14、実装時の想定外1件への設計者判断。根拠 /tmp/CC報告ファイル/ssot-ay2p/w375-cause.md）:
- 事実: 幅375で S2 149→160、S3 149→192。原因は CSS 宣言値ではなく flex の自動最小幅（min-width:auto）で、金型の余白・文字サイズにより入力欄の内容ベースの床が 149→192 になったため（実験: comp-field__input を外すと 149、min-width:0 で 56）。S3 の「詳細フィルタ」は変更前から右端が切れており（可視 47.5/92.5）、変更後は可視 4.5。どちらも祖先 .page-layout-content（frontend/src/pages-layout.css:90 overflow auto）の横スクロールで全体が見え、document の横はみ出しは前後とも無し。幅375でも同じ InventoryPage（App.tsx:206、ShellSwitch の Outlet）。
- 判断: 許容して進める。理由: (1) ボタンが画面に収まらないのは変更前からある在庫ツールバーのスマホ幅の不具合で、本便の変更が原因ではない（変更前も切れていた）。(2) 代わりの対処の min-width:0 は検索欄が 56px まで縮み入力できる幅でなくなるので採らない。(3) ツールバーをスマホ幅で折り返す等の直し方は配置の設計変更で本便の範囲外。
- 維持の仕組みの「守っていないもの」に追加: 在庫一覧のツールバーは幅375でボタンが画面に収まらない（変更前から。別便で折り返し等を設計）。
- 受入の補足: 幅375の width は記録のみ（基準外）。本番判定の JS 文字列はバッククォート形 `` `input`,{type:`search`,className:`field-h-md field-w-md` `` で 0 件（build 出力の書式に合わせる。改訂1 LOW-2 を差し替え）。S3 の Enter 検索は onKeyDown を逐語保持（diff）で確認し、実画面の前後比較は未実施として記録する。

Architect 審査（AY-2p）: Fable 設計審査 r1 APPROVE（MEDIUM 2・LOW 3 を改訂1 に反映、2026-10-14）。Fable は AI の審査で、PO 承認や人のレビューではない。PO 方針決定: 2026-10-13「一覧画面の検索欄5件を標準の入力欄の型にそろえる」y。

## 維持の仕組み
- 守り手: frontend/src/components/TextField.test.tsx、scripts/check-ui-governance.js（pages の生 input 増加を検出。ただし type=number は検出対象外＝:213-218）、frontend の horizontal-overflow e2e、frontend-check（CI）。
- 守っていないもの: `.search-bar input`（frontend/src/components/components.css:56-65）を使う他画面の form 内入力は生 input/旧外観のまま（別便）。死にクラス search-input と効果のない field-h-md の除去（別便）。type=number の生 input は check-ui-governance.js:213-218 が検出しない。在庫一覧のツールバーは幅375でボタンが画面に収まらない（変更前から。別便で折り返し等を設計。改訂2）。
- 切戻し: 本 PR の merge commit を revert（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 不要。既存の金型 TextFieldControl と field-size の複合セレクタを再利用するだけで、新しい仕組みを入れないため。
- 過去事例: AW-2b #4033 の複合セレクタ（`.comp-field__input.field-w-*` で幅を指定する型）を、field-size.css に sm/md/lg を併記して踏襲した。AY-2k〜2o の同型移管（生 input を TextFieldControl へ移し、外観は金型に任せ、並びは変えない）を5画面の検索欄に適用した。
- 応用: 幅は前後差0を計測で確認し、幅375のみ flex の自動最小幅で S2 149→160、S3 149→192 になったが、変更前からの不具合の延長として改訂2で許容した。

## 関係する ADR
- ADR-144（UI ガバナンス）: 生 input を金型へ移す本便の根拠。docs/adr/ADR-144-ui-component-governance.md、docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン強制）: 新トークンなし。docs/adr/ADR-067-design-token-enforcement.md。
- ADR-027（UI 国際化）: placeholder・aria-label の t() キーは逐語保持。docs/adr/ADR-027-ui-internationalization.md。
- ADR-1003（GO の委任）: GO は Claude Opus が発行。docs/adr/ADR-1003-go-delegation-to-opus.md。
- 相互参照: recon は docs/handoff/list-search-inputs/recon.md。

## main 取り込み後の再確認（2026-10-14）
- 取り込み: origin/main fbdf92a1b（基準 6c8a5955a から12コミット先行）を merge。衝突は frontend/src/pages/inventory/InventoryPage.tsx の import 行1件のみ、両方残して解消。
- main 側の変更: InventoryPage.tsx（PageLayout headerAction・Drawer 追加、一覧 API に merge_same_post=true 追加、列追加）、locales、openapi.json 等。検索欄・ツールバー・兄弟ボタン周辺は無変更。全文: evidence-20260910/ay2p-merged-main-delta.txt。
- 在庫一覧の再計測（幅1280・1440・375、evidence-20260910/ay2p-merged-*）: 幅 280→280（375 は 149→192 で改訂2により許容）、高さ 36→39.61（375 は 44）、toolbar 36→39.61・表の開始位置 +3.6、縦中心差 0.01 以内、横はみ出しなし、console error なし。API URL は origin/main そのままと merge 後で一致。
- 品質（merge 後）: generate / tsc / lint / check:all / test:coverage（1054 passed）/ build すべて exit 0（ay2p-merged-quality-exitcodes.txt）。storybook は merge 前に exit 0、merge 後は未実行。
