# card: 便2-2c2b 直し1 会社情報の画面の国の欄に「*」の印を付ける（ADR-1061）

- 状態: PO 2026-11-27「1」（「*」の印を付ける直しを準備する。作るのはクラウドの係）。元の設計は PO 承認済み（2026-11-12「1」。design.md §3-4a）。
- きっかけ: 2026-11-26 に本番の会社情報の画面を Chrome で確かめた。国の欄は入れないと保存できない（design.md :169 country_code 必須・画面も `required`）。ところが会社名・市区町村・番地・通りには「*」があり、国の欄だけ無い。保存を押すまで必須だと分からなかった。
- 設計: docs/handoff/viewer-contract-stage/design.md §3-4a（画面は金型だけで作る）。
- 担当: クラウドの Sonnet。§1 の3ファイルだけを直す。本番・secrets・DB には触らない。PR は作らない（Opus が作る）。
- 基準: origin/main `24354620e`。行番号がずれていたら「変更前」の文字列で場所を探す。件数が §0-3 と合わなければ BLOCKED。
- 危険便か: いいえ（migrations/・deploy.yml・本番 scripts/ に触らない）。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと

- D1 印は金型の側で出す。国の欄の金型（frontend/src/components/CountryCombobox.tsx）に、省ける `label` と `error` を足す。描き方は TextField（frontend/src/components/TextField.tsx:83〜:105）と同じ形にする（`comp-field`・`comp-field__label`・`required` のとき `comp-field__required` の「*」・`comp-field__hint comp-field__hint--error` と `role="alert"`）。画面のファイルで「*」を手で書かない（PO 2026-11-12「金型登録のないハードコードを禁止」）。
- D2 `label` も `error` も渡さないときは、今の描き方（:89 の `return (` の中・:90 の外側の div から）を1文字も変えない。この金型を使うほかの4ファイル（DutyRuleFormModal・LeadEditPage・LeadFormFields・LeadsPage）は触らないし、見た目も変わらない。登録の画面（RegisterPage・RegisterAddressPage・RegisterChangeBillingPage）は別の部品 pages/register/CountryCombobox.tsx を使うので対象外。
- D3 `label` か `error` を渡したときは、外側を `<div className="comp-field comp-field--full">` で包み、その中に ①ラベル ②今の描き方（ref の付いた div。外側クリックで閉じる仕組みはこの div のまま） ③理由の行 の順で並べる。
- D4 会社情報の画面（frontend/src/pages/admin/IssuerProfileSection.tsx:177〜:187）は、手書きの `<div className="form-group">`・`<label>`・`<div className="error-message">` をやめ、金型に `label={t("issuerProfile.country")}` と `error={fieldError("country_code")}` を渡す。国の欄の理由の出方が、ほかの欄（赤い字で欄の下）と同じになる。
- D5 新しい文は足さない。ja.json・en.json は触らない（`issuerProfile.country` は既にある）。

## 0. カード発行前チェック

| # | 確かめたこと | 結果 |
|---|---|---|
| 1 | 設計の節（§3-4a）と PO の答えを指している | ○ |
| 2 | 触るファイルを §1 に全部並べた（3） | ○ |
| 3 | 直すファイルの「変更前」の文字列を 24354620e で数えた（§0-3） | ○ |
| 4 | 危険パス（migrations/・deploy.yml・本番 scripts/）を含まない | ○ |
| 5 | 対象外（ほかの呼び出し元4ファイル・登録の画面の別部品・backend・文の追加）を書いた | ○ |
| 6 | 画面の文字はすべて t()。新しいキーは無い | ○ |
| 7 | 部品は金型だけ。色の直書き・画面での手書きの「*」なし | ○ |
| 8 | 試験のコマンドは今のリポジトリにある（vitest・tsc・check:all） | ○ |
| 9 | 停止の条件を §4 に書いた | ○ |
| 10 | 報告の形を §5 に書いた | ○ |

## 0-2. 読んだ節

- docs/ai-agents/executor-checklist.md の 00-common・03-file・10-executor。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1手順1コマンド・出力に上限・プレースホルダなし・commit と push は git log で確かめる）・11-lint.md。照合: 手順はすべて `cd` で始まる（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`sleep` なし。

## 受領確認

最初の返事の1行目と2行目に次を書く。

```
RECEIVED viewer-contract-bin2-2c2b-fix1 HEAD=（git rev-parse HEAD の40文字）
本報告はカード 便2-2c2b 直し1 会社情報の画面の国の欄に「*」の印を付ける の実行結果である
```

## 0-3. 実装前点検

手順2で数える。1つでも違えば停止する（BLOCKED）。

| # | ファイル | 数える文字列 | 期待 |
|---|---|---|---|
| P1 | frontend/src/components/CountryCombobox.test.tsx | ファイルがある | 無い |
| P2 | frontend/src/components/CountryCombobox.tsx | 行数（wc -l） | 207 |
| P3 | frontend/src/components/CountryCombobox.tsx | `  required?: boolean;` | 1 |
| P4 | frontend/src/components/CountryCombobox.tsx | `ref={ref} style={{ position: "relative" }}` | 1 |
| P5 | frontend/src/components/CountryCombobox.tsx | `label?:` を含む行 | 0 |
| P6 | frontend/src/pages/admin/IssuerProfileSection.tsx | `issuerProfile.country")}</label>` | 1 |
| P7 | frontend/src/pages/admin/IssuerProfileSection.tsx | `className="error-message">{fieldError("country_code")}` | 1 |
| P8 | frontend/src の .tsx（stories と試験を除く） | `components/CountryCombobox"` を読み込むファイル | 5 |

## 1. 触るファイル

| ファイル | 種類 | 何をするか |
|---|---|---|
| frontend/src/components/CountryCombobox.tsx | 直す | D1〜D3 |
| frontend/src/pages/admin/IssuerProfileSection.tsx | 直す | D4 |
| frontend/src/components/CountryCombobox.test.tsx | 新規 | §2-3 の試験 |

ほかのファイルは触らない。

## 2. 変更

### 2-1. CountryCombobox.tsx

変更前（:14〜:22 と :24〜:32）:

```tsx
interface CountryComboboxProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onCommit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
}

export function CountryCombobox({
  id,
  value,
  onChange,
  onCommit,
  placeholder,
  disabled = false,
  required = false,
}: CountryComboboxProps) {
```

変更後:

```tsx
interface CountryComboboxProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onCommit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  /** 渡すと TextField と同じラベルを出す。required のとき「*」を付ける */
  label?: string;
  /** 渡すと TextField と同じ赤い理由の行を欄の下に出す */
  error?: string;
}

export function CountryCombobox({
  id,
  value,
  onChange,
  onCommit,
  placeholder,
  disabled = false,
  required = false,
  label,
  error,
}: CountryComboboxProps) {
```

:89 の `return (` から :206 の `);` までは、`return` を `const combobox =` に変えるだけで、かっこの中身は1文字も変えない。そのすぐ後（関数を閉じる `}` の前）に次を足す。

```tsx
  if (label == null && error == null) return combobox;

  return (
    <div className={`comp-field comp-field--full${error != null ? " comp-field--error" : ""}`}>
      {label != null && (
        <label htmlFor={id} className="comp-field__label">
          {label}
          {required && (
            <span className="comp-field__required" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {combobox}
      {error != null && (
        <p className="comp-field__hint comp-field__hint--error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
```

### 2-2. IssuerProfileSection.tsx

変更前（:177〜:187）:

```tsx
            <div className="form-group">
              <label htmlFor={`${idp}-country`}>{t("issuerProfile.country")}</label>
              <CountryCombobox
                id={`${idp}-country`}
                value={current.country_code}
                onChange={(value) => update("country_code", value)}
                disabled={locked}
                required
              />
              {fieldError("country_code") && <div className="error-message">{fieldError("country_code")}</div>}
            </div>
```

変更後:

```tsx
            <CountryCombobox
              id={`${idp}-country`}
              label={t("issuerProfile.country")}
              value={current.country_code}
              onChange={(value) => update("country_code", value)}
              error={fieldError("country_code")}
              disabled={locked}
              required
            />
```

`fieldError` は理由の無いとき `undefined` を返す（IssuerProfileSection.tsx:67〜:70 `(key: keyof RegionForm): string | undefined`。Opus が 24354620e で確かめた）。

### 2-3. CountryCombobox.test.tsx（新規）

`vi.mock("../lib/api", ...)` で `api.get` が国2件（JP・US）を返すようにする。次の4つを確かめる。

| # | 渡すもの | 期待 |
|---|---|---|
| T1 | `label="Country"`・`required` | ラベル「Country」があり、その中に「*」（class `comp-field__required`）が1つ。`getByLabelText(/^Country\*?$/)` で入力欄が取れる（ラベルの文字は「*」を含めて「Country*」になるため。前例 frontend/src/pages/viewer/Password.test.tsx:24） |
| T2 | `label="Country"`（required なし） | ラベルはあるが「*」は0 |
| T3 | `label` も `error` も無し | `container.querySelector(".comp-field")` が null・`label` 要素が0（今の描き方のまま） |
| T4 | `label="Country"`・`error="Required"` | `role="alert"` に「Required」が1つ |

## 3. 手順

1. 場所を作る。

```
cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2c2b-fix1 && git log --oneline -1 | tail -1
cd ~/sa && git merge-base --is-ancestor 24354620e HEAD; echo "is-ancestor exit=$?"
```

期待: `is-ancestor exit=0`。

2. 点検する（§0-3）。

```
cd ~/sa && git rev-parse HEAD
cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2c2b-fix1.md
cd ~/sa && ls frontend/src/components/CountryCombobox.test.tsx; echo "ls exit=$?"
cd ~/sa && wc -l frontend/src/components/CountryCombobox.tsx
cd ~/sa && grep -c '  required?: boolean;' frontend/src/components/CountryCombobox.tsx
cd ~/sa && grep -c 'ref={ref} style={{ position: "relative" }}' frontend/src/components/CountryCombobox.tsx
cd ~/sa && grep -c 'label?:' frontend/src/components/CountryCombobox.tsx
cd ~/sa && grep -c 'issuerProfile.country")}</label>' frontend/src/pages/admin/IssuerProfileSection.tsx
cd ~/sa && grep -c 'className="error-message">{fieldError("country_code")}' frontend/src/pages/admin/IssuerProfileSection.tsx
cd ~/sa && grep -rln 'components/CountryCombobox"' frontend/src --include='*.tsx' | grep -v stories | grep -vc test
```

期待: `ls exit=1`・207・1・1・0・1・1・5。

3. §2 を当てる。新規ファイルは Write、それ以外は Edit。1か所ずつ。

4. 画面の検査。

```
cd ~/sa/frontend && node --version && npm --version
cd ~/sa/frontend && npm ci 2>&1 | tail -3
cd ~/sa/frontend && npx tsc --noEmit -p . 2>&1 | tail -15
cd ~/sa/frontend && npm run test:unit -- src/components/CountryCombobox.test.tsx src/lib/query/batch3fPages.test.tsx src/pages/admin/issuerProfileForm.test.ts src/pages/register/CountryCombobox.test.tsx 2>&1 | tail -15
cd ~/sa/frontend && npm run check:all 2>&1 | tail -30
```

期待: tsc の出力なし。vitest は failed 0。check:all は終了コード 0。

5. 確かめる。

```
cd ~/sa && git status --short | tail -10
cd ~/sa && git diff | tail -150
```

期待: 変わったファイルは §1 の3つだけ。

6. 記録して送る（shingo-cc 名義）。

```
cd ~/sa && git add frontend/src/components/CountryCombobox.tsx frontend/src/components/CountryCombobox.test.tsx frontend/src/pages/admin/IssuerProfileSection.tsx
cd ~/sa && git -c user.name=shingo-cc -c user.email=shingo-cc@users.noreply.github.com commit -m "fix(frontend): show required mark on issuer country field via CountryCombobox label (ADR-1061 bin2-2c2b fix1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd ~/sa && git push origin release/viewer-contract-bin2-2c2b-fix1 2>&1 | tail -3
cd ~/sa && git log --oneline -2 | tail -2
```

## 4. 想定される分かれ道

次のときは、そこで停止して BLOCKED と報告する（直さない・言い換えない）。

- 手順1の is-ancestor が 0 でない。
- §0-3 の数が1つでも違う。
- §2 の「変更前」の文字列が見つからない、または2か所以上に当たる。
- tsc が何か出す。
- vitest に failed がある。
- check:all が 0 以外で終わる（どの検査が何を言ったかを生のまま報告する）。
- 直すために §1 の外のファイルを触る必要がある。
- push が失敗する。

直してよいのは、このカードの写し間違い（字下げ・閉じかっこ・カンマの抜け）だけ。直したら、どこをどう直したかを報告に書く。試験の skipped は止めずに数を書く。

## 5. 報告の形

最後の返事に、受領確認の2行、手順ごとの tail の生出力、手順5の diff の全文、停止したときは「どの手順で・何が出たか・何をしなかったか」の3点を書く。最後の行は `DONE` か `BLOCKED: 理由` のどちらか。

## 6. 受入

| 基準 | 検証方法 |
|---|---|
| 会社情報の画面の国の欄のラベルに「*」がある | Opus が本番で Chrome の画面を見る（国内用・海外用の両方） |
| 国の欄の理由が、ほかの欄と同じく赤い字で欄の下に出る | T4 の試験 |
| ほかの4ファイルの国の欄は変わらない | T3 の試験と、手順5で変わったファイルが3つだけ |
| 文字は t() だけ・色の直書きなし | check:all（i18n・デザイントークンの検査）が通る |

## 7. 委任の定型

- sleep・ヒアドキュメントは使わない。PR は作らない。
- 見張り（hook）に止められたら、言い換えずに止められた文をそのまま報告する。
- §1 にないファイルは直さない。

END OF CARD
