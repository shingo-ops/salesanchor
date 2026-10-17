<!-- rules-ack: 607cd6e7 -->
# 実装カード 便3b — 必須9項目で止められたとき、登録・保存の画面に「どの項目が足りないか」を言葉で出す（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便3bの作業指示書です。便3a（#4418、本番反映済み）で、バックエンドは足りない項目があると 422 で止め、`REQUIRED_FIELDS_MISSING:name_en,mark` のような符号を返すようになりました。今の画面は、この符号をそのまま出すか（2画面）、「入力内容を確認してください」という一般の文言しか出しません（1画面）。この便では、3つの登録画面と商品詳細の保存で、符号を「英語名、型番」のような項目名の言葉に直して出します。バックエンドは触りません。

- 設計: docs/handoff/master-register-required-fields/design.md:60-65（便2 画面：必須の印と空のときの案内）・:76-78（便3 止める）・:88（422 には足りない項目名を全部出す）。KGI と3便は PO 承認 2026-10-16「y」
- 前提の便: 便3a（#4418）が main にマージ済み（6a17d6c10）。§10 手順1 で確かめる
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）、ADR-144（UI ガバナンス。新しい部品を作らず、今ある表示の場所をそのまま使う）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（止められた理由を画面の言葉で出す。frontend だけ） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main 2d82e8784 の実物。/tmp/CC報告ファイル/master-required-fields/bin3b/recon-raw.md） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 新しい作業場所は `scripts/new-worktree.sh` で作る | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便3b の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `frontend/src/features/tcg-product-import/productDetailModel.ts`: 422 の符号を項目名の言葉に直す関数 `requiredFieldsMessage` を1つだけ足す（§4-1）
2. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx`: 新規登録と保存の 422 で、この関数の言葉を出す（§4-2）
3. `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx`: 登録の失敗で、この関数の言葉を出す（§4-3）
4. `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx`: 登録の失敗で、この関数の言葉を出す（§4-4）
5. `frontend/src/locales/ja.json`・`en.json`: 文言キー2つ（§4-5）
6. 試験（§4-6）
7. このカードを `docs/handoff/master-register-required-fields/card-bin3b.md` に置く

入れない:
- バックエンド（`backend/`）。符号の形は便3aのまま
- CSV 取り込み画面（便3a で済み。`importMessages.ts` は触らない）
- `CodeCollisionNotice.tsx`・`addExcludeWord`（除外ワードを足すだけで、空にすることは無い）
- 新しい部品・新しい CSS。今ある表示の場所（`<p role="alert">`・`pmd-error`・`Callout`）をそのまま使う
- DB・本番

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 2d82e8784。根拠の全文は /tmp/CC報告ファイル/master-required-fields/bin3b/recon-raw.md）
- 符号: 登録は `REQUIRED_FIELDS_MISSING:` ＋項目名のカンマ区切り（backend/app/services/tcg_product_master_svc.py:523）。保存は `REQUIRED_FIELDS_CLEARED:` ＋項目名（backend/app/services/tcg_product_detail_svc.py:220）。項目名は API 名で `name`, `name_en`, `mark`, `release_date`, `search_keywords`, `exclude_keywords`, `work_id`, `product_format_id`, `product_category_id`（tcg_product_master_svc.py:35-38）
- 応答は `{"detail": "REQUIRED_FIELDS_MISSING:name_en,mark"}` の形の 422。画面の `ApiError` は `message` に detail の文字列が入る（frontend/src/lib/api.ts:101-107）
- 画面A `TcgProductDetailDrawer.tsx`: 登録 :185-189・保存 :152-157 とも、422 は一律 `productDetail.invalid` を :245 の `<p role="alert">{t(error)}</p>` に出す
- 画面B `ProductMasterDrawer.tsx`: :184 で `setError(String((reason as Error)?.message || reason))`、:286 で「登録エラー: ＜符号そのまま＞」
- 画面C `ReviewRegisterProductForm.tsx`: :259-262 で `t("reviewItem.wizard.register.failed", { reason: reasonOf(error) })`（＝「登録できませんでした（REQUIRED_FIELDS_MISSING:name_en,mark）」）を :493 の `Callout` に出す
- 項目名の文言は既にある: `productDetail.japanese_title`（日本語名）・`english_title`（英語名）・`mark`（型番）・`release_date`・`search_keywords`・`exclude_keywords`・`work_id`・`product_format_id`・`product_category_id`。区切りは `reviewItem.wizard.register.listSeparator`（「、」｜「, 」）。画面B・C は既に `t(\`productDetail.${f}\`)` で項目名を出している（ProductMasterDrawer.tsx:265-272）

### 2-2. 設計の細部（Opus の技術判断）
- D1 符号を言葉に直す処理は `productDetailModel.ts` に1つだけ置く（SSOT）。3画面とも既にこのファイルを読んでいる（`missingFields` を使用）
- D2 API 名 → 文言キーの対応は `name`→`japanese_title`、`name_en`→`english_title`、ほかは同じ名前。対応表に無い名前が来たら、その名前をそのまま出す（言葉が抜けて項目が消えるのを防ぐ）
- D3 符号でない失敗（409・500・ほかの 422）は今の表示のまま変えない
- D4 文言は「登録できない／空にできない」理由と、直し方（値を入れる・存在しないときは印）の両方を書く。印を付けられるのは英語名・型番・発売日・除外ワードだけなので、そう書く

## 3. 触るファイル

1. `frontend/src/features/tcg-product-import/productDetailModel.ts`
2. `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx`
3. `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx`
4. `frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx`
5. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
6. 試験: `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx`・`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx`・`frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.test.tsx`・`frontend/src/features/tcg-product-import/productDetailModel.test.ts`（無ければ新規）
7. `docs/handoff/master-register-required-fields/card-bin3b.md`（新規）

## 4. 実装

### 4-1. `productDetailModel.ts`（ファイルの末尾に足す。import は既存の書き方に合わせる。`ApiError` は `frontend/src/lib/api.ts` から、`TFunction` は既存ファイルが使っている型に合わせる）

```ts
// ADR-1020 便3b: バックエンドが必須9項目で止めたときの符号（REQUIRED_FIELDS_MISSING:/REQUIRED_FIELDS_CLEARED:）を、画面の言葉に直す
const REQUIRED_FIELD_PREFIXES = [
  ["REQUIRED_FIELDS_MISSING:", "productDetail.requiredFieldsMissing"],
  ["REQUIRED_FIELDS_CLEARED:", "productDetail.requiredFieldsCleared"],
] as const;

// API の項目名 → 文言キー（productDetail.<key>）。載っていない名前はそのまま出す
const REQUIRED_FIELD_LABEL_KEYS: Record<string, string> = {
  name: "japanese_title",
  name_en: "english_title",
};

export function requiredFieldsMessage(err: unknown, t: TFunction): string | null {
  if (!(err instanceof ApiError) || err.status !== 422) return null;
  const code = err.message;
  for (const [prefix, key] of REQUIRED_FIELD_PREFIXES) {
    if (!code.startsWith(prefix)) continue;
    const fields = code
      .slice(prefix.length)
      .split(",")
      .filter((f) => f !== "")
      .map((f) => {
        const label = REQUIRED_FIELD_LABEL_KEYS[f] ?? f;
        const k = `productDetail.${label}`;
        const text = t(k);
        return text === k ? f : text;
      });
    return t(key, { fields: fields.join(t("reviewItem.wizard.register.listSeparator")) });
  }
  return null;
}
```

（`t(k) === k` は文言キーが無いときの i18next の戻り方。既存コードに別の判定のやり方があればそれに合わせる）

### 4-2. `TcgProductDetailDrawer.tsx`
- 今の `error` は文言キーを持つ（:245 で `t(error)`）。言葉そのものを持つ状態を1つ足す: `const [requiredError, setRequiredError] = useState<string | null>(null);`
- 保存（:146 付近）と登録（:164 付近）の始めで、今 `setError(null)` をしている所で `setRequiredError(null)` も行う
- 保存の catch（:152-157）と登録の catch（:185-189）の先頭に:

```ts
const required = requiredFieldsMessage(err, t);
if (required) {
  setBlocked(false);
  setError(null);
  setRequiredError(required);
  return;
}
```

（`return` で抜けても後片付け（`finally` の処理など）が飛ばないこと。既存が `finally` で保存中の印を戻しているならそのまま効く。`catch` の後に後片付けの行があるなら、`return` ではなく `else` で包む）
- 表示（:245 の直後）: `{requiredError && <p role="alert">{requiredError}</p>}`（新しい部品・クラスは足さない）

### 4-3. `ProductMasterDrawer.tsx`
- :184 の catch を `setError(requiredFieldsMessage(reason, t) ?? String((reason as Error)?.message || reason));` にする。:166 に同じ形の catch があり、それが `createProduct` の失敗なら同じに直す（登録以外の呼び出しなら触らない。どちらかを報告に書く）
- 表示（:286）は変えない（「登録エラー: ＜言葉＞」になる）

### 4-4. `ReviewRegisterProductForm.tsx`
- :259-262 を次にする:

```ts
} catch (error: unknown) {
  setErrorNotice(requiredFieldsMessage(error, t) ?? t("reviewItem.wizard.register.failed", { reason: reasonOf(error) }));
  return;
}
```

### 4-5. 文言（`productDetail` の中、`requiredMissingConfirmable` の直後に。ja/en 同じキー）

ja.json:
```json
"requiredFieldsMissing": "必要な項目が入っていないため登録できません：{{fields}}。値を入れてください。英語名・型番・発売日・除外キーワードは、存在しないときは「調べたが存在しない」に印を付けてください。",
"requiredFieldsCleared": "{{fields}} は空にできません。値を入れてください。英語名・型番・発売日・除外キーワードは、存在しないときは「調べたが存在しない」に印を付けてください。"
```

en.json:
```json
"requiredFieldsMissing": "Cannot register because required fields are empty: {{fields}}. Enter them. For English name, model number, release date and exclusion keywords, tick \"checked, none exists\" if there is none.",
"requiredFieldsCleared": "{{fields}} cannot be left empty. Enter a value. For English name, model number, release date and exclusion keywords, tick \"checked, none exists\" if there is none."
```

（項目の呼び名は既存の `productDetail.english_title`・`mark`・`release_date`・`exclude_keywords` の ja/en の値と同じにする。実物と違えば実物に合わせる）

### 4-6. 試験（既存の試験ファイルの書き方・モックの仕方に合わせる）

| # | ファイル | 試験 | 期待 |
|---|---|---|---|
| 1 | productDetailModel.test.ts | 422 `REQUIRED_FIELDS_MISSING:name_en,mark` | 文言キー `productDetail.requiredFieldsMissing` に、英語名と型番の言葉が区切りでつながって入る |
| 2 | 同 | 422 `REQUIRED_FIELDS_CLEARED:name` | `requiredFieldsCleared` に日本語名の言葉 |
| 3 | 同 | 対応表に無い名前 `REQUIRED_FIELDS_MISSING:foo` | `foo` がそのまま入る |
| 4 | 同 | 409 や、ほかの 422（`PRODUCT_FORMAT_INVALID`）、ApiError でない値 | `null` |
| 5 | TcgProductDetailDrawer.test.tsx | 登録で 422 `REQUIRED_FIELDS_MISSING:mark` | 画面に型番の言葉を含む alert が出る。`productDetail.invalid` の文言は出ない |
| 6 | 同 | 保存で 422 `REQUIRED_FIELDS_CLEARED:release_date` | 発売日の言葉を含む alert |
| 7 | ProductMasterDrawer.test.tsx | 登録で 422 `REQUIRED_FIELDS_MISSING:name_en` | 符号の文字列 `REQUIRED_FIELDS_MISSING` が画面に出ず、英語名の言葉が出る |
| 8 | ReviewRegisterProductForm.test.tsx | 登録で 422 `REQUIRED_FIELDS_MISSING:exclude_keywords` | 同上（除外キーワードの言葉） |

既存の試験は変えない。既存の試験が落ちたら §6。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 画面の試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/tcg-product-import/ src/features/tcg-analysis-review/ 2>&1 | tail -15` が合格

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git diff origin/main -- frontend/src | grep -nE "^\+\s*(it|test)\(" | head -20`（§4-6 の8個）

5-3. 符号を直す箇所: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git grep -n "requiredFieldsMessage" -- frontend/src | grep -v "\.test\." | head -10`（定義1つ＋画面A 2か所・B 1〜2か所・C 1か所）

5-4. 型・lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -10` と `npx eslint src/features/tcg-product-import/productDetailModel.ts src/features/tcg-product-import/TcgProductDetailDrawer.tsx src/features/tcg-analysis-review/ProductMasterDrawer.tsx src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx 2>&1 | tail -10` がエラー 0（`src/api/generated/schema.d.ts` が無くて落ちるときは、先に `npm run generate:api-types 2>&1 | tail -3`。生成物はコミットしない）

5-5. i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格

5-6. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git diff origin/main --stat | tail -20` が §3 のファイルだけ

5-7. PR の CI は担当が待たない。PR を作ったら URL を報告して終える

## 6. 分岐ごとの対処

- §10 手順1 で origin/main の `backend/app/services/tcg_product_master_svc.py` に `REQUIRED_FIELDS_MISSING` の文字が無い → BLOCKED:（便3a が入っていない）
- §2-1 の行番号やコードが実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- 既存の試験が落ちる → 落ちた試験名と原文を貼る。今回の変更で期待が変わる試験（422 で `productDetail.invalid` を期待しているのに、符号つきの 422 を使っている等）だけは、期待を新しい言葉に直し、どの行をどう直したかを報告に書く。それ以外は NEEDS_DECISION:
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 3つの登録画面で、足りない項目が符号でなく項目名の言葉で出る | 試験 5・7・8 |
| 商品詳細の保存で、空にできない項目が言葉で出る | 試験 6 |
| 符号でない失敗の表示は今のまま | 試験 4 と既存の試験が合格 |
| 文言は ja/en 同じキー・ハードコードなし | §5-5・§5-4 の eslint |
| 新しい部品・CSS を足していない | §5-6 の差分に CSS・components/ が無い |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の HEAD がマージ commit と一致すること、本番の画面 JS に `Cannot register because required fields are empty` が入っていることを読み取りで確かめる
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin3b/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（画面の表示が符号のままに戻るだけ。保存を止める判定は便3aのまま）

## 10. PR

手順1 前提が main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "REQUIRED_FIELDS_MISSING" origin/main -- backend/app/services/tcg_product_master_svc.py
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin3b --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b
    このカードを /tmp/CC報告ファイル/master-required-fields/bin3b/card-bin3b.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b/docs/handoff/master-register-required-fields/card-bin3b.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-6 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git add frontend/src/features/tcg-product-import frontend/src/features/tcg-analysis-review frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/master-register-required-fields/card-bin3b.md && git status -s | head -30
期待する出力 §3 のファイルだけが追加されている（それ以外が出たら git restore --staged で外す）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git commit -m "feat: ADR-1020便3b 必須項目で止められた理由を登録・保存の画面に項目名で出す"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && git push -q -u origin release/master-register-required-fields-bin3b && git log -1 --oneline && git log origin/release/master-register-required-fields-bin3b -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin3b && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin3b-pr-body.md）に作り、作業場所に cd してから `scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin3b --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-027・ADR-144 を書く。区分は S〜M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）、PO 2026-10-17 チャット『PRマージ、デプロイまで完走させてくれ』（本セッション＝ADR-1020 便2〜便3）」と書く。validate-pr-body.sh が「設計docに参照がない」と ADR を指摘したら、その ADR だけを `対象ADR` から外し、外したことを報告に書く
- frontend/src を変える PR なので、本文に `### GO記録` の見出しと欄を置く（中身は Opus が書く。担当は欄の雛形だけ: `- GO発行者:`・`- 日時:`・`- GO原文:`・`- 対象 HEAD:`）。validate が欄の中身を求めて落ちたら、その原文を報告して PR を作らずに終える
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。触るファイル: は実際に変えた全ファイル（`git diff origin/main --name-only` と一致させる）。削除するファイル: は既存行を変えた全ファイル（新しく作ったファイルを除く）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-6 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin3b/impl/）／§4-3 の :166 をどう扱ったか／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）に止められたら、言い換えずに報告して終える。ack の行は書かない
- Bash のコマンドに削除の SQL の語（大文字の削除文）を書かない

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
