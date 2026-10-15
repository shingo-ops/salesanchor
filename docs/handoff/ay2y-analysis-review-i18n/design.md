# AY-2y 設計: 商品マスタ引き出し画面・原文欄の英語化と金型移管

mode: handoff。ADR-027 / ADR-144 / ADR-067 を継承。recon: docs/handoff/ay2y-analysis-review-i18n/recon.md。生出力は /tmp/CC報告ファイル/ssot-ay2y/（recon/・impl/）。実測の前後表: docs/handoff/design-system-recon/evidence-20260910/ay2y-acceptance.md。

状態: 設計審査済み（Fable r1 REVISE → r2 APPROVE。/tmp/CC報告ファイル/ssot-ay2y/design-review.md・design-review-r2.md）。見える変化は、金型の見た目と、閉じるボタンの「×」の文字が X アイコンになること（R2-2）。§0 は本文より優先する。

## 0. r2 の確定事項（本文と食い違うときはこちらが正）
- **R2-1（HIGH-1）候補選択 :344・:469**: `Button variant="ghost" size="md"` にし、中身を `<span>` 1つで包む（`<span><strong>{c.product_id}</strong> {c.japanese_title}</span>`。:469 は今の空白2つをそのまま）。`layoutClassName` の class に書いてよいのは text-align・width・justify-content・white-space（normal）だけ。それでも ja の innerText が変わる、または横 overflow が増えるときだけ B7 で停止。
- **R2-2（M-1）閉じる :507**: 前例 frontend/src/components/Drawer.tsx:150-158 と同じ形（`Button variant="ghost" size="md" iconOnly aria-label={t('common.close')}`、中身は constants/icons.tsx の X アイコン `aria-hidden`）。見た目は「×」の文字が X アイコンに変わる（変更として記録）。B2 の比較からはこのボタンの中身だけ除く（aria-label「閉じる」は比較に含める）。
- **R2-3（M-2）textarea の最小高**: AX-2b の記録（標準にして最小高だけ配置規則として残す）に従う。`--pmd-textarea-min-h`（:113）は残し、`.pmd-field textarea`（:255-258）を `.pmd-field .comp-field__textarea { min-height: var(--pmd-textarea-min-h); }` の1規則に置き換える（resize は金型に任せる。textarea の class 名は実物に合わせる）。§4-3 の「--pmd-textarea-min-h も削除」は取り消す。
- **R2-4（M-3）SourceRawPane.tsx:28**: `// eslint-disable-next-line react-hooks/exhaustive-deps -- run only when jump.requestId changes` で抑止する。依存配列は変えない。停止条件にはしない。
- **R2-5（M-4・M-5）size と variant を確定**:
  - 引き出し画面の入力欄（文字・日付・複数行）は、すべて size="sm"（手本 ReviewRegisterProductForm.tsx:339-399 と同じ）。
  - 引き出し画面のボタンは size="md"（手本 :409・:414・:419 と同じ）。

  | 行 | ボタン | variant |
  |---|---|---|
  | :240 | 重複候補を確認 | secondary |
  | :247 | 商品マスタに登録 | primary |
  | :332 | マスタを検索 | secondary |
  | :358 | キーワードを追記 | primary |
  | :457 | 検索（割り当て） | secondary |
  | :477 | 商品を変更 | primary |
  | :480 | 確認済みとして記録 | secondary |
  | :344・:469 | 候補選択 | ghost |
  | :507 | 閉じる | ghost・iconOnly |

  - モードごとに出る区画は1つだけなので、primary は1画面に1個になる。
  - 原文欄（SourceRawPane）は、入力欄が `TextFieldControl size="sm"`、ボタン3つが `Button variant="secondary" size="sm"`（狭い1行の中で高さ 28px にそろえる）。
- **R2-6（L-1）**: :320 は Trans に固定する（前例 pages/integrations/FedexEtdSetupGuide.tsx:367-369。i18n.ts:35 は escapeValue:false）。キーは `keywordIntro`（ja「Gemini抽出名「<strong>{{name}}</strong>」を既存商品の検索キーワードに追記します。」）。分割案は削る。
- **R2-7（L-2）※の英訳を確定**:
  - fieldWork = Series
  - fieldManufacturer = Manufacturer
  - fieldCategory = Product category
  - fieldMark = Mark
  - fieldReleaseDate = Release date

  既存キーからは写さない。
- **R2-8（L-3）**: n=1 のとき「1 extracted items」になるが、許容する（複数形のキーは足さない）。
- **R2-9（L-4・L-5）**: SearchSelect は `<label className="pmd-field">` で包む形を残し、ラベルと入力欄は入れ子で関連付ける（id は足さない）。`useTranslation` は次の6つに足す: SearchSelect、RegistrationSection、SearchKeywordSection、ExcludedSection、ProductMasterDrawer、SourceRawPane。SearchSelect の placeholder は SearchSelect の中で t() する。PO「y」2026-10-15（2ファイルの日本語を翻訳キーにし、ja/en の訳を足し、入力欄・ボタンを金型へ移して本番まで。英訳は Opus が用意し英語画面も確認。日本語の表示は変えない）。
mode: handoff。親: docs/specs/design-system/README.md。ADR-144 / ADR-067 / ADR-027 を継承。
保留の正: docs/specs/design-system/design.md:2344・:2401・:2572（「ProductMasterDrawer.tsx 7（警告63）と SourceRawPane.tsx 1（警告11）は同ファイルの i18n・警告解消と同時」）。
recon: /tmp/CC報告ファイル/ssot-ay2y/recon/（WT /Users/tanizawashingo/worktrees/salesanchor/release-ay2y-analysis-review-i18n、0c7852fd9 起点）。PR では docs/handoff/ay2y-analysis-review-i18n/recon.md として置く。

## 1. 目的（PO に見える変化）
- 画面: スーパー管理 → 解析ルール（/super-admin/analysis-rules）→ 仕入元詳細。商品行から開く「商品マスタ」引き出し画面（4モード: 新規登録／検索キーワード追記／除外対象／商品割り当て）と、左の原文検索欄。
- 日本語画面: 表示される文言は一字一句同じ。入力欄・ボタンの見た目がアプリ共通の金型にそろう。
- 英語画面: この2か所が英語で表示される（今は日本語のまま出る）。
- 動き（検索・登録・重複確認・キーワード追記・商品変更・確認済み記録・行ジャンプ）は変わらない。

## 2. 対象ファイル（これ以外の製品コードは触らない）
1. frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx
2. frontend/src/features/tcg-analysis-review/SourceRawPane.tsx
3. frontend/src/features/tcg-analysis-review/supplier-detail-view.css（pmd-* の生要素向け規則の削除のみ）
4. frontend/src/features/tcg-analysis-review/source-raw-pane.css（:48 の `.source-search input` の扱いのみ）
5. frontend/src/locales/ja.json・en.json（新キー追加。同じ位置・同じキー）
6. 試験（新規）・docs・証跡

## 3. i18n（ADR-027）
### 3-1. キーの置き場所と再利用の規則
- 新キーは既存ブロック `tcgAnalysisReview`（ja/en とも :4644）の中に `productMasterDrawer` と `sourceRawPane` の2つの子として足す。ja と en は同じ位置・同じ順。
- 再利用するのは「既存キーの ja 値が今の文言と完全一致し、意味も同じ」ものだけ。次の6つに限る（実装者は ja 値の完全一致を実物で確認し、違えば新キーにする）:
  - `common.close`（閉じる）・`common.previous`（前へ）・`common.next`（次へ）
  - `superAdmin.supplierQuality.productAssign.searchPlaceholder`（商品名を入力）・`.searching`（検索中…）・`.noResults`（検索結果なし）… 同じ引き出し画面の商品割り当てモードが既に使っているキー
  - `reviewIssues.excluded`（除外対象）… 同じ課題の表示名
- `inbox.emptyField` など別画面のキーは、文言が同じでも再利用しない（新キー `emptyValue`）。

### 3-2. 書き方の規則
- 「ラベル: 値」は `{t('…label')}: {value}` と書く（コロンと半角空白は JSX に残す）。ja の表示が今と同じになり、利用者の入力値を翻訳文字列へ埋め込まない。
- 数を含む文言は「抽出商品 {itemCount}件」だけ。`t('tcgAnalysisReview.sourceRawPane.extractedItems', { n: itemCount })`（変数名は `n`。`count` は複数形の解決が走るので使わない）。
- 太字が文中に入る :320 の1文は `Trans`（`components={{ strong: <strong /> }}`）で書く（R2-6）。
- :222・:233 の `eslint-disable-next-line local/no-japanese-literal` は、文言を t() 化したうえで削除する。

### 3-3. キーと訳（ja は今の文言を一字一句そのまま。en は以下）
`tcgAnalysisReview.productMasterDrawer.`:
| キー | ja（今の文言） | en |
|---|---|---|
| searchSelectPlaceholder | 名称で検索・選択 | Search or select by name |
| unselected | 未選択 | Not selected |
| emptyValue | 未入力 | Not entered |
| registeredTitle | 商品マスタへの登録が完了しました（次回解析で反映） | Registered in the product master (applied from the next analysis) |
| product | 商品 | Product |
| issuedProductId | 発行された商品ID | Issued product ID |
| registerHeading | 商品マスタ新規登録 | New product master entry |
| formLoading | 登録フォームを読み込み中… | Loading registration form… |
| fieldKind | 大分類 | Major category |
| fieldWork | 作品 | ※ |
| fieldManufacturer | メーカー | ※ |
| fieldCategory | 商品カテゴリ | ※ |
| fieldMark | マーク | ※ |
| fieldJapaneseTitle | 日本語タイトル | Japanese title |
| fieldEnglishTitle | 英語タイトル | English title |
| fieldReleaseDate | 発売日 | ※ |
| fieldSearchKeywords | 検索キーワード | Search keywords |
| fieldExcludeKeywords | 除外キーワード | Exclude keywords |
| confirmHeading | 登録内容確認 | Review entry |
| duplicateWarning | 既存商品の可能性があります（確認してください） | This may be an existing product (please check) |
| duplicateConfirmed | 重複候補を確認しました（新規商品です） | I checked the possible duplicates (this is a new product) |
| registerError | 登録エラー | Registration error |
| checking | 確認中… | Checking… |
| checkDuplicates | 重複候補を確認 | Check for duplicates |
| saving | 登録中… | Registering… |
| register | 商品マスタに登録 | Register in product master |
| keywordExists | このキーワードはすでに登録済みです。 | This keyword is already registered. |
| keywordAddFailed | 追記に失敗しました。 | Failed to add the keyword. |
| keywordAddedTitle | 検索キーワードを追記しました（次回解析で反映） | Search keyword added (applied from the next analysis) |
| addedKeyword | 追記したキーワード | Added keyword |
| keywordHeading | マスタ検索・検索キーワード追記 | Master search / add search keyword |
| keywordIntro | Gemini抽出名「<strong>{{name}}</strong>」を既存商品の検索キーワードに追記します。 | Add the Gemini extracted name “<strong>{{name}}</strong>” to an existing product's search keywords. |
| notAvailable | 未取得 | Not available |
| searchByName | 商品名で検索 | Search by product name |
| searchMaster | マスタを検索 | Search master |
| currentKeywords | 現在の検索KW | Current keywords |
| selected | 選択中 | Selected |
| keywordToAdd | 追記するキーワード | Keyword to add |
| adding | 追記中… | Adding… |
| addKeyword | キーワードを追記 | Add keyword |
| excludedBody | この商品は商品マスタの除外キーワードに一致したため、解析から除外されています。 | This product matched an exclude keyword in the product master, so it is excluded from analysis. |
| geminiName | Gemini抽出名 | Gemini extracted name |
| excludedHowTo | 除外キーワードの確認・変更は 商品マスタV2 シートの Exclude Keywords 列から直接行ってください。 | To check or change exclude keywords, edit the Exclude Keywords column of the “商品マスタV2” sheet directly. |
| editLater | （編集機能は今後のリリースで追加予定） | (Editing will be added in a future release.) |
| drawerAriaLabel | 商品マスタメンテナンス | Product master maintenance |
| drawerTitleFallback | 商品マスタ修正 | Edit product master |

※ の en は、同じ意味の既存キーの en 値をそのまま写す（作品=`reviewItem.wizard.register.work`、メーカー=`reviewItem.wizard.register.manufacturer`、マーク=`reviewItem.wizard.register.mark`、発売日=`reviewItem.wizard.register.releaseDate`、商品カテゴリ=`nav.productCategories`）。写した値と元キーを報告する。
- Trans で `{{name}}` を使う場合、i18n.ts の `interpolation.escapeValue` を確認する。false でなければ Trans の children 方式（`<strong>{{name}}</strong>` を JSX 側で渡す）にし、文字列への埋め込みで `&amp;` 等が出ないことを試験で固定する。
- 「商品マスタV2」はシート名（固有名）なので en でも日本語のまま残す。英語画面の日本語残り検査（§6 B6）の例外はこの1語と、mock データの値だけ。

`tcgAnalysisReview.sourceRawPane.`:
| キー | ja | en |
|---|---|---|
| noMatch | 該当行がありません | No matching lines |
| sourceCount | 原文 1件 | 1 source message |
| extractedItems | 抽出商品 {{n}}件 | {{n}} extracted items |
| searchLabel | 原文検索 | Search source |
| searchPlaceholder | L0006 または文字列 | L0006 or text |
| move | 移動 | Go |
| rawAriaLabel | 原文全文 | Full source text |

## 4. 金型移管（ADR-144。手本は同じ feature の ReviewRegisterProductForm.tsx）
### 4-1. ProductMasterDrawer.tsx
- 文字入力: SearchSelect 内 :54（`list={listId}` はそのまま渡す。datalist :64-66 は残す）、:187・:191（`required` はそのまま）・:195・:325・:448（`onKeyDown` はそのまま）を `TextFieldControl` へ移す。:199 の `type="date"` も `TextFieldControl type="date"` にする（前例: pages/inbox/InboxProfileModal.tsx:198、pages/shifts/ShiftsPage.tsx:65）。
- 複数行入力: :203・:207 を `TextareaControl` へ移す。
- size: ReviewRegisterProductForm.tsx で同じ種類の入力に使っている size に合わせる（実物で確認し、ファイル:行を報告）。同じ種類が無い入力は同ファイルの文字入力と同じ size にする。
- ボタン: :240・:247・:332・:358・:457・:477・:480 を `Button` へ移す。variant と size は、ReviewRegisterProductForm.tsx の同じ役割のボタン（登録の確定・検索・確認）に合わせる。対応が無いものは `variant="secondary" size="sm"`。どのボタンを何に合わせたか表で報告する。type・disabled・onClick・表示文言の条件分岐はそのまま。`loading` prop は使わない（文言の切り替えは今のまま t() で行う）。
- 閉じる :507: `Button variant="ghost" iconOnly aria-label={t('common.close')}`。中身は同じ feature 内または features/tcg-product-import/TcgProductDetailDrawer.tsx の閉じるボタンの前例（アイコン定数）に合わせる。前例が無ければ "×" を中身に残す（記号で、日本語ではない）。
- 候補選択 :344・:469: `Button variant="ghost"`（size は他のボタンと同じ）にし、左寄せと横幅いっぱいが要るなら、Button の `layoutClassName` に配置だけの class（text-align・width・justify-content だけ。色・枠・余白・文字の大きさは書かない）を足す。それで「strong の ID＋名前」が今と同じ並びで出ないなら、停止して報告する（B7）。
- 触らない: :229 のチェックボックス（Checkbox の金型が未作成。PO の判断待ち）、:503 の背景 div、h2/h3/p/small の構造、API 呼び出し、状態管理、MasterMaintenanceSection の分岐。

### 4-2. SourceRawPane.tsx
- :30 の input を `TextFieldControl`（size は 4-1 と同じ考え方。周りのボタンと高さがそろう size）、button 3つを `Button variant="secondary" size="sm"`（submit は `type="submit"` を維持）。
- :30 の1行は、読みやすさのために複数行へ整形してよい（JSX の構造・属性・順序は変えない）。
- :28 の `react-hooks/exhaustive-deps` 警告: `jump?.requestId` が変わったときだけ動かすのが意図。リポジトリに `eslint-disable-next-line react-hooks/exhaustive-deps -- <理由>` の前例が1件以上あれば、同じ書式で理由を付けて抑止する（例: `-- jump.requestId が変わったときだけ実行する`）。前例が0件なら停止して NEEDS_DECISION（依存配列を変えると動きが変わるおそれがあるため、勝手に直さない）。

### 4-3. CSS
- supplier-detail-view.css: `.pmd-field input, .pmd-field textarea`（:244-253）、`.pmd-actions button`（:260-268）、`.pmd-actions button:disabled`（:309-312）、`.pmd-head button`（:227-236）、`.pmd-search-candidate button`（:293-301）を削除する。`.pmd-field textarea`（:255-258）は R2-3 の1規則に置き換え、`--pmd-textarea-min-h`（:113）は残す。候補ボタンの配置規則 `.pmd-search-candidate .pmd-candidate-btn { white-space: normal; text-align: left; width: 100%; justify-content: flex-start; }` を `.pmd-search-candidate small`（:303）の直後に1つ足す（r2 審査 MEDIUM-1。bare class では .comp-btn と同じ強さになり読み込み順で負けるため）。
- source-raw-pane.css: `.source-search input { min-width: 0; }`（:48）は、金型の input にも grid の縮みが要るなら `.source-search .comp-field__input` に書き換え、要らないなら削除する（実測で判断し、理由を報告）。`.source-search` の grid（:28-34）は変えない。
- 新しい色・数値は使わない。stylelint で止まったら停止。

## 5. 触らない範囲
SupplierDetailView.tsx・ItemComparison.tsx・ほかの features、API・backend・DB・migrations・deploy.yml・scripts、金型本体（TextField.tsx・Textarea.tsx・Button.tsx・FormField.css。Textarea への invalid 追加はしない）、チェックボックス、`.line-jump`（共有）、既存キーの値の変更。

## 6. 停止条件（該当したら直さずに止まり、Opus へ NEEDS_DECISION）
- B1: 390px または 1280px で、引き出し画面本体（.pmd-body）または原文欄（.source-search の行・.source-raw）の横 overflow（scrollWidth - clientWidth）が変更前より増える。
- B2: 日本語画面で、4モードの引き出し画面と原文欄に表示される文字（innerText）と、aria-label・placeholder の値が、変更前と1文字でも違う。
- B3: 操作したときの API 呼び出し（パス・メソッド・本文）が変更前と違う。対象は、重複確認・登録・マスタ検索・キーワード追記・商品変更・確認済み記録の6つ。
- B4: 2ファイルに対する pre-commit と同じ eslint（`--max-warnings=0`）で、警告が1件でも残る。
- B5: tsc・lint・check:all・check:new-tokens・check:i18n-missing-keys・stylelint・build・build-storybook のどれかが失敗する。
- B6: 英語画面の innerText・aria-label・placeholder に、日本語（ひらがな・カタカナ・漢字）が残る。例外は「商品マスタV2」と mock データの値（mock の値は ASCII で用意する）。
- B7: 候補選択ボタンの並び（ID の太字＋名前、左寄せ）を、配置だけの class で保てない。
- B8: ja.json と en.json で、足したキーの集合が一致しない（キーの差分 0 を jq などで実測する）。

## 7. 試験（新規。frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx・SourceRawPane.test.tsx）
- 近隣の試験（ReviewRegisterProductForm.test.tsx:3, :76）と同じく、実際の i18n を import する。ja と en の両方で描画する。
- ProductMasterDrawer は4モードを描画する。モードは review_issues で切り替える。
  - ja で、主な文言が今と同じに出ること（見出し・ボタン・確認欄の「大分類: 未選択」等）。
  - en で、日本語が出ないこと（「商品マスタV2」を除く）。
  - 入力欄が `comp-field__input`・`comp-field__textarea` 系の金型 class を持つこと（class 名は実物に合わせる）。
  - ボタンが金型の class を持つこと。
  - 登録モードで、必須（日本語タイトル）が空だとボタンが disabled になること。
  - api は vi.mock で差し替える（前例の書式に合わせる）。
- SourceRawPane:
  - ja で「原文 1件」「抽出商品 3件」が出ること、en で「1 source message」「3 extracted items」が出ること。
  - 存在しない文字を入れると、ja で「該当行がありません」、en で「No matching lines」になること。
  - 一致が複数あるときだけ「前へ」「次へ」が出ること。
- 試験が終わったら言語を ja に戻す（ほかの試験へ影響させない）。

## 8. 実測（AY-2x と同じ方法。一時 spec はコミットしない）
- 条件: 390 / 1280px × ja / en × ライト / ダーク の8条件。
- 状態:
  - 引き出し画面の4モード: 登録（空、重複候補ありで、チェック前・チェック後）、キーワード追記（検索結果あり・選択後）、除外、割り当て（検索結果あり・選択後）。
  - 原文欄: 一致が複数ある状態と、一致が0件の状態。
- 取る値:
  - 入力欄・ボタンの computed style（font-size、height、padding、border-color、border-radius、background、color）と rect。
  - innerText（B2・B6）、aria-label、placeholder。
  - .pmd-body と .source-search の scrollWidth / clientWidth。
  - API 呼び出しの記録（B3）。
- 生出力は /tmp/CC報告ファイル/ssot-ay2y/impl/ に置く。要約は docs/handoff/design-system-recon/evidence-20260910/ay2y-acceptance.md に前後の表で残す。前後の測定 JSON（ay2y-measure-before.json / ay2y-measure-after.json）も同じ場所に置く。
- mock: installAuthBypass・mockApi・ALL_PERMISSIONS と、/me/permissions（is_super_admin: true）の前例（/tmp/CC報告ファイル/ssot-ay2x/impl/ay2x-measure.spec.ts）に従う。仕入元一覧と仕入元詳細の API は、実物の呼び出しを確かめてから mock する。
- WT の frontend/node_modules（本店へのシンボリックリンク）はコミットに含めない（git status で未追跡に出ないか、.gitignore にあるかを確認する）。

## 9. 受入条件
| 基準 | 検証方法 |
|---|---|
| 日本語の表示が今と同じ | 実測 B2（8条件中 ja 4条件で innerText・aria-label・placeholder の差 0）、試験 §7 |
| 英語画面に日本語が残らない | 実測 B6、試験 §7 |
| 入力欄・ボタンが金型の class | 試験 §7、実測の DOM |
| 動きが同じ | 実測 B3（API 呼び出しの差 0）、試験 §7 の disabled |
| 2ファイルの eslint 警告 0 | pre-commit と同じ eslint の出力（74→0） |
| ja/en のキーが一致 | B8 の実測、check:i18n-missing-keys exit 0 |
| 横 overflow が増えない | 実測 B1 |
| 直値の色・新トークンなし | check:all・check:new-tokens・stylelint exit 0 |
| 型・ビルド | tsc・build・build-storybook exit 0 |
| 本番 | merge 後の本番 JS に `tcgAnalysisReview.productMasterDrawer` のキーがある（または en 文言「Register in product master」がある）。本番 CSS の `.pmd-actions button{` が 0 件。app と /api/health が 200 |

## 10. docs
- docs/specs/design-system/design.md
  - :2401 の保留行と :2572 の件数を更新する（保留 22→14。ProductEditPage 14 だけが残る）。
  - 末尾に、AY-2x の本番反映記録を観測値だけで足す。中身は PR #4279 merge c1fc79f12 14:06:17Z、deploy 38577549205 success 14:09:05Z、本番 CSS index-BGBdy_e3.css で invalid の規則があり `.dist-input` が 0 件、app 200、/api/health 200。出典は /tmp/CC報告ファイル/ssot-ay2x/prod/checks.txt。
  - 続けて §AY-2y 節（目的・変更・キーの置き場所・実測・PO 決定）を足す。
- docs/handoff/ay2y-analysis-review-i18n/{recon,design}.md
  - パスはフルパス（リポジトリ相対の完全なパス）で書く。
  - design.md には「## 外部・過去事例の参照と我々への応用」と「## 維持の仕組み」の見出しを入れる。

## 11. 代替案
- A（採用）: i18n 化と金型移管を1便で行う。pre-commit の警告0が前提なので、分けると i18n 化だけの便が先に要る。同じファイルを2回触ると、前後比較が2回に分かれる。
- B: i18n 化だけ先に行い、金型は別便にする。PO の承認は1便でまとめる形だったので、不採用。
- C: `--max-warnings` の閾値を変える・`--no-verify` を使う。design.md:2344 で禁止しているので、不採用。

## 12. 戻し方
本 PR の merge commit を revert する（DB への影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例は不要。自社の金型と ADR-027 の i18n 規則を当てはめる便で、自社の実物の前後比較が直接の根拠になる。
過去事例は次の2つ:
- §AY-2x（生 input を TextFieldControl へ逐語で移管）
- 同じ feature の ReviewRegisterProductForm.tsx（同じ登録フォームの金型版）

## 維持の仕組み
守り手: frontend/scripts/eslint-rules/no-japanese-literal.cjs（frontend/eslint.config.js で有効、pre-commit `--max-warnings=0`）、check:i18n-missing-keys、frontend/src/components/Button.tsx・frontend/src/components/TextField.tsx・frontend/src/components/Textarea.tsx、frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx・frontend/src/features/tcg-analysis-review/SourceRawPane.test.tsx

- ESLint の local/no-japanese-literal（pre-commit で `--max-warnings=0`）
- check:i18n-missing-keys
- 金型（TextField.tsx・Textarea.tsx・Button.tsx）
- 追加する試験
- docs/CC_UI_GOVERNANCE.md

注記: check-ui-governance は pages/ だけが対象で、features/ は見ない。これは既知の残件（CI の検出範囲、PO の判断待ち）。

## 追記 R2-10（実装中の B1 停止を受けた Opus の設計判断、2026-10-15）
- 観測: 原文検索で複数行が当たった状態で、`.source-search` の横はみ出しが増えた。390 ja は 0→7px、390 en は 0→61px、1280 en は 0→23px（/tmp/CC報告ファイル/ssot-ay2y/impl/compare.txt）。原因は、金型のボタンが広くなり、:30 の `minmax(130px, 1fr)` の下限と合わせると枠を超えること。
- 判断: `.source-search` を2段にする。
  - 1段目はラベルだけの全幅（`label { grid-column: 1 / -1 }`）。
  - 2段目は `minmax(0, 1fr) auto auto auto`。
  - 新しい値は使わない。見える変化は、ラベルが入力欄の上に移ること。
- 結果: 測り直しで B1 該当なし（docs/handoff/design-system-recon/evidence-20260910/ay2y-acceptance.md）。frontend/src/features/tcg-analysis-review/source-raw-pane.css の `.source-search input { min-width: 0; }` は残した。
- 不採用にした案:
  - ボタンの余白を絞る案。金型から外れるため。
  - 下限だけ0にする案。390 en で入力欄が約69px まで縮むため（実測値から推算）。
