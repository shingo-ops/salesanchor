---
mode: handoff
---
# 実装カード 便2: サーバーの共通の2種類の文を理由コードにする（ADR-1071 A2 の1回目）

親: [design.md](./design.md) §11。ADR: [ADR-1071](../../adr/ADR-1071-plain-language-error-messages.md)。

- 状態: カード作成済み（2026-11-08 Opus）。
- 実装承認: PO 2026-11-08 の選択「2」（サーバーの文を直す作業から始める）と、同じ発言の「PRマージ、デプロイまで完走させてくれ」。マージと本番への反映の GO は Opus が委任（ADR-1003）に基づき別に出す。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR 作成・GO・マージ判断。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/ の 00-common.md・03-file.md・04-worktree.md・10-executor.md
- 区分: サーバーの失敗の応答の detail の文字列・画面の API の受け口・文言・試験。migrations・deploy.yml・本番 scripts/・.github/ は触らない。
- 作業する枝: `release/error-text-bin2-common-reasons`（設計の文書とこのカードが載って push 済み）。新しい枝は作らない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は PR を作らない） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（共通の2種類の文だけ。「見つかりません」は直さない） | ○ |
| 5 | 既存の枝の起点を明示（origin/release/error-text-bin2-common-reasons） | ○（§5 手順1） |
| 6 | 書式は実例で示す（作るコードと文を全部書く） | ○（§3） |
| 7 | 合格基準を出力まで縛る（触るファイル以外 0） | ○（§5 手順9・10） |
| 8 | 件数の判定には名前を出す手順を対で置く | ○（§5 手順3・4） |
| 9 | 出力量に上限のないコマンドを使わない | ○（`| tail -N`） |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（前後の文で探す） | ○（§3） |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・PR は作らない・フックに止められたら言い換えない） | ○（§4） |

## 1. 目的（便2 で起きること）

- サーバーの 92 か所の失敗の文（design §11-2 の表の 8 種類の文）を、理由コード `no_fields_to_update` と `conflict_constraint` に置き換える。状態番号は変えない。
- 画面の API の受け口（`frontend/src/lib/api.ts` の2か所）で、この2つのコードを受けたら、画面の言語の文（design §11-4）を出す。表に無いコードは今までどおり。
- W1 の基準値を 739 → 647 に下げる。

## 2. 触るファイル（これ以外は触らない）

| # | ファイル | 新規/変更 |
|---|---|---|
| 1 | `backend/app/routers/` の下の 47 ファイル（§3-1 の台本が置き換えたファイルだけ） | 変更（detail の文字列だけ） |
| 2 | `backend/tests/error_detail_baseline.json` | 変更（台本で書き出す。手で直さない） |
| 3 | `backend/tests/test_super_admin_unit_ignore_phrases.py` | 変更（1 行） |
| 4 | `backend/tests/test_api_error_reason_sync.py` | 新規 |
| 5 | `frontend/src/lib/apiErrorReason.ts` | 新規 |
| 6 | `frontend/src/lib/apiErrorReason.test.ts` | 新規 |
| 7 | `frontend/src/lib/api.ts` | 変更（import 1 行・2 か所） |
| 8 | `frontend/src/lib/api.httpError.test.ts` | 変更（試験を足す） |
| 9 | `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 変更（`apiError` の区切りを足す） |

## 3. 作る中身（design §11 が正。食い違えば design に従い、報告に書く）

### 3-1 サーバーの文の置き換え（台本で行う。ファイルごとに手で直さない）

置き換えの表（左の文字列を、ダブルクォートを含めて文字どおり、右に置き換える）:

| 今の文字列 | 新しい文字列 |
|---|---|
| `"更新するフィールドを指定してください"` | `"no_fields_to_update"` |
| `"更新するフィールドを少なくとも1つ指定してください"` | `"no_fields_to_update"` |
| `"更新フィールドが指定されていません"` | `"no_fields_to_update"` |
| `"制約違反"` | `"conflict_constraint"` |
| `"重複または制約違反"` | `"conflict_constraint"` |
| `"重複または FK 違反"` | `"conflict_constraint"` |
| `"会社の登録に失敗しました（company_code 重複または制約違反の可能性）"` | `"conflict_constraint"` |
| `"担当者の登録に失敗しました（contact_code 重複または制約違反の可能性）"` | `"conflict_constraint"` |

台本 `/tmp/replace_bin2.py`（Write で作る。リポジトリには入れない）:

```python
import sys
from pathlib import Path

PAIRS = [
    ('"更新するフィールドを指定してください"', '"no_fields_to_update"'),
    ('"更新するフィールドを少なくとも1つ指定してください"', '"no_fields_to_update"'),
    ('"更新フィールドが指定されていません"', '"no_fields_to_update"'),
    ('"制約違反"', '"conflict_constraint"'),
    ('"重複または制約違反"', '"conflict_constraint"'),
    ('"重複または FK 違反"', '"conflict_constraint"'),
    ('"会社の登録に失敗しました（company_code 重複または制約違反の可能性）"', '"conflict_constraint"'),
    ('"担当者の登録に失敗しました（contact_code 重複または制約違反の可能性）"', '"conflict_constraint"'),
]
app = Path(sys.argv[1])
total = {old: 0 for old, _ in PAIRS}
files = []
for path in sorted(app.rglob("*.py")):
    text = path.read_text(encoding="utf-8")
    new = text
    for old, rep in PAIRS:
        n = new.count(old)
        if n:
            total[old] += n
            new = new.replace(old, rep)
    if new != text:
        path.write_text(new, encoding="utf-8")
        files.append(path.relative_to(app).as_posix())
for old, _ in PAIRS:
    print(total[old], old)
print("sum", sum(total.values()), "files", len(files))
for f in files:
    print(f)
```

期待（Opus が origin/main `b6b89095c` で数えた値）: 42・5・3・19・15・6・1・1、sum 92、files 47。違っても止まらず、数と名前を報告に書く。

### 3-2 `backend/tests/test_super_admin_unit_ignore_phrases.py`

`assert dup.json()["detail"] == "重複または制約違反"` の 1 行を `assert dup.json()["detail"] == "conflict_constraint"` にする。ほかは変えない。

### 3-3 `frontend/src/lib/apiErrorReason.ts`（新規。このとおりに作る）

```ts
/**
 * サーバーが失敗の応答の detail に文字列で返す、画面に共通の理由コード → 文言キーの対応表（ADR-1071 便2）。
 *
 * frontend/src/lib/api.ts が、detail がこの表のコードのときだけ i18n の文を ApiError.message にする。
 * 表に無いコードは今までどおり detail をそのまま message にする（コードを比べている画面を壊さないため）。
 * 新しいコードを足すときは、この表に 1 行と、ja.json・en.json の apiError に文を足す。
 * 突き合わせの試験: apiErrorReason.test.ts（画面側）・backend/tests/test_api_error_reason_sync.py（サーバー側）。
 */
export const API_ERROR_REASON_KEYS: Readonly<Record<string, string>> = {
  no_fields_to_update: "apiError.noFieldsToUpdate",
  conflict_constraint: "apiError.conflictConstraint",
};

/** detail が表のコードなら文言キー、そうでなければ null */
export function apiErrorReasonKey(detail: unknown): string | null {
  if (typeof detail !== "string") return null;
  return Object.prototype.hasOwnProperty.call(API_ERROR_REASON_KEYS, detail)
    ? API_ERROR_REASON_KEYS[detail]
    : null;
}
```

### 3-4 `frontend/src/lib/api.ts`

- import の並び（`import { expireSession, getAccessToken, selfRefresh } from "./auth/selfAuth";` の次の行）に `import { apiErrorReasonKey } from "./apiErrorReason";` を足す。
- `request` の中の `if (!res.ok) {` のかたまり（`// detail が文字列ならそのままメッセージ、dict なら detail フィールドを優先` の注記があるところ）を次にする:

```ts
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        // detail が共通の理由コード（apiErrorReason.ts の表）なら画面の言語の文、
        // それ以外の文字列ならそのまま、dict なら detail フィールドを優先
        const reasonKey = apiErrorReasonKey(detail);
        const message = reasonKey
          ? i18n.t(reasonKey)
          : typeof detail === "string"
            ? detail
            : detail?.detail || i18n.t("common.httpError", { status: res.status });
        throw new ApiError(message, res.status, detail);
      }
```

- `requestForm` の中の `if (!res.ok) {` のかたまりを次にする:

```ts
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail = (errBody as { detail?: unknown }).detail;
    const reasonKey = apiErrorReasonKey(detail);
    const message = reasonKey
      ? i18n.t(reasonKey)
      : typeof detail === "string"
        ? detail
        : (detail as { detail?: string })?.detail || i18n.t("common.httpError", { status: res.status });
    throw new ApiError(message, res.status, detail);
  }
```

- ほかの所は変えない。型の都合で `i18n.t(reasonKey)` が通らないときは、止まらずに `i18n.t(reasonKey as never)` などの最小の直しをし、報告に書く。

### 3-5 文言（`ja.json`・`en.json` の最上位の最後に `apiError` を足す。2 つのファイルで同じ位置・同じキー）

ja:

```json
  "apiError": {
    "noFieldsToUpdate": "変わった項目がないため、保存しませんでした。内容を変えてから、もう一度保存してください。",
    "conflictConstraint": "同じものがすでに登録されているか、関係するデータと合わないため、保存できませんでした。入力した内容を確かめて、もう一度お試しください。"
  }
```

en:

```json
  "apiError": {
    "noFieldsToUpdate": "Nothing was saved because no fields were changed. Change something, then save again.",
    "conflictConstraint": "This could not be saved because the same item already exists or it does not match related data. Check what you entered and try again."
  }
```

直前の最上位のキーの閉じかっこ `}` の後ろに `,` を付ける。JSON として読めることを §5 手順6 で確かめる。

### 3-6 `frontend/src/lib/apiErrorReason.test.ts`（新規）

```ts
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import ja from "../locales/ja.json";
import en from "../locales/en.json";
import { API_ERROR_REASON_KEYS, apiErrorReasonKey } from "./apiErrorReason";

type Dict = Record<string, unknown>;
const lookup = (d: Dict, key: string): unknown =>
  key.split(".").reduce<unknown>((cur, k) => (cur && typeof cur === "object" ? (cur as Dict)[k] : undefined), d);

// CI checks out the whole repo and runs from frontend (precedent: src/features/discord-connect/discordConnectError.test.ts)
function readPyFiles(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...readPyFiles(p));
    else if (name.endsWith(".py")) out.push(readFileSync(p, "utf8"));
  }
  return out;
}

describe("apiErrorReasonKey", () => {
  it("maps table codes to locale keys and returns null otherwise", () => {
    expect(apiErrorReasonKey("no_fields_to_update")).toBe("apiError.noFieldsToUpdate");
    expect(apiErrorReasonKey("conflict_constraint")).toBe("apiError.conflictConstraint");
    expect(apiErrorReasonKey("viewer_already_linked")).toBeNull();
    expect(apiErrorReasonKey("toString")).toBeNull();
    expect(apiErrorReasonKey({ reason: "no_fields_to_update" })).toBeNull();
    expect(apiErrorReasonKey(null)).toBeNull();
  });
});

describe("i18n", () => {
  it("has a non-empty ja and en text for every key", () => {
    for (const key of Object.values(API_ERROR_REASON_KEYS)) {
      expect(lookup(ja as Dict, key), `ja:${key}`).toBeTruthy();
      expect(lookup(en as Dict, key), `en:${key}`).toBeTruthy();
    }
  });
});

describe("backend sync", () => {
  const sources = readPyFiles("../backend/app").join("\n");
  it("every table code is used in backend/app", () => {
    expect(Object.keys(API_ERROR_REASON_KEYS).length).toBe(2);
    for (const code of Object.keys(API_ERROR_REASON_KEYS)) {
      expect(sources.includes(`"${code}"`), code).toBe(true);
    }
  });
});
```

### 3-7 `backend/tests/test_api_error_reason_sync.py`（新規）

```python
"""画面の共通の理由コードの表（frontend/src/lib/apiErrorReason.ts）とサーバーの突き合わせ（ADR-1071 便2）。

サーバーだけを変えた PR でも、表のコードが backend/app から消えていないことを確かめる。
画面だけを変えた PR は frontend/src/lib/apiErrorReason.test.ts が同じことを確かめる。
DB・ネットワークは使わない。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "frontend" / "src" / "lib" / "apiErrorReason.ts"
APP_DIR = REPO / "backend" / "app"

_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.[A-Za-z0-9]+",?$', re.MULTILINE)


def _codes() -> list[str]:
    return _ROW.findall(TABLE.read_text(encoding="utf-8"))


def test_table_rows_are_read():
    assert _codes() == ["no_fields_to_update", "conflict_constraint"]


def test_table_codes_are_used_in_app():
    sources = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_DIR.rglob("*.py")))
    missing = [c for c in _codes() if f'"{c}"' not in sources]
    assert not missing, "表のコードがサーバーで使われていない: " + ", ".join(missing)
```

### 3-8 `frontend/src/lib/api.httpError.test.ts`（足す）

ファイルの先頭の import の並びに `import ja from "../locales/ja.json";` を1行足し、ファイルの最後に次を足す（既存の試験は変えない）。日本語の期待値は ja.json から読む（試験のファイルに日本語を直接書くと、記録の前の点検 `eslint --max-warnings=0` の `local/no-japanese-literal` で止まるため）:

```ts
async function catchApiError(run: () => Promise<unknown>): Promise<ApiError> {
  let caught: unknown;
  try {
    await run();
  } catch (e) {
    caught = e;
  }
  expect(caught).toBeInstanceOf(ApiError);
  return caught as ApiError;
}

function stubDetail(status: number, detail: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), { status, headers: { "Content-Type": "application/json" } }),
    ),
  );
}

describe("common reason code texts (ADR-1071 bin2)", () => {
  afterEach(async () => {
    await i18n.changeLanguage("ja");
  });

  const cases = [
    {
      status: 400,
      code: "no_fields_to_update",
      ja: ja.apiError.noFieldsToUpdate,
      en: "Nothing was saved because no fields were changed. Change something, then save again.",
    },
    {
      status: 409,
      code: "conflict_constraint",
      ja: ja.apiError.conflictConstraint,
      en: "This could not be saved because the same item already exists or it does not match related data. Check what you entered and try again.",
    },
  ];

  for (const c of cases) {
    for (const lang of ["ja", "en"] as const) {
      it(`request: ${c.code} becomes the ${lang} text`, async () => {
        await i18n.changeLanguage(lang);
        stubDetail(c.status, c.code);
        const err = await catchApiError(() => api.patch("/dummy", {}));
        expect(err.status).toBe(c.status);
        expect(err.message).toBe(c[lang]);
        expect(err.responseDetail).toBe(c.code);
      });
      it(`requestForm: ${c.code} becomes the ${lang} text`, async () => {
        await i18n.changeLanguage(lang);
        stubDetail(c.status, c.code);
        const err = await catchApiError(() => api.postForm("/dummy", new FormData()));
        expect(err.message).toBe(c[lang]);
        expect(err.responseDetail).toBe(c.code);
      });
    }
  }

  it("passes an unknown code through unchanged", async () => {
    stubDetail(409, "viewer_already_linked");
    const err = await catchApiError(() => api.post("/dummy", {}));
    expect(err.message).toBe("viewer_already_linked");
  });

  it("keeps the detail field of a dict detail", async () => {
    stubDetail(409, { detail: "x", id: 1 });
    const err = await catchApiError(() => api.post("/dummy", {}));
    expect(err.message).toBe("x");
  });
});
```

POST・PATCH が送り直しをして試験が待つときは、止まらずに原因を報告に書き、`api.get` に変えて続ける（文の確かめが目的）。

## 4. 担当の決まり（定型）

1. sleep で待たない。CI の結果は待たずに報告して終える（Opus が見る）。
2. ファイルの編集は Edit／Write のツールで行う。ヒアドキュメントや sed で書き換えない。例外: §3-1 の置き換えは `/tmp/replace_bin2.py` の台本で、基準値の JSON は §5 手順4 の台本で行う。
3. PR は作らない（Opus が作る）。push までで終える。
4. フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を報告に書いて終える。
5. 止まるのは次だけ: 削除・`--force` が要る push・main への push・本番への接続が要る場面・§2 以外のファイルを直さないと進めない場面。それ以外の数や行の食い違いは記録して続ける。
6. 秘密の値を画面にもファイルにも出さない。
7. Bash に psql の語を書かない。commit 文は `-m` で渡す。git は 1 命令ずつ流す。
8. 1 つの発言は 600 文字以内。長い報告は番号付きの発言に分ける。

## 5. 手順（1手順1コマンド。`<repo>` は担当の作業場所の絶対パス）

1. 作業場所を公式の台本で作る。`<main>` はクラウドが最初に置いたリポジトリの場所。次を 1 つずつ流し、出力を報告に書く。Bash ツールの timeout 引数は 600000 にする。
   - (1a) `cd <main> && git fetch origin release/error-text-bin2-common-reasons main`
   - (1b) `cd <main> && git branch --list release/error-text-bin2-common-reasons`。出力が空であること。空でなければ消さずに BLOCKED で終える。`git checkout -B` は使わない。
   - (1c) `cd <main> && bash scripts/new-worktree.sh release/error-text-bin2-common-reasons`。`--claude` は付けない。出力は head・tail などのパイプに通さない。
   - (1d) `ls -1d "$HOME/worktrees/salesanchor/release-error-text-bin2-common-reasons"` と `git -C <main> worktree list`。両方にその場所が出ること。出なければ BLOCKED。以後の `<repo>` はこの場所の絶対パス。
   - (1e) push 済みの枝の先頭に合わせる: `cd <repo> && git switch -C release/error-text-bin2-common-reasons origin/release/error-text-bin2-common-reasons`。続けて `cd <repo> && git rev-parse HEAD` と `cd <repo> && git rev-parse origin/release/error-text-bin2-common-reasons` を流し、2 つが同じことを報告に書く（違えば BLOCKED）。続けて `cd <repo> && git log --oneline -3`。rebase・reset はしない。
   - 台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない。
2. 環境を作る（前回の便0 と同じ）:
   - (2a) `python3.12 --version; echo rc=$?`。rc=0 なら `python3.12 -m venv /tmp/v312; echo rc=$?`、0 でなければ `uv venv --python 3.12 /tmp/v312; echo rc=$?`（これも 0 でなければ BLOCKED）。
   - (2b) `cd <repo>/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt > /tmp/v312-pip.txt 2>&1; echo rc=$?` と `tail -30 /tmp/v312-pip.txt`（uv で作ったときは `uv pip install --python /tmp/v312/bin/python -q -r requirements.txt -r requirements-dev.txt`）。rc=0 でなければ BLOCKED。
   - (2c) `cd <repo>/frontend && npm ci > /tmp/npm-ci.txt 2>&1; echo rc=$?` と `tail -20 /tmp/npm-ci.txt`。rc=0 でなければ BLOCKED。
3. サーバーの置き換え: `/tmp/replace_bin2.py` を §3-1 のとおり Write で作り、`cd <repo>/backend && /tmp/v312/bin/python /tmp/replace_bin2.py app 2>&1 | tail -60`。続けて `cd <repo> && git diff --stat backend/app | tail -5` と `cd <repo> && git grep -nE '更新するフィールド|更新フィールドが指定|制約違反|FK 違反' -- backend/app | tail -10`（合格: 出力が次のコメント4行だけ。`app/schemas/central_masters.py:30`・`app/routers/super_admin_aliases.py:300`・`app/routers/super_admin_aliases.py:308`・`app/routers/tcg_product_import.py:491`。どれも `#` の後ろの説明文で、detail ではないので直さない。これ以外の行が出たら BLOCKED:）。
4. 基準値を台本で書き出す: `cd <repo>/backend && /tmp/v312/bin/python tests/test_error_detail_guard.py --write-baseline` と `cd <repo> && git diff --stat backend/tests/error_detail_baseline.json | tail -3`。期待: `書き出し: ` の後の件数が 647。違っても止まらず、数を報告に書く。
5. §3-2〜§3-8 を Edit／Write で作る。
6. 確かめ（それぞれ `| tail -N` で切る）:
   - (6a) `cd <repo>/frontend && node -e "for (const f of ['src/locales/ja.json','src/locales/en.json']) { const d=require('./'+f); console.log(f, Object.keys(d).length, JSON.stringify(d.apiError)); }"`
   - (6b) `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 -rA tests/test_error_detail_guard.py tests/test_api_error_reason_sync.py 2>&1 | tail -30`。timeout 引数は 600000。合格: 5 つ passed・赤 0。
   - (6c) `cd <repo>/backend && /tmp/v312/bin/python -m pytest -q --no-cov -p no:cacheprovider -n 0 tests/test_super_admin_unit_ignore_phrases.py 2>&1 | tail -30`。DB が無くて skip や error になるときは、その出力をそのまま報告に書いて続ける（CI で見る）。
   - (6d) `cd <repo>/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/api.httpError.test.ts src/lib/apiErrorReason.test.ts 2>&1 | tail -40`。合格: 赤 0。
   - (6e) `cd <repo>/frontend && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -20; echo rc=$?`（tsconfig の名前が違えば `ls tsconfig*` を流し、app 用のものを使う）。
   - (6f) `cd <repo>/frontend && npx eslint src/lib/api.ts src/lib/apiErrorReason.ts src/lib/apiErrorReason.test.ts src/lib/api.httpError.test.ts 2>&1 | tail -20; echo rc=$?`
   - (6g) `cd <repo>/frontend && npm run check:i18n-missing-keys 2>&1 | tail -10` と `cd <repo>/frontend && npm run check:error-text-next-action 2>&1 | tail -10`。合格: どちらも赤 0。W2 の基準値は変えない。
   - (6h) `cd <repo>/backend && /tmp/v312/bin/python -m ruff check app tests/test_api_error_reason_sync.py tests/test_super_admin_unit_ignore_phrases.py 2>&1 | tail -20` と `cd <repo>/backend && /tmp/v312/bin/python -m ruff format --check tests/test_api_error_reason_sync.py 2>&1 | tail -5`。format が赤なら `ruff format` で直し、直したことを報告に書く。
7. 予備: `cd <repo> && git diff origin/main --stat -- backend/app | tail -3` と、置き換え以外の差が無いことの確かめ `cd <repo> && git diff origin/main -- backend/app | grep -E '^[-+][^-+]' | grep -vE 'no_fields_to_update|conflict_constraint|更新するフィールド|更新フィールドが指定|制約違反|FK 違反' | tail -10`（合格: 出力が空）。
8. `cd <repo> && git add backend/app backend/tests/error_detail_baseline.json backend/tests/test_super_admin_unit_ignore_phrases.py backend/tests/test_api_error_reason_sync.py frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/lib/api.ts frontend/src/lib/api.httpError.test.ts frontend/src/locales/ja.json frontend/src/locales/en.json`
9. `cd <repo> && git diff --cached --stat | tail -70` を報告に書く。合格: 変えたファイルが §2 のものだけ（backend/app は手順3 の台本が出した名前だけ）。
10. commit: `cd <repo> && PATH=/tmp/v312/bin:$PATH git commit -m "feat(errors): common reason codes for no-fields and conflict errors (ADR-1071 bin2)" -m "Co-Authored-By: Claude Sonnet <noreply@anthropic.com>"`。timeout 引数は 600000。続けて `cd <repo> && git log --oneline -3` と `cd <repo> && git diff origin/main...HEAD --name-only | tail -70` を報告に書く。合格: 設計の文書（`docs/handoff/error-message-plain-language/` の下）と §2 のものだけ。
11. push: `cd <repo> && PATH=/tmp/v312/bin:$PATH git push -u origin HEAD`。timeout 引数は 600000。出力の全文を報告に書く。続けて `cd <repo> && git ls-remote origin release/error-text-bin2-common-reasons` と `cd <repo> && git rev-parse HEAD` を報告に書き、一致を確かめる。

## 6. PR

担当は作らない。Opus が push を確かめてから、`### 標準ワークフロー確認` と `### GO記録` を入れて作る。

## 7. 報告（完了報告の本文に、次をこの順で全部含める）

1. 冒頭の1行: 本報告はカード 便2（card-bin2、共通の2種類の文の理由コード化）の実行結果である。続けて、受領確認: カード末尾の合図 END OF CARD（END-OF-CARD-ERRMSG-BIN2）まで読んだ。
2. 手順1〜11 の各コマンドの生出力（省略しない。`tail` で切った範囲はそのまま）。
3. 置き換えの数（手順3）と基準値の件数（手順4）。
4. §3 と違う作り方をした所の一覧（無ければ「無し」）。
5. 止まった場合は「止まった手順の番号／最後に実行したコマンド／止まった理由の原文」。
6. 最後の行は `DONE`、`BLOCKED: 理由`、`NEEDS_DECISION: 問い`（理由・問いは文で書く） のどれか1つ。

END OF CARD（END-OF-CARD-ERRMSG-BIN2）
