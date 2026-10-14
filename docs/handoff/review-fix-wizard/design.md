<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-fix-wizard

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`  
**recon**: `docs/handoff/review-fix-wizard/recon.md`（追加調査の生出力はリポジトリ外 ~/CC報告ファイル-keep/review-page-20261013/ に保存）  
**日付**: 2026-10-14  
**担当**: Planner（Opus）。設計審査は Fable（architect）

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-14）:「直すの選択肢は選べるように出来る？新規商品として登録するのか、既存の商品として登録するのかなど、選択しながら進められるようにしたい、質問形式で埋めていく項目を変化させたながら人間が選択入力しながら修正していく。実現できる？理解できる？」
- 決定（2026-10-14、PO「y」）: 最初の質問「何を直しますか？」に次の4つを出す。
  1. 既存の商品に付け替える（全件）。任意で「この書き方を検索キーワードに追加する」。
  2. 新しい商品として登録する（商品が未決定の件だけ）。登録したら**続けてこの行をその新商品に付け替える**。
  3. 状態を直す（状態の確認が必要な件だけ）。
  4. このままで良い（新解析 v102 の件で、確認済みにできる理由だけ）。
  - 「除外する」は出さない（保存する仕組みが無い。recon §2 ExcludedSection）。
  - 選択肢はカード型（ラジオ型）の部品を**金型として新規登録する**（ADR-144 の PO 許可。同日の「y」）。
  - 「戻る」で選び直せる。
  - 要確認スライドの「商品マスタ修正」（ProductMasterDrawer）は、この流れに置き換える。

## 1. 目的（KGI）

PO が要確認スライドの「直す」欄を使うとき、次がすべて ○ になる。

- K1: 「直す」欄の先頭に「何を直しますか？」と、カード型の選択肢が出る。出る選択肢は §3 の表どおり（例: 商品が決まっている件に「新しい商品として登録する」は出ない。v6 の件に「このままで良い」は出ない）。「除外する」はどの件にも出ない。
- K2: 選択肢を1つ選ぶと、その選択肢の入力欄だけが出る。「戻る」を押すと、入力途中の内容は消えて質問に戻る。
- K3: 「新しい商品として登録する」で保存すると、商品マスタに登録され、続けてこの行がその新商品に付け替えられる（保存は1回の操作で2つの API が順に呼ばれる）。
- K4: 似た商品が見つかったら「この中に同じ商品がありますか？」と聞かれる。候補を選ぶと**登録せずに**その商品へ付け替える。「どれも違う」を選ぶと新規登録して付け替える。
- K5: 登録は成功したが付け替えが失敗した場合、「登録済み（番号）。付け替えだけやり直す」が出て、押すと付け替えだけが再送される（商品の二重登録は起きない）。
- K6: 「既存の商品に付け替える」で、「この書き方を検索キーワードに追加しますか？」に「追加する」を選んで保存すると、付け替えと検索キーワード追加の両方が行われ、それぞれの結果が表示される。
- K7: 要確認スライドから「商品マスタ修正」ボタンと別ドロワーが無くなる。仕入元詳細（SupplierDetailView）の「商品マスタ修正」は今のまま動く。

## 2. 変更前 → 変更後

### 変更前（recon §1・§2、追加調査 §7）

`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:78-118` の「直す」欄は上から順に、付け替えフォーム（ReviewProductFixForm）、状態（ConditionReviewPanel）、「商品マスタ修正」ボタン（別ドロワー ProductMasterDrawer を開く）、理由一覧（v102 の ackable な理由に「このままで良い」）を、件によらず全部並べる。ProductMasterDrawer の新規登録（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:88-274`）は登録だけで、行には付け替えない。生 input と日本語直書きが多い。

### 変更後

「直す」欄は次の構成にする。

1. 見出し「直す」（既存キー）。
2. **理由一覧（読むだけ）**: 今の理由一覧（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:89-116`）から「このままで良い」ボタンを外したもの。GapSuspectNote は今のまま理由の横に出す。
3. **質問「何を直しますか？」**: 新しい金型 ChoiceCardGroup（§4）。選択肢は §3 の表で決める。出せる選択肢が0個のときは質問を出さず、文言 `reviewItem.wizard.nothingToFix` を出す。
4. 選択肢を選ぶと、質問は1行の要約「直す内容: ＜選んだ選択肢＞」＋「戻る」ボタン（Button 金型、variant は既存の secondary 相当。Generator が Button の props を実物で確認）に縮み、その下に選択肢ごとの入力欄（§5）が出る。
5. 保存が成功したら、成功の Callout を出し、`onRefresh()` を呼び、質問の状態に戻す（選択を外す）。Callout は次の操作まで残す。

新しい部品はファイルを分ける。

- `ReviewFixWizard`（frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx、新規）: 質問と分岐。props は `{ item: ReviewDrawerItem; onRefresh: () => Promise<void> }`。
- `ReviewRegisterProductForm`（frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx、新規）: 選択肢2の入力・重複確認・登録→付け替え。
- 見た目は frontend/src/features/tcg-analysis-review/review-fix-wizard.css（新規、`var()` のみ）。

## 3. 選択肢を出す条件（対応表）

判定はフロントにある値だけで行う（追加調査 §7。`pid_resolved` はフロントに無いため `review_issues` を使う）。判定関数は ReviewFixWizard.tsx に置き、`export` して試験する。

| # | 選択肢 | 出す条件 | 根拠 |
|---|---|---|---|
| 1 | 既存の商品に付け替える | 常に出す | corrections は全件で使える（recon §3「補正保存」） |
| 2 | 新しい商品として登録する | `item.review_issues` に `PRODUCT_ID_UNRESOLVED` か `PRODUCT_MASTER_UNREGISTERED` を含む | registration-form は pid_resolved の件で 404（recon §3）。PRODUCT_MASTER_UNREGISTERED のときは PRODUCT_ID_UNRESOLVED も付く（recon §4） |
| 3 | 状態を直す | ConditionReviewPanel の表示条件 `relevant` が真 | `frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:25-27`。この条件式を同ファイルから `isConditionReviewRelevant(item)` として export し、パネル内部もそれを使う（式を2か所に書かない） |
| 4 | このままで良い | `item.is_v102 === true` かつ、`review_reason_details` に `ackable !== false` でまだ確認済みにしていない理由が1つ以上ある | 今の条件 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:99-109` と同じ。v102 専用（非 v102 は 409）、condition_unknown は非 ackable（recon §3） |
| — | 除外する | 出さない | 保存先が無い（recon §2 ExcludedSection、§4 EXCLUDED の原因） |

選択肢の並び順は上の # の順。

## 4. 新しい金型 ChoiceCardGroup（ADR-144、PO 許可 2026-10-14）

- ファイル: frontend/src/components/ChoiceCardGroup.tsx、ChoiceCardGroup.css、ChoiceCardGroup.stories.tsx、ChoiceCardGroup.test.tsx（同じディレクトリ）。前例 `frontend/src/components/Stack.tsx` と同じ構成。components/ に index は無いので直接 import（追加調査 §9）。
- props:
  ```ts
  export type ChoiceCardOption<V extends string> = {
    value: V;
    label: string;          // 呼び出し側で t() 済み
    description?: string;   // 1行の補足（呼び出し側で t() 済み）
    disabled?: boolean;
  };
  export type ChoiceCardGroupProps<V extends string> = {
    legend: string;         // 質問文（画面に見える）
    name: string;           // radio の name
    options: ChoiceCardOption<V>[];
    value: V | null;
    onChange: (value: V) => void;
  };
  ```
- DOM: `<fieldset class="comp-choice-card-group">` ＋ `<legend>`。各選択肢は `<label class="comp-choice-card">` の中に `<input type="radio">`（見た目は隠すが、フォーカスと矢印キー操作はブラウザ標準のまま）＋ label ＋ description。金型の内部なので生 radio を使ってよい（ADR-144 は金型の中身を規定しない。`scripts/check-ui-governance.js` も radio を数えない＝追加調査 §1）。
- 見た目: カードは枠線・角丸・余白をトークンで。選ばれたカードは枠色を強調色、フォーカス時は既存のフォーカスリングと同じトークン。disabled は `--opacity-dim`。色・px の直値は書かない（ADR-067）。使うトークン名は Generator が `frontend/src/tokens.css`（例 `--opacity-dim` は :264）から選び、PR に一覧を書く。
- 縦並び（1列）。幅は親に合わせる。
- 試験（ChoiceCardGroup.test.tsx）: legend が出る／クリックで onChange が value 付きで呼ばれる／`value` のカードが checked／disabled はクリックしても呼ばれない／矢印キーで隣へ移る（user-event）。
- story: 「4択・未選択」「選択済み」「disabled あり」「description なし」。

## 5. 選択肢ごとの入力欄

### 5-1. 既存の商品に付け替える

- 今の ReviewProductFixForm（`frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx`）をそのまま使い、任意 props `suggestKeyword?: string` を足す。
- `suggestKeyword` が空でないとき、商品を選んだ後（保存ボタンの前）に ChoiceCardGroup で「この書き方「＜suggestKeyword＞」を検索キーワードに追加しますか？」→「追加しない」（初期選択）／「追加する」を出す。
- ReviewFixWizard は `suggestKeyword = item.gemini.name`（今の SearchKeywordSection と同じ語。`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:301-304`）を渡す。
- 保存の順: ①今どおり postProductCorrection → 成功したら ②「追加する」のときだけ `addSearchKeyword(product_id, suggestKeyword)`（POST `/tcg/products/{id}/search-keywords`、id は候補の `product_id`＝整数文字列。追加調査 §8）。
- 結果表示:
  - ①成功＋②が `ok:true` → `reviewItem.wizard.keyword.added`。
  - ①成功＋②が HTTP 200 で `ok:false, code:"KEYWORD_ALREADY_EXISTS"`（例外ではない＝`backend/app/services/tcg_product_master_svc.py:536`）→ `reviewItem.wizard.keyword.failed` の reason に `reviewItem.wizard.keyword.exists`。
  - ①成功＋②がそれ以外の `ok:false` → keyword.failed の reason に code。②が例外（ApiError）→ keyword.failed の reason に ApiError の message。
  - ①失敗 → ②は呼ばない（今の失敗表示のまま）。
- `suggestKeyword` を渡さないときの見た目と動きは今と同じ（既存試験 `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.test.tsx` はそのまま通る）。

### 5-2. 新しい商品として登録する（ReviewRegisterProductForm）

画面の順:

1. 開いたら GET `/tcg/products/registration-form`（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:119` と同じ呼び方）。ApiError の status が 404 かつ `message === "PRODUCT_MASTER_V2_ALREADY_RESOLVED"` なら「この行の商品はすでに決まっています。「既存の商品に付け替える」を使ってください」を出し、入力欄は出さない。それ以外の失敗は `reviewItem.wizard.register.failed` に理由を入れて出す（`PRODUCT_MASTER_V2_EXTRACTION_ITEM_NOT_FOUND` も 404 だが別扱い）。
2. 入力欄（PO の並び順）:
   | 項目 | 部品 | 必須 |
   |---|---|---|
   | 商品種別（大分類） | AsyncCombobox 金型（読み込み済みの選択肢から絞り込む） | 必須 |
   | 作品 | AsyncCombobox 金型（同上） | 必須 |
   | メーカー | AsyncCombobox 金型（同上） | 必須 |
   | カテゴリ | AsyncCombobox 金型（同上） | 必須 |
   | 日本語名 | TextField 金型 | 必須 |
   | 英語名 | TextField 金型 | 任意 |
   | 記号 | TextField 金型 | 任意 |
   | 発売日 | TextField 金型 `type="date"`（TextField は type を素通しする。`frontend/src/components/TextField.tsx:29-30`） | 任意 |
   | 検索キーワード | Textarea 金型（1行1語。初期値は `item.gemini.name`） | 任意 |
   - 4つの選択欄（大分類・作品・メーカー・カテゴリ）は、件数に左右されないよう最初から AsyncCombobox にする（今の画面も打って絞り込む方式＝`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:49-84`。本番件数を Generator は取れないため、件数で部品を変える判断はしない）。
     - registration-form の lookups `{id, name}`（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:24`）を `{value: String(id), label: name}` に写す。
     - `loadOptions(query)` は、読み込み済みの一覧から label に query を含むもの（大文字小文字を区別しない）を最大 50 件、`Promise.resolve` で返す。API は呼ばない。
     - 見出しとエラーの付け方は ReviewProductFixForm と同じ（`frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx:55-73` の `comp-field` ＋ `comp-field__label`）。必須の印は `comp-field__required`、エラー文は `comp-field__hint comp-field__hint--error`（どちらも `frontend/src/components/FormField.css` の既存クラス）。
   - 必須は今と同じ（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:131-134`）。未入力のまま「似た商品がないか確認」を押すと、未入力の欄すべてにエラー文 `reviewItem.wizard.register.required` を出し、API は呼ばない。TextField／Textarea は金型の `error` props を使う。
   - 送る body のキー名・値の形は今の RegistrationSection（`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:140-160`）と同じにする。ただし**検索キーワードは、Textarea の各行の前後の空白を除き、空行を除いて `,` で join した1つの文字列**にする（backend はカンマで分ける＝`backend/app/services/tcg_product_master_svc.py:430,446`）。check-duplicates と /tcg/products の両方に同じ文字列を送る。除外キーワードは空文字。
3. 「似た商品がないか確認」ボタン → POST `/tcg/products/check-duplicates`。
   - 候補0件 → そのまま 4 へ。
   - 候補あり → ChoiceCardGroup「この中に同じ商品がありますか？」: 候補ごとの選択肢（label = japanese_title、description = 番号）＋最後に「どれも違う。新しく登録する」。
     - 候補を選んで「この商品に付け替える」→ postProductCorrection(item, 候補の product_id) だけを呼ぶ（登録しない）。
     - 「どれも違う」→ 4 へ（force=true）。
4. 「登録して付け替える」ボタン → ① POST `/tcg/products`（force は 3 の結果どおり）→ `ok:true` なら返った `product_id`（整数文字列、追加調査 §3）で ② postProductCorrection(item, product_id)。
   - ① で `ok:false, DUPLICATE_CANDIDATE` が返った（確認と登録の間に他で登録された）→ 3 の候補質問に戻す。
   - ① 成功・② 成功 → 成功 Callout「新しい商品（番号）を登録し、この行を付け替えました」→ onRefresh。
   - ① 成功・② 失敗 → 警告 Callout「新しい商品（番号）は登録済みです。付け替えに失敗しました（理由）」＋ボタン「付け替えだけやり直す」。押すと ② だけを再送する（① の結果は state に持つ）。「戻る」を押した場合も登録は残る旨を Callout に書く。
   - ① が成功して登録番号（registeredProductId）を state に持った後は、「登録して付け替える」「似た商品がないか確認」と入力欄は出さず、「付け替えだけやり直す」と「戻る」だけを出す（再押下での二重登録を画面上で起こせなくする）。
   - 二重送信防止: 保存中はボタンを disabled にし、処理中フラグを ref で持つ（ConditionReviewPanel と同じ型）。
5. API 呼び出しの関数は `frontend/src/features/tcg-analysis-review/reviewActions.ts` に足す（fetchRegistrationForm / checkProductDuplicates / createProduct / addSearchKeyword）。応答の型（registration-form の選択肢、重複候補、登録結果）は ProductMasterDrawer.tsx にある今の型定義を reviewActions.ts へ**移し**、ProductMasterDrawer.tsx はそれを import する（型を2か所に書かない）。ProductMasterDrawer.tsx の変更はこの型の移動と import だけ。

### 5-3. 状態を直す

- 今の ConditionReviewPanel をそのまま出す（label 付き）。変更は §3 の判定関数の export だけ。

### 5-4. このままで良い

- 確認済みにしたコードの一覧（今の ackedCodes）は ReviewFixWizard の state に置き、質問へ戻っても消さない。
- `ackable !== false` で未確認の理由だけを並べ、理由ごとに今の「このままで良い」ボタン（今の acknowledge 処理 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:48-62` を ReviewFixWizard へ移す）。送る body と API は今と同じ。

## 6. 文言（i18n。ja/en 同一キー、ADR-027）

新しいキーは `reviewItem.wizard.*` 名前空間に置く。Generator は既存の `reviewItem` 名前空間を実物で確認し、衝突があれば止めて報告する。

| キー | ja | en |
|---|---|---|
| reviewItem.wizard.question | 何を直しますか？ | What do you want to fix? |
| reviewItem.wizard.choice.reassign | 既存の商品に付け替える | Reassign to an existing product |
| reviewItem.wizard.choice.reassignDesc | 商品を検索して選びます | Search and pick a product |
| reviewItem.wizard.choice.register | 新しい商品として登録する | Register as a new product |
| reviewItem.wizard.choice.registerDesc | 商品マスタに登録し、この行を付け替えます | Add to the product master and reassign this row |
| reviewItem.wizard.choice.condition | 状態を直す | Fix the condition |
| reviewItem.wizard.choice.conditionDesc | 状態を確認・訂正します | Confirm or correct the condition |
| reviewItem.wizard.choice.keep | このままで良い | Keep as is |
| reviewItem.wizard.choice.keepDesc | 理由ごとに確認済みにします | Mark reasons as checked |
| reviewItem.wizard.selected | 直す内容: {{choice}} | Fixing: {{choice}} |
| reviewItem.wizard.back | 戻る | Back |
| reviewItem.wizard.nothingToFix | この行で直せる項目はありません | Nothing to fix on this row |
| reviewItem.wizard.keyword.question | この書き方「{{keyword}}」を検索キーワードに追加しますか？ | Add “{{keyword}}” as a search keyword? |
| reviewItem.wizard.keyword.no | 追加しない | Don't add |
| reviewItem.wizard.keyword.yes | 追加する | Add |
| reviewItem.wizard.keyword.added | 付け替えました。検索キーワードに追加しました | Reassigned and added the search keyword |
| reviewItem.wizard.keyword.failed | 付け替えました。検索キーワードは追加できませんでした（{{reason}}） | Reassigned, but the search keyword was not added ({{reason}}) |
| reviewItem.wizard.keyword.exists | すでに登録済みの書き方です | This keyword already exists |
| reviewItem.wizard.register.alreadyResolved | この行の商品はすでに決まっています。「既存の商品に付け替える」を使ってください | This row already has a product. Use “Reassign to an existing product”. |
| reviewItem.wizard.register.kind | 商品種別 | Product type |
| reviewItem.wizard.register.work | 作品 | Title / series |
| reviewItem.wizard.register.manufacturer | メーカー | Manufacturer |
| reviewItem.wizard.register.category | カテゴリ | Category |
| reviewItem.wizard.register.japaneseTitle | 日本語名 | Japanese name |
| reviewItem.wizard.register.englishTitle | 英語名 | English name |
| reviewItem.wizard.register.mark | 記号 | Code mark |
| reviewItem.wizard.register.releaseDate | 発売日 | Release date |
| reviewItem.wizard.register.keywords | 検索キーワード（1行に1つ） | Search keywords (one per line) |
| reviewItem.wizard.register.required | 入力してください | Required |
| reviewItem.wizard.register.checkDuplicates | 似た商品がないか確認 | Check for similar products |
| reviewItem.wizard.register.dupQuestion | この中に同じ商品がありますか？ | Is the same product in this list? |
| reviewItem.wizard.register.dupNone | どれも違う。新しく登録する | None of these. Register a new one |
| reviewItem.wizard.register.dupNumber | 番号 {{id}} | No. {{id}} |
| reviewItem.wizard.register.useCandidate | この商品に付け替える | Reassign to this product |
| reviewItem.wizard.register.submit | 登録して付け替える | Register and reassign |
| reviewItem.wizard.register.done | 新しい商品（番号 {{id}}）を登録し、この行を付け替えました | Registered new product (No. {{id}}) and reassigned this row |
| reviewItem.wizard.register.reassignFailed | 新しい商品（番号 {{id}}）は登録済みです。付け替えに失敗しました（{{reason}}）。「戻る」を押しても登録は残ります | New product (No. {{id}}) was registered, but reassigning failed ({{reason}}). The product stays registered even if you go back. |
| reviewItem.wizard.register.retryReassign | 付け替えだけやり直す | Retry reassign only |
| reviewItem.wizard.register.failed | 登録できませんでした（{{reason}}） | Could not register ({{reason}}) |

- 要確認スライドで使わなくなる既存キー（「商品マスタ修正」ボタンとヒントのキー）は、Generator が `git grep` で他の使用箇所を確認し、0件なら ja/en から両方消す。1件でもあれば残す。
- エラー理由 `{{reason}}` は、今の部品が使っている ApiError からの取り出し方（ReviewProductFixForm.tsx の実物）に合わせる。

## 7. 対象と対象外

- 対象（触るファイル）:
  - 新規: frontend/src/components/ChoiceCardGroup.tsx / .css / .stories.tsx / .test.tsx、frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx、ReviewRegisterProductForm.tsx、review-fix-wizard.css、ReviewFixWizard.test.tsx、ReviewRegisterProductForm.test.tsx
  - 変更: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`（「直す」欄を ReviewFixWizard に置き換え、ProductMasterDrawer の import と呼び出しを削除）、`frontend/src/features/tcg-analysis-review/ReviewProductFixForm.tsx`（suggestKeyword）、`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx`（判定関数の export）、`frontend/src/features/tcg-analysis-review/reviewActions.ts`（API 関数と型）、`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx`（型の移動に伴う import のみ）、`frontend/src/features/tcg-analysis-review/review-item-drawer.css`（使われなくなった規則があれば削除のみ。`.review-item-fix__product` は ReviewProductFixForm が使い続けるので残す）、`frontend/src/locales/ja.json`、`frontend/src/locales/en.json`、`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.stories.tsx`
  - 試験の更新:
    - `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`: :13 の ConditionReviewPanel の mock に `isConditionReviewRelevant` を足す（`vi.importActual` で実物を再 export する）。:14 の ProductMasterDrawer の mock は削除。:99-105（Product ラベル／Reassign ボタン／masterHint）は「選択肢1を選んだ後に Product ラベルと Reassign ボタンが出る」検査に書き換え、masterHint の検査は「無いこと」の検査にする。
    - `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.test.tsx`: 追加のみ。
    - `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`: :49 の「Edit」ボタンの検査は、質問「What do you want to fix?」が出る検査に置き換える。「Keep as is」を押す前に選択肢4（カード「Keep as is」）を選ぶ手順を足す。送る body・回数の検査は変えない。選択肢のカードとボタンが同じ名前「Keep as is」になるため、カードは radio の role、ボタンは button の role で区別して取る。
- 対象外:
  - backend・DB・migration（一切変えない。新規登録→付け替えは既存 API 2つの順呼びで成立する＝追加調査 §3・§4）。
  - SupplierDetailView と ProductMasterDrawer の画面（型 import 以外は触らない）。
  - 除外の保存、除外キーワードの編集。
  - 商品名・数量・価格の訂正（保存先が無い。#4259 の決定どおり）。
  - 新規登録・キーワード追加のあとの「他の行」の再解析（今の仕組みどおり次回解析で反映）。

## 8. 代替案と選択理由

- 案A（採用）: 金型 ChoiceCardGroup ＋ 選んだ分岐だけ出す。PO の「質問形式で項目を変化させながら」に直接合う。生 radio を金型の中に閉じ込められる。
- 案B: Tabs 金型で4タブ。タブは「見る場所の切り替え」の部品で、「答える質問」に見えない。件によって出ない選択肢があるとタブが歯抜けになる。不採用。
- 案C: Select で選ぶ。選択肢の説明（description）を出せず、選ぶ前に全体が見えない。不採用。
- 案D: ProductMasterDrawer を直して残す。別ドロワーへの移動が残り、生 input・直書きの金型移管も全面になる（範囲が大きい）。仕入元詳細では残し、要確認スライドだけ置き換える。

## 9. 外部・過去事例の参照と我々への応用

- 過去事例（社内）: #4259（`docs/handoff/review-drawer-align-form/design.md`）で「直す」欄を保存できる項目だけのフォームにした。今回はその上に質問を足す。保存できない項目を出さない方針を引き継ぐ（「除外する」を出さない）。
- 過去事例（社内）: `docs/handoff/review-inline-edit/design.md:18-24` で新規登録と ProductMasterDrawer の置き換えを対象外にしていた。今回がその別課題。
- 外部事例: 該当なし。理由: 部品の作り（fieldset＋legend＋radio）は HTML 標準の作法で、数値の効果を示す外部事例を設計の根拠に使っていない。成功は §10 の受け入れ基準で直接判定する。

## 10. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 選択肢の出し分け（§3 の表の4条件×出る/出ない、除外が無い） | `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx`（判定関数の表駆動試験＋描画） |
| K2 選ぶと入力欄が出る・戻るで質問に戻り入力が消える | `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx` |
| K3 新規登録→付け替えが順に1回ずつ呼ばれ、human_value が登録結果の product_id | `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx`（api.post の呼び出し順・引数） |
| K4 重複候補を選ぶと /tcg/products を呼ばずに付け替えだけ／「どれも違う」で force=true | `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx` |
| K5 付け替え失敗時「付け替えだけやり直す」で /tcg/products が再度呼ばれない | `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx` |
| K5 補足: registration-form が 404 のとき案内を出し入力欄を出さない | `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx` |
| K6 付け替え＋キーワード追加（成功／KEYWORD_ALREADY_EXISTS／付け替え失敗時は追加を呼ばない） | `frontend/src/features/tcg-analysis-review/ReviewProductFixForm.test.tsx`（追加ケース） |
| K7 要確認スライドに「商品マスタ修正」が無い／SupplierDetailView は無変更 | `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`＋`git diff --stat origin/main -- frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx` が空 |
| 「このままで良い」の送信 body・回数が今と同じ | `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx` |
| 金型の動作（選択・disabled・矢印キー） | frontend/src/components/ChoiceCardGroup.test.tsx |
| 文言は全部 t() 経由・ja/en 同一キー・色/px 直値なし | CI（eslint・i18n キー一致・ui-governance）全件 pass |
| 見た目（質問・選択後・新規登録フォーム・重複候補） | Storybook を Playwright で撮影した png を ~/CC報告ファイル-keep/review-page-20261013/ に保存し、Opus が目視確認 |
| 既存の試験が全部通る | `npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-analysis-review src/components src/pages/super-admin/components` と `npx tsc --noEmit`（frontend） |

## 11. リスクと対処

- 登録だけ成功して付け替えが失敗する → 「付け替えだけやり直す」で再送（K5）。登録は残ることを画面に書く。
- 新規登録した商品の他の行には、次回解析まで反映されない（今と同じ）→ 対象外に明記。成功文言は「この行を付け替えました」に限定し、他の行に効くとは書かない。
- 作品・メーカーの選択肢が多い → 最初から打って絞り込む部品（AsyncCombobox）にし、件数に依存しない（§5-2）。
- 既存の英語文言に依存する試験が壊れる → 対象に列挙済み。送信内容の検査は変えない。
- 生 radio を金型内で使う → 金型の中なので ADR-144 の範囲内。ゲートも数えない。

## 12. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | ChoiceCardGroup 金型（tsx/css/stories/test） | Generator（Sonnet） |
| 2 | reviewActions.ts に API 関数と型を移す・ProductMasterDrawer の import 差し替え | Generator（Sonnet） |
| 3 | ReviewProductFixForm に suggestKeyword、ConditionReviewPanel に判定関数 export | Generator（Sonnet） |
| 4 | ReviewRegisterProductForm・ReviewFixWizard・ReviewItemDrawer の差し替え・i18n | Generator（Sonnet） |
| 5 | 試験の追加・更新、tsc・vitest・eslint、Storybook 撮影 | Generator（Sonnet） |
| 6 | コード審査 | Fable（reviewer） |
| 7 | PR・GO・マージ・デプロイ確認 | Opus |

## 13. 戻し方・測り方

- 戻し方: マージコミットを `git revert -m 1` する PR を出す。backend・DB の変更が無いので、フロントの再デプロイだけで元に戻る。登録済みの商品はそのまま残る（正規の登録 API で作ったもの）。
- 測り方: 受け入れ基準の試験結果と Storybook の png。本番では、デプロイ後の JS に `reviewItem.wizard.question` の文言（ja「何を直しますか？」）が含まれることを確認する。本番画面での実操作の確認は PO の目視（未確認として報告する）。

## 維持の仕組み

- 選択肢の出し分けは ReviewFixWizard.tsx の1つの判定関数だけで決め、状態の条件は ConditionReviewPanel.tsx の関数を共用する（条件を2か所に書かない）。
- API の型は reviewActions.ts の1か所だけに置く。
- 守り手: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`（「直す」欄が質問で始まり、商品マスタ修正が無いこと）、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`（「このままで良い」の送信内容）、`frontend/src/features/tcg-analysis-review/ReviewProductFixForm.test.tsx`（付け替えとキーワード追加）。新規の ReviewFixWizard.test.tsx・ReviewRegisterProductForm.test.tsx・ChoiceCardGroup.test.tsx も同じ役を持つ（このPRで追加）。
