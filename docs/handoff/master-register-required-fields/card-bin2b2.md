<!-- rules-ack: 607cd6e7 -->
# 実装カード 便2b-2 — 細分類マスタ画面で「使えるゲーム」を選べるようにする（ADR-1020）

> この文書は何か：共用商品マスタの9項目必須化（ADR-1020）の便2b-2（画面だけ）の作業指示書です。解析ルール画面の「細分類」マスタ（`ProductFormatsMasterPanel.tsx`）に、①その細分類を使えるゲームを複数選ぶ欄、②一覧の「使えるゲーム」列、③保存時に使えるゲームを丸ごと置き換える呼び出し（便2aの `PUT /super-admin/product-formats/{format_id}/games`）、④外せない・見つからないときの分かる文言、を足します。商品詳細側（便2b-1）は済み。解析レビューからの登録は便2b-3、CSV は便2c、保存の停止は便3。

- 設計: docs/handoff/master-register-required-fields/design.md:50・:65（細分類マスタ画面に「使えるゲーム」の編集を足す）・§7（KGI と3便は PO 承認 2026-10-16「y」）
- 前提の便: 便2a（#4412）が main にマージ済み・本番反映済み（2026-10-17 02:11 JST、deploy run 38937760981）。§10 手順1 で確かめる
- 対象ADR: ADR-1020（本テーマ）、ADR-027（i18n。文言は `t()` だけ・ja/en 同じキー）、ADR-144（金型。`MultiSelect`・`Callout` を使い、生の input/select・色の直値・新しい `style=` を書かない）
- 状態: 設計は Opus 自己審査 APPROVE。§2-2 の細部は Opus の技術判断（設計の目的・範囲は変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（細分類マスタ画面だけ） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行番号は origin/main 5f3cca95b の実物） |
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

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便2b-2 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx`: 使えるゲームの欄・一覧の列・保存の流れ・エラー文言（§4-1）
2. `frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `productFormatsMaster` に 7 キー（§4-2）
3. `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx`（新規）: 試験 6 本（§4-3）
4. このカードを `docs/handoff/master-register-required-fields/card-bin2b2.md` に置く

入れない:
- 既存の「Card Game（`type_master_id`）」の単一選択欄・列の変更（そのまま残す）
- 既存の `style=`（237行・252行・277行・291行）の書き換え
- バックエンド、`frontend/api-contract/openapi.json`、商品詳細（便2b-1）、解析レビュー（便2b-3）、CSV（便2c）

## 2. 前提の事実と設計の細部

### 2-1. 事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | 一覧 `GET /super-admin/product-formats` と PATCH・PUT の応答は `game_ids: list[int]` を返す。POST（新規）の応答は `id` を持つが `game_ids` は空配列（紐づけはまだ無いため） | `backend/app/routers/super_admin_product_formats.py:74-76`・`:108`・`:143-144`、`backend/app/schemas/product_format.py:36-42` |
| F2 | `PUT /super-admin/product-formats/{format_id}/games` は `{"game_ids": [int, ...]}`（最大200・余計なキー禁止）を受け、紐づけを丸ごと置き換える。無効・存在しないゲームを含むと 422 `PRODUCT_FORMAT_GAME_UNKNOWN`、外す組を商品が使っていれば 409 `PRODUCT_FORMAT_GAME_IN_USE` | 同 `:147-203`、`product_format.py:45-50` |
| F3 | `api` は失敗時に `ApiError`（`status` と、`detail` が文字列ならその文字列を `message`）を投げる | `frontend/src/lib/api.ts:12-24`・`:99-107` |
| F4 | ゲームの選択肢は、パネルが既に取っている `GET /super-admin/tcg/types`（無効も含む・`is_active` あり）を使う。本番は 14 件すべて有効、紐づけ 69 行はすべて有効なゲーム | `backend/app/routers/super_admin_tcg.py:40`・`:154-170`、本番の読み取り（2026-10-17 02:24 JST、`t|14|69`） |
| F5 | 金型 `MultiSelect` は `label`・`options`（`value`/`label`）・`selected`・`onChange`・`clearLabel`・`allLabel`（0件の表示）・`countLabel`・`testId` を受ける。ボタン `${testId}-button`、選択肢 `${testId}-option-${value}` | `frontend/src/components/MultiSelect.tsx:1-48` |
| F6 | 金型 `Callout` は `variant="warning"` で `role="alert"`、`title` と本文を受ける | `frontend/src/components/Callout.tsx:1-34` |
| F7 | パネルの今のエラー表示は表の上の `<p role="alert">`（211行）だけで、ドロワーを開いている間は見えにくい。保存は `submit`（133-158行） | `ProductFormatsMasterPanel.tsx` |
| F8 | このパネルを使うのは `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` だけ。パネルの試験は無い | `git grep -ln ProductFormatsMasterPanel` |

### 2-2. 設計の細部（Opus の技術判断）

- D1 選択肢は `is_active` のゲームと、今選ばれているゲーム（無効になったもの）。並びは API の順（`sort_order, id`）
- D2 新規: POST → 応答の `id` を `setEditId` → 選んだゲームが1件以上なら PUT。PUT が失敗したら、ドロワーは開いたまま・編集の状態（以後の保存は PATCH）でエラーを出し、一覧を読み直す（細分類だけ作られてゲームが空、の状態を利用者に見せる）
- D3 編集: PATCH → 選んだゲームが開いたときと違うときだけ PUT（比較は並べ替えた文字列の配列）。送る `game_ids` は数の昇順
- D4 409 `PRODUCT_FORMAT_GAME_IN_USE` と 422 `PRODUCT_FORMAT_GAME_UNKNOWN` は `t()` の文言に置き換える。他は今のとおり `message`
- D5 エラーはドロワーを開いている間はドロワーの中の `Callout`（warning）で出し、閉じているときは今の `<p role="alert">` で出す（同時に2つ出さない）
- D6 一覧の列「使えるゲーム」はゲーム名（`name_ja`）を `, ` でつなぐ。0件は `-`（既存の列と同じ）

## 3. 触るファイル

1. `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx`
2. `frontend/src/locales/ja.json`
3. `frontend/src/locales/en.json`
4. `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx`（新規）
5. `docs/handoff/master-register-required-fields/card-bin2b2.md`（このカード）

## 4. 実装

### 4-1. `ProductFormatsMasterPanel.tsx`

(a) import: 9行目を `import { api, ApiError } from "../../../lib/api";` にする。`import ConfirmModal ...` の直後に2行足す:

```ts
import { MultiSelect } from "../../../components/MultiSelect";
import { Callout } from "../../../components/Callout";
```

(b) `interface TcgType` に `is_active: boolean;` を、`interface ProductFormat` に `game_ids: number[];` を足す。`FormatFormState` に `game_ids: string[];` を、`emptyForm` に `game_ids: [],` を足す。

(c) `const [confirmDeleteId, ...]` の直後に足す:

```ts
  // ADR-1020: 開いたときの「使えるゲーム」（変わったときだけ PUT するため）
  const [savedGameIds, setSavedGameIds] = useState<string[]>([]);
```

(d) `openCreate` を `const openCreate = () => { setEditId(null); setForm(emptyForm); setSavedGameIds([]); setError(""); setShowForm(true); };` にする。`openEdit` の `setForm({...})` に `game_ids: item.game_ids.map(String),` を足し、`setForm` の直後に `setSavedGameIds(item.game_ids.map(String).sort());` と `setError("");` を足す。

(e) `submit` を次に置き換え、直前に `errorMessage` を足す:

```ts
  // ADR-1020: 使えるゲームの置き換えで返る理由を、分かる文言にする
  const errorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError && err.status === 409 && err.message === "PRODUCT_FORMAT_GAME_IN_USE") return t(`${f}.gamesInUse`);
    if (err instanceof ApiError && err.status === 422 && err.message === "PRODUCT_FORMAT_GAME_UNKNOWN") return t(`${f}.gamesUnknown`);
    return err instanceof Error ? err.message : fallback;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const payload = {
      code: form.code,
      name: form.name,
      name_en: form.name_en || null,
      line_id: form.line_id,
      type_master_id: form.type_master_id,
      display_order: form.display_order,
      is_active: form.is_active,
    };
    const wanted = [...form.game_ids].sort();
    let targetId = editId;
    try {
      if (targetId) {
        await api.patch(`/super-admin/product-formats/${targetId}`, payload);
      } else {
        const created = await api.post<ProductFormat>("/super-admin/product-formats", payload);
        targetId = created.id;
        setEditId(created.id);
        setSavedGameIds([]);
      }
      const before = editId ? savedGameIds : [];
      if (wanted.join(",") !== before.join(",")) {
        await api.put(`/super-admin/product-formats/${targetId}/games`, {
          game_ids: wanted.map(Number).sort((a, b) => a - b),
        });
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditId(null);
      setSavedGameIds([]);
      await load();
    } catch (err) {
      setError(errorMessage(err, t("common.saveError")));
      await load();
    }
  };
```

(f) `getGameName` の直後に足す:

```ts
  const getGameNames = (ids: number[]) => ids.length === 0 ? "-" : ids.map(id => getGameName(id)).join(", ");
  const gameOptions = tcgTypes
    .filter(g => g.is_active || form.game_ids.includes(String(g.id)))
    .map(g => ({ value: String(g.id), label: g.name_ja }));
```

(g) `columns` の `type_master_id` の行の直後に1行足す:

```ts
    { key: "game_ids", header: t(`${f}.gameIds`), renderCell: row => getGameNames(row.game_ids) },
```

(h) 211行を `{error && !showForm && <p role="alert">{error}</p>}` にする。

(i) `<form ref={formRef} ...>` の直後（grid の `div` の前）に足す:

```tsx
          {error && <Callout variant="warning" title={t(`${f}.saveFailed`)}>{error}</Callout>}
```

(j) grid の中、Card Game（`typeMasterId`）の `div className="form-group"` の直後に足す（新しい `style=` は書かない）:

```tsx
            <div className="form-group">
              <MultiSelect
                label={t(`${f}.gameIds`)}
                options={gameOptions}
                selected={form.game_ids}
                onChange={next => setForm({ ...form, game_ids: next })}
                clearLabel={t(`${f}.gamesClear`)}
                allLabel={t(`${f}.gamesNone`)}
                countLabel={n => t(`${f}.gamesCount`, { n })}
                testId="product-format-games"
              />
            </div>
```

### 4-2. 文言（`productFormatsMaster` の中、`"isActive"` の後に足す。ja と en で同じキー）

| キー | ja | en |
|---|---|---|
| `gameIds` | 使えるゲーム | Usable games |
| `gamesNone` | 未設定 | None |
| `gamesClear` | 選択をクリア | Clear selection |
| `gamesCount` | {{n}}件のゲーム | {{n}} games |
| `gamesInUse` | この細分類を使っている商品があるため、そのゲームは外せません。先に商品の細分類か作品を直してください。 | Products with this sub-category use that game, so it cannot be removed. Change those products first. |
| `gamesUnknown` | 選んだゲームが見つからないか、使われていません。読み込み直してから選んでください。 | A selected game was not found or is inactive. Reload and choose again. |
| `saveFailed` | 保存できませんでした | Could not save |

ハードコードの日本語を tsx に書かない。

### 4-3. 試験（`ProductFormatsMasterPanel.test.tsx`、新規）

- 手本: `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.test.tsx`（`vi.mock("../../../lib/api", ...)`・`beforeEach` で `i18n.changeLanguage("en")`・`afterEach(cleanup)`）
- `vi.mock` の `ApiError` は `class ApiError extends Error { status: number; responseDetail: unknown; constructor(message: string, status: number, detail?: unknown) { super(message); this.status = status; this.responseDetail = detail; } }` とし、試験の中で `new ApiError("PRODUCT_FORMAT_GAME_IN_USE", 409)` のように使う。`api` は `get`・`post`・`patch`・`put`・`delete` を `vi.fn()`
- `api.get` は path で返し分ける: `/super-admin/product-formats` → 細分類 1 件（`id: 7, code: "BOX", name: "Booster Box", name_en: null, line_id: null, type_master_id: null, display_order: 100, is_active: true, created_at, updated_at, game_ids: [1, 2]`）、`/super-admin/product-lines` → `[]`、`/super-admin/tcg/types` → `[{ id: 1, code: "pokemon", name_ja: "Pokemon", name_en: null, is_active: true }, { id: 2, code: "onepiece", name_ja: "One Piece", name_en: null, is_active: true }, { id: 3, code: "old", name_ja: "Old Game", name_en: null, is_active: false }]`
- 編集は行のクリック（`fireEvent.click(await screen.findByText("Booster Box"))`）で開く。保存はフッターの `Update`／`Create` ボタンのクリック。jsdom で `requestSubmit` が動かなければ `fireEvent.submit(form 要素)` で代える（報告に書く）
- ゲームの選択は `fireEvent.click(screen.getByTestId("product-format-games-button"))` → `fireEvent.click(screen.getByTestId("product-format-games-option-1"))`

| # | 名前 | 中身 |
|---|---|---|
| 1 | `lists usable games for each format` | 描画後、`Pokemon, One Piece` の文が出る |
| 2 | `does not offer inactive games` | 新規で開き、ゲームの欄を開く → `product-format-games-option-3` が無い |
| 3 | `creates a format and then replaces its games` | 新規で code・name を入れ、ゲーム 1 を選び Create → `api.post` が 1 回、その後 `api.put` が `("/super-admin/product-formats/50/games", { game_ids: [1] })`（`api.post` は `{ id: 50, ..., game_ids: [] }` を返す） |
| 4 | `skips the games call when games are unchanged` | 編集で開き、name を変えて Update → `api.patch` が 1 回、`api.put` は 0 回 |
| 5 | `sends sorted game ids when games change` | 編集で開き、ゲーム 1 を外して Update → `api.put` が `("/super-admin/product-formats/7/games", { game_ids: [2] })` |
| 6 | `keeps the drawer open and explains a game in use` | 編集で開き、ゲーム 2 を外す。`api.put` が `new ApiError("PRODUCT_FORMAT_GAME_IN_USE", 409)` で失敗 → `role="alert"` の中に `Products with this sub-category use that game` を含む文が出て、`Update` ボタンがまだある（ドロワーが開いたまま）。一覧の読み直し（`api.get` の `/super-admin/product-formats`）が 2 回以上 |

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 型と lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20` と `npx eslint src/pages/super-admin/components/ProductFormatsMasterPanel.tsx src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx 2>&1 | tail -20` がどちらもエラー 0。

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && grep -nE "^\s*it\(" frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx | wc -l` と `grep -nE "^\s*it\(" frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx | head -10` の出力（6 本、名前が §4-3 の表のとおり）。

5-3. 試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx 2>&1 | tail -30` が全部合格。

5-4. 金型と i18n: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` が合格。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git diff origin/main -- frontend/src/pages | grep -nE "^\+.*(<input|<select|#[0-9a-fA-F]{3,6}\b|style=)" | head -10` が 0 行。`git diff origin/main -- frontend/src/pages | grep -nP "^\+(?!.*//).*[\x{3040}-\x{30ff}\x{4e00}-\x{9fff}]" | head -10` の出力（コメント以外の日本語が 0 行）。

5-5. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git diff origin/main --stat | tail -10` が §3 の 5 ファイルだけ。

5-6. PR の CI は担当が待たない。PR を作ったら URL を報告して終える。

## 6. 分岐ごとの対処

- §10 手順1 で、origin/main の `backend/app/routers/super_admin_product_formats.py` に `PRODUCT_FORMAT_GAME_IN_USE` の文字が無い → BLOCKED:（作業を始めない）
- §4 の行の目印が実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- `MultiSelect` の Popover が jsdom で開かず試験が書けない → 原文を貼って NEEDS_DECISION:（金型を変えない）
- `api.post` などの型引数で tsc が落ちる → 落ちた行を貼り、型だけで直す。直せなければ BLOCKED:
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 一覧に細分類ごとの使えるゲームが出る | 試験 1、§8 の画面確認 |
| 無効なゲームは選択肢に出ない | 試験 2 |
| 新規でも使えるゲームが保存される | 試験 3 |
| ゲームを変えないときは置き換えを呼ばない | 試験 4 |
| ゲームを変えたら、選んだ一覧で置き換える | 試験 5 |
| 外せないときは理由が分かり、入力が消えない | 試験 6 |
| 文言は ja/en 同じキー、金型だけを使う | §5-4 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の紐づけ表が 69 行のままであること（画面の反映だけでデータが変わらない）を読み取りで確かめる
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin2b2/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（画面だけが元に戻る。API とデータは変わらない）

## 10. PR

手順1 便2aが main にあることを確かめ、新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && git grep -c "PRODUCT_FORMAT_GAME_IN_USE" origin/main -- backend/app/routers/super_admin_product_formats.py
期待する出力 1 以上（0 なら §6 の1つ目）
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/master-register-required-fields-bin2b2 --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2
    このカードを /tmp/CC報告ファイル/master-required-fields/bin2b/card-bin2b2.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2/docs/handoff/master-register-required-fields/card-bin2b2.md` に同じ内容で置く。`cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2/frontend && ls node_modules | head -1` で依存が無ければ `npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-5 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git add frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/master-register-required-fields/card-bin2b2.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git commit -m "feat: ADR-1020便2b-2 細分類マスタで使えるゲームを選ぶ"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && git push -q -u origin release/master-register-required-fields-bin2b2 && git log -1 --oneline && git log origin/release/master-register-required-fields-bin2b2 -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin2b2 && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin2b2-pr-body.md）に作り、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin2b2 --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020 を書く。区分は S か M（危険パスなし）。PO承認: に「PO 2026-10-16『y』（KGI G1〜G4・3便）」と書く
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: 触るファイル: frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx, frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx, frontend/src/locales/ja.json, frontend/src/locales/en.json, docs/handoff/master-register-required-fields/card-bin2b2.md ／ 削除するファイル: なし

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin2b2/impl/）／判断を要した点（事実のみ）
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
