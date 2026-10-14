<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-fix-column

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`  
**recon**: `docs/handoff/review-fix-column/recon.md`  
**前提の設計**: `docs/handoff/review-fix-wizard/design.md`（#4265、質問形式）  
**日付**: 2026-10-14  
**担当**: Planner（Opus）。設計審査は Fable（architect）、実装は Sonnet

---

## 0. PO の依頼と決定（原文）

- 依頼（2026-10-14）:「採用元は不要、この列を修正に使う列とすることは出来る？行を選択するとスライドページが出てきて、何を直しますか？など行ごとに選択が出来るようにしたい、スライドページで記入をするとデータテーブルに値が反映される、値はスライドページからしか変更が出来ず、並べているデータテーブルは値を表示するだけ、理解できる？」
- 依頼（同日）:「確認が必要な理由も要確認の商品というヘッダーの下に表示して非エンジニアでも何が原因で要確認になったのかが理解できるように記載してほしい」「確認が必要な理由という見出しも必要ない、理由だけ赤字で出ていれば理解できるので。」
- 決定（同日 PO「y」）: 案 /tmp/CC報告ファイル/review-fix-column-proposal.md のとおり。商品と状態の行から設計する。数量・価格などは後日別に判断。
- 決定（同日 PO「y」）: 要確認一覧の「ここで直す」欄（ReviewRowActions）も外し、直す操作はスライドに一本化する。

## 1. 目的（KGI）

PO が要確認ページを使うとき、次がすべて ○ になる。

- K1: スライドを開くと、見出し「要確認の商品」のすぐ下（原文・比較より上）に、理由が赤字で並ぶ。「確認が必要な理由」という見出しは無い。
- K2: スライドの比較表の列が「項目／Gemini抽出／システム最終結果／修正」になる。「採用元」は無い。仕入元詳細の比較表は今のまま「採用元」がある。
- K3: 「修正」列は、商品ID・作品の行は人が商品を決めた件（pid_basis=MANUAL）だけ、その商品名・作品名を出す。状態の行は人が状態を決めた件（condition_basis=MANUAL_CONDITION_REVIEW）だけ、その状態を出す。直せるがまだ直していない行は薄い字で「押して直す」と出る。直せない行は「—」。
- K4: 比較表の「商品ID」か「作品」の行を押すと、その行が選択色になり、表の下に「何を直しますか？」と「既存の商品に付け替える」（商品が未決定の件は「新しい商品として登録する」も）が出る。「状態」の行（状態を直せる件だけ）を押すと、状態を選ぶ欄が直接出る。直せない行は押しても何も起きない。
- K5: スライドで保存すると、スライドを閉じなくても比較表の「修正」列に値が出る。保存でその件が要確認でなくなった場合は「この商品は要確認から外れました」と出て、表は最後の内容のまま残る。
- K6: 要確認の一覧表に「ここで直す」欄が無い。一覧の行を押すとスライドが開く（今と同じ）。
- K7: 理由の下に「このままで良い」ボタンがある（確認済みにできる理由がある件だけ）。押すと今の「このままで良い」の欄が出る（送る内容は今と同じ）。
- K8（不具合修正）: 「状態を直す」の保存が通る。状態の番号（整数）で送ると保存され、UUID 形式や数字以外は 422 になる。

## 2. 変更前 → 変更後

### 変更前（recon §1〜§5）
- スライド: タイトル → 原文｜比較（4列目「採用元」）→「直す」（見出し「確認が必要な理由」＋理由＋出どころ＋「何を直しますか？」）。
- 一覧表: 最後の列「ここで直す」で商品選択と「このままで良い」ができる。
- 保存後、スライド内の表は古いまま。
- 状態の保存は API の型の誤りで必ず 422（本番の保存記録 0 件）。

### 変更後
- スライド: タイトル → 赤字の理由（＋出どころ・取りこぼし注記・「このままで良い」ボタン）→ 原文｜比較（4列目「修正」、行を押せる）→「直す」（行を選ぶまでは「直したい行を表から押してください」、選んだら行に合う質問）。
- 一覧表: 「ここで直す」列なし。表示だけ。
- 保存後、スライドは一覧の最新データから同じ件を引き直す。

## 3. 行と「直す」の対応（判定はこの表だけ）

| 比較表の行 key | 押せる条件 | 押したときの範囲（scope） | 「修正」列に出す値（条件） |
|---|---|---|---|
| productId | 常に（付け替えは常に可） | product | pid_basis が "MANUAL" のとき `system.product_title`（空なら `system.product_id`） |
| work | 常に | product | pid_basis が "MANUAL" のとき `system.work_name` |
| state | `isConditionReviewRelevant(item)` が真 | condition | condition_basis が "MANUAL_CONDITION_REVIEW" のとき状態名（Empty box は「空箱」、他は canonical のまま。今の ConditionReviewPanel と同じ表示規則） |
| それ以外（name, quantity, price, unit, memo, sourcePosition, saleStatus） | 押せない | — | 「—」 |

- 押せるが「修正」の値が無い行は、薄い字の「押して直す」を出す。
- scope ごとの選択肢（`availableFixChoices` の結果をさらに絞る）:
  - product: reassign、register（今の条件どおり）。
  - condition: condition だけ → 質問を出さず、その入力欄を直接出す。
  - keep: keep だけ（理由の下の「このままで良い」ボタンから）→ 直接出す。
- 選択肢が1つだけのときは質問を出さずに直接その入力欄、2つ以上なら「何を直しますか？」。「戻る」は質問がある場合だけ出す（今と同じ）。

## 4. backend の変更

### 4-1. 状態保存の型（K8）
- `backend/app/routers/item_corrections.py:60` `condition_id: UUID` → `condition_id: str = Field(pattern=r"^[1-9][0-9]{0,9}$")`。
- 変更前後で、ルーターからサービスへ渡す値は文字列（サービスは `backend/app/services/tcg_condition_review_svc.py:286` で int 化、`:336` で文字列比較）。ルーター内で `model_dump()` 等を使って UUID オブジェクトを文字列化している箇所があれば、文字列のまま渡す形に合わせる（実装時に該当行を確認し、変更前後をレポートに書く）。
- `request_id: UUID` は変えない（画面は crypto.randomUUID を送る。`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx` で実装時に確認）。
- 試験: `backend/tests/test_item_corrections.py:155-157` を整数文字列に変える。UUID 形式・"abc"・"0" が 422、"5" がサービスに "5" で渡ることを追加。

### 4-2. 一覧 API に condition_basis を足す（K3）
- `backend/app/services/tcg_analysis_review_svc.py` の SELECT に `ar.condition_basis` を足し、system の dict に `condition_basis` を入れる（`pid_basis` と同じ並び。`:224`・`:288` の書き方に合わせる）。
- `backend/app/routers/tcg_analysis_review.py` の SystemFields に `condition_basis: str = ""`（他の str 項目と同じ既定値の作法に合わせる）。
- 値の正本は analysis_results.condition_basis（人の判断で書く場所は `backend/app/services/tcg_condition_review_svc.py:348-359` と `backend/app/services/line_analysis_v102_svc.py:802-804` の2か所で、今と変わらない）。新しい表・列・別の保存は作らない。
- 試験: `backend/tests/test_tcg_analysis_review.py`（モック）で condition_basis がレスポンスに出ること。

## 5. frontend の変更

### 5-1. 型
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx` の AnalysisReviewItem の system に `pid_basis?: string`（未定義なら足す）と `condition_basis?: string`。

### 5-2. ItemComparison（K2・K3・K4）
- `ReadOnlyComparison` に任意 props を足す: `fixColumn?: { selectedRowKey: string | null; onRowSelect: (rowKey: string) => void; fixableRowKeys: string[] }`。
  - 無いとき（仕入元詳細）: 今と全く同じ（4列目「採用元」）。
  - あるとき（要確認スライド）: 4列目を「修正」（新キー `tcgAnalysisReview.compareColumns.fix`）に替え、値は §3 の表で決める。DataTable に `onRowClick`（fixableRowKeys に入る行だけ onRowSelect を呼ぶ）と `selectedKeys={new Set([selectedRowKey])}` を渡す。押せない行に押せる見た目が付く場合は `rowClassName` で押せる行だけに印を付け、CSS は var() のみで「押せない行の cursor を既定に戻す」（DataTable の既存クラスを確認して最小で）。
- 「修正」列の値と押せる行の判定は、新しい純関数 `fixRowsOf(item)`（ItemComparison.tsx か新ファイル `frontend/src/features/tcg-analysis-review/reviewFixRows.ts`）の1か所で決める。§3 の表をそのまま実装する。
- `ItemComparison` 本体の props に `fixColumn` を足して ReadOnlyComparison に渡す。readOnly=false 側は触らない。

### 5-3. ReviewFixWizard（scope）
- props に `scope: "product" | "condition" | "keep"` を足す。表示する選択肢は `availableFixChoices(item, ackedCodes)` を scope で絞ったもの（新しい純関数 `choicesForScope` を同じファイルに置く。判定は1か所）。
- 選択肢が1つなら最初から choice をそれにする（質問と「戻る」を出さない）。
- 呼び出し側は `key={`${item.extraction_item_id}:${scope}`}` で、行を替えると入力状態を捨てる。

### 5-4. ReviewItemDrawer（K1・K4・K7）
- 並び: Drawer（タイトル「要確認の商品」）→ 理由の欄 → 原文｜比較 →「直す」欄。
- 理由の欄（見出しなし）:
  - 理由ラベルを `<ul className="review-item-reasons">` で並べ、文字色は CSS で `var(--danger-text)`（ライト/ダーク両方定義済み。`frontend/src/index.css:53`・`:246`）。
  - gemini_gap_suspect の GapSuspectNote は今どおり理由の下に出す（色は既定）。
  - 「出どころ：…」行は今どおり出す（色は既定）。
  - 理由が無い件は今の `reviewItem.noReasons` を既定色で出す。
  - 「このままで良い」ボタン（Button 金型 variant="secondary"、文言は今の選択肢ラベル `reviewItem.wizard.choice.keep` を使う）は `choicesForScope(item, "keep", ackedCodes)` が空でないときだけ。押すと scope=keep。
  - 「確認が必要な理由」の見出し（`reviewItem.reasonsHeading`）は出さない。キーはどこからも使われなくなるなら ja/en 両方から消す。
- 比較: `fixColumn` を渡す。選択中の行 key は Drawer の state。
- 「直す」欄: 見出し「直す」。scope が null なら「直したい行を表から押してください」（新キー `reviewItem.pickRowHint`）。scope があれば ReviewFixWizard。
- 行を押す: productId/work → scope=product、state → scope=condition。同じ行をもう一度押しても選択は外さない。
- ackedCodes（確認済みにした理由）を今は ReviewFixWizard の中で持っている。ボタンの表示判定にも要るので、Drawer に持ち上げて props で渡す（持つ場所は1か所）。

### 5-5. NeedsReviewTabsPanel（K5・K6）
- `drawerItem` を `drawerItemId: string | null` と `lastDrawerItem`（最後に見た件）に替える。表示する件は `data.items.find((i) => i.extraction_item_id === drawerItemId) ?? lastDrawerItem`。見つからない（要確認から外れた・ページ外）ときは Drawer に `removedFromList` を渡し、Callout（info）で `reviewItem.removedFromList`「この商品は要確認から外れました」を表の上に出す。
- 「ここで直す」列（inline_fix、`:166-173`）を消す。
- frontend/src/features/tcg-analysis-review/ReviewRowActions.tsx と frontend/src/features/tcg-analysis-review/ReviewRowActions.test.tsx は他から使われていなければ削除。ReviewRowActions だけが使う i18n キーは ja/en 両方から削除（`git grep` で他の使用が無いことを確認してから）。

### 5-6. CSS
- 新しいトークンは作らない。色・余白は既存の var() だけ。新しいクラスは `frontend/src/features/tcg-analysis-review/review-item-drawer.css` と ItemComparison の既存 CSS に置く。
- 「押して直す」の薄い字は既存の弱い文字色トークン（例 `--text-muted` 等。実装時に index.css で実在を確認して使う）。

## 6. 文言（i18n。ja/en 同一キー、ADR-027）

| キー | ja | en |
|---|---|---|
| tcgAnalysisReview.compareColumns.fix | 修正 | Fix |
| reviewItem.fixColumn.tapToFix | 押して直す | Tap to fix |
| reviewItem.pickRowHint | 直したい行を表から押してください | Select the row you want to fix in the table |
| reviewItem.removedFromList | この商品は要確認から外れました | This item is no longer in the review list |

- 既存の `tcgAnalysisReview.compareColumns.source`（採用元）は仕入元詳細で使い続けるので消さない。

## 7. 対象と対象外

- 対象: §4・§5 のファイルと、その試験・stories。
  - backend: `backend/app/routers/item_corrections.py`、`backend/app/services/tcg_analysis_review_svc.py`、`backend/app/routers/tcg_analysis_review.py`、`backend/tests/test_item_corrections.py`、`backend/tests/test_tcg_analysis_review.py`
  - frontend: `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`、`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx`、`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`、`frontend/src/features/tcg-analysis-review/review-item-drawer.css`、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`、ReviewRowActions（削除）、ja/en、関係する test と `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.stories.tsx`
- 対象外:
  - 数量・価格・単位・備考・商品名の行を直すこと（保存の仕組みが無い。PO が後日判断）。
  - 仕入元詳細（`frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx`）の表と「商品マスタ修正」。差分ゼロ。
  - migration・deploy 設定・DB の新しい表や列。
  - 再解析（Celery）の完了待ち。理由や販売状況は再解析後に変わる（今と同じ）。「修正」列は保存と同じトランザクションで書かれる pid_basis・condition_basis を見るので、保存直後に出る。
  - ItemComparison の readOnly=false 側（使われていない）。

## 8. 代替案と選択理由

- 案A（採用）: 「修正」列の値は analysis_results の pid_basis／condition_basis（人の判断で書かれる印）と今のシステム値から出す。新しい保存場所も新しい読み方も作らない（SSOT）。backend は1列を返すだけ。
- 案B: item_corrections から人の値を一覧 API で読み出す。読み方（有効判定）が `backend/app/services/v102_human_decisions_svc.py:125-179` と状態の valid_ack の2通りあり、もう1か所に書くと食い違いの元になる。不採用。
- 案C: 比較表の行を押すと別のスライドがもう1枚出る。スライドの上にスライドを重ねると戻り方が分かりにくい。同じスライドの「直す」欄に出す。
- 案D: 一覧の「ここで直す」を残す。PO の「値はスライドページからしか変更が出来ず」と合わない（PO が y で外すと決定）。

## 9. 外部・過去事例の参照と我々への応用

- 過去事例（社内）: #4265（`docs/handoff/review-fix-wizard/design.md`）の質問形式と ChoiceCardGroup をそのまま使い、行ごとに選択肢を絞るだけにする。
- 過去事例（社内）: `docs/handoff/review-inline-edit/design.md` で一覧の行内編集を入れた。今回 PO 決定で外す。
- 外部事例: 該当なし。理由: 表の行を選んで詳細欄で編集する形は一般的な画面の作法で、数値の効果を設計の根拠にしていない。成功は §10 で直接判定する。

## 10. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1 理由が赤字で見出しなし・原文/比較より上 | `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`（「確認が必要な理由」が無い・理由のリストが比較より前・クラス名）＋Storybook png の目視 |
| K2 スライドは「修正」列・「採用元」なし／仕入元詳細は「採用元」あり | `frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx`（fixColumn あり/なし） |
| K3 「修正」列の値（§3 の表の各条件） | 純関数の表駆動試験（`fixRowsOf`） |
| K4 行を押すと選択色＋行に合う選択肢、押せない行は無反応 | `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx` |
| K4 scope ごとの選択肢・1つなら質問なし | `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx` |
| K5 保存後に同じ件を一覧から引き直す・外れたら案内 | `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx` |
| K6 一覧に「ここで直す」が無い | `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx` |
| K7 「このままで良い」の送信 body・回数が今と同じ | `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx` |
| K8 状態保存: "5" は通る・UUID/"abc"/"0" は 422 | `backend/tests/test_item_corrections.py` |
| condition_basis がレスポンスに出る | `backend/tests/test_tcg_analysis_review.py` |
| 文言は t() 経由・ja/en 同一キー・色/px 直値なし・新金型なし | CI 全件 pass |
| 既存の試験が通る | vitest（`--no-file-parallelism`）・tsc・eslint・backend pytest（該当ファイル） |
| 本番反映 | デプロイ成功、本番 JS に「押して直す」が含まれる |

## 11. リスクと対処

- 状態保存の修正で、今まで 422 だった保存が実際に通るようになる（本番に初めて condition_review 行が入る）→ 保存処理（`backend/app/services/tcg_condition_review_svc.py:283-367`）は試験済みの既存処理で、今回変えない。保存されるのは人が選んだ時だけ。
- pid_basis=MANUAL は過去の一括修正（2026-09 の 371 件）でも付いている → それも人の決定なので「修正」列に出るのが正しい。
- 一覧のページ外に件が移るとスライドに案内が出る → 表は最後の内容を残すので操作は失われない。
- 一覧の「ここで直す」を消すと一覧からの素早い付け替えができなくなる → PO 決定（y）。

## 12. 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | backend 4-1・4-2 と試験 | Generator（Sonnet） |
| 2 | fixRowsOf・ItemComparison の fixColumn | Generator（Sonnet） |
| 3 | ReviewFixWizard の scope、ReviewItemDrawer の並び替え・ackedCodes 持ち上げ | Generator（Sonnet） |
| 4 | NeedsReviewTabsPanel（drawerItemId・ここで直す削除）、ReviewRowActions 削除、i18n | Generator（Sonnet） |
| 5 | 試験・stories・tsc・vitest・eslint・pytest、Storybook 撮影 | Generator（Sonnet） |
| 6 | コード審査 | Fable（reviewer） |
| 7 | PR・GO（ADR-1003 委譲）・マージ・デプロイ確認 | Opus |

## 13. 戻し方・測り方

- 戻し方: マージコミットを `git revert -m 1` する PR を出す。DB の変更は無い。K8 で保存された condition_review 行は正規の保存 API で入った人の判断として残る。
- 測り方: §10 の試験と Storybook png。本番はデプロイ後 JS に「押して直す」があることを確認。本番画面での実操作（行を押して保存し「修正」列に出る）は PO の目視（未確認として報告）。

## 維持の仕組み

- 行と「直す」の対応・「修正」列の値は `fixRowsOf` の1か所、scope ごとの選択肢は `choicesForScope` の1か所で決める。
- 「修正」列の値は analysis_results の印（pid_basis・condition_basis）から読み、別の保存場所を作らない。
- 守り手: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`、`frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx`、`frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx`、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`、`backend/tests/test_item_corrections.py`、`backend/tests/test_tcg_analysis_review.py`

## 14. 設計審査（Fable）REVISE への対応で確定した点

審査記録: Fable architect 2026-10-14 判定 REVISE（recon の行番号は全件一致・方向は承認、未記載7点）。本節は §3〜§7 に優先する。

- A. ackedCodes は ReviewItemDrawer が持つ。ReviewFixWizard の props は `{ item, scope, ackedCodes, onAcked, onRefresh }`。`onAcked(codes)` は Drawer の ackedCodes に足す（今の `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:54,88` の setAckedCodes を移す）。
- B. 単一選択肢の扱い: Wizard 内の state `choice` は今どおり null 始まり。表示する choice は `choice ?? (choices.length === 1 ? choices[0] : null)` で導出する（保存後 `handleSaved` が `setChoice(null)` しても単一選択肢の入力欄が出続ける）。
- C. 既存試験の期待値変更（#4265 の K1「開くとすぐ質問」を本設計の K4 で置き換える）:
  - `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx`: scope を渡す形に全件書き換え（product は2択、condition/keep は質問なしで直接入力欄、choices 0 件は nothingToFix）。
  - `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`: ItemComparison のモックをやめて実物を使う（行を押す試験のため）。開いた直後は pickRowHint が出て質問は出ない。
  - `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`: 開いた直後に質問が出る前提の箇所は「行を押す／このままで良いボタンを押す」操作を挟む形に直す。
- D. 削除対象に追加: frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.inline.test.tsx（「ここで直す」列の試験）、frontend/src/features/tcg-analysis-review/review-row-actions.css、`frontend/src/tokens.css` の `--review-inline-fix-col-w` の行（使用は NeedsReviewTabsPanel.tsx:24 のみ。消す前に git grep で他使用ゼロを確認）。
- E. i18n の削除は `needsReview.inline.header`・`needsReview.inline.saved`・`needsReview.inline.error`・`needsReview.inline.unknownError`・`needsReview.inline.ackAria` の5キーに限る（各キーを git grep して ReviewRowActions 以外の使用ゼロを確認してから）。`needsReview.inline.productAria/productPlaceholder/noResults/searchError` は ReviewProductFixForm・ReviewRegisterProductForm が使うので残す。`reviewItem.reasonsHeading` も他使用ゼロを確認してから削除。
- F. DataTable 金型は変えない。onRowClick を渡すと全行に clickable クラスと tabIndex=0 が付く（`frontend/src/components/DataTable.tsx:244,254`）。押せない行は `rowClassName` で `item-comparison__row--static` を付け、CSS で `cursor: default` に戻す。キーボードの焦点は押せない行にも残るが、Enter を押しても何も起きない（許容。onRowClick 内で fixableRowKeys に無い行は無視）。selectedKeys は `selectedRowKey ? new Set([selectedRowKey]) : undefined`。
- G. `backend/app/routers/item_corrections.py:145` の `model_dump(mode="json")` は変更不要（str はそのまま、request_id は文字列化され今と同じ）。「修正」列の条件に `MANUAL_RAW_REVIEW:PO_RULES` は含めない（§3 の2値だけ）。`backend/tests/test_tcg_analysis_review.py:137-139` の system キー列挙に condition_basis を足す。
- 未解決1（長い商品名）: 「修正」列は幅指定なしの `ComparisonCell`（Gemini・システム列と同じく幅に追従し、はみ出しは省略、title で全文）。`--comparison-source-col-w` は仕入元詳細の「採用元」で使い続けるので残す。
- 未解決2（押せない行の焦点）: F のとおり許容。
- 未解決3（keep を使い切った後）: Drawer は onAcked のあと `choicesForScope(item, "keep", ackedCodes)` が空なら scope を null に戻し、pickRowHint を出す（ボタンも消える）。
- 再審査（Fable 2026-10-14）APPROVE。付帯指示（Opus 採用）: keep を使い切って scope を null に戻すとき、「確認済みにしました」の通知（`reviewItem.acked` 系の既存文言）は Drawer が state に持ち、理由の欄の直下に Callout(info) で出す。次に行を押す等の操作で消す。Wizard 側の通知は scope が続く場合だけ使う。`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx:59-66` の送信 body・回数・GET 2 回の期待は変えない。
