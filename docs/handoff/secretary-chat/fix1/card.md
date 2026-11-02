# 実装カード 直し1 — 鍵が使えないときの文言・単価の小数

親: docs/handoff/secretary-chat/fix1/design.md（第2版）／ recon: docs/handoff/secretary-chat/fix1/recon.md ／ ADR-1056・ADR-027・ADR-144・ADR-067
状態: 設計担当（Opus）作成。実装は Sonnet。成功条件 PO 承認 2026-11-02「1」。
作業場所: 設計の書類 PR #5009（ブランチ `release/secretary-error-message`）がマージされた後の origin/main から、新しいブランチ `release/secretary-fix1-impl` を `bash scripts/new-worktree.sh release/secretary-fix1-impl --claude` で作る（クラウドで作業するときは origin/main から同じ名前のブランチを作る）。#5009 のブランチには push しない。設計の書類（fix1/ と親設計）は触らない。

## 0. 始める前に
- `./scripts/dev/executor-preflight.sh || exit 1`。`frontend/CLAUDE.md`・`docs/CC_UI_GOVERNANCE.md` を読む。
- 下の行番号が実物と合うか確かめる。合わなければ始めずに `BLOCKED:` で止める。

## 1. 変えるファイル（これ以外は触らない）
| ファイル | 変えること |
|---|---|
| `secretary-agent/server.mjs` | :95 の `if (exitCode !== 0) return finish(502, { code: "cli_failed" });` を、下の 2-1 に置き換える |
| `secretary-agent/server.test.mjs` | 下の 3-1 を足す。今の (6) と「読めない出力」の試験は残す |
| `backend/app/routers/assistant.py` | :103-111 を下の 2-2 に置き換える |
| `backend/tests/test_assistant_router.py` | :168 の期待を `(502, {"code": "cli_failed"}, 502, "agent_failed")` に変え、`(502, {"code": "auth_failed"}, 503, "auth_failed")` を足す。:239-247 の試験は画面の code を `agent_failed` に変える。下の 3-2 を足す |
| `frontend/src/features/secretary/secretaryApi.ts` | :56 の型に `"authFailed" \| "agentFailed"` を足す。:58-63 に `auth_failed: "authFailed"`・`agent_failed: "agentFailed"` を足す |
| `frontend/src/features/secretary/SecretaryDraftInvoice.tsx` | 下の 2-3 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | 下の 3-3 |
| `frontend/src/locales/ja.json`・`en.json` | `secretary.error.authFailed`・`secretary.error.agentFailed`・`secretary.priceDecimals` を足す（文言は design.md 2-3 のとおり。1 字も変えない） |

## 2. 中身
### 2-1 server.mjs
```js
      if (exitCode !== 0) {
        // 鍵が使えないとき claude は exit 1 で、標準出力の JSON に api_error_status 401 を出す（fix1/recon.md 1-1）
        let code = "cli_failed";
        try {
          if (JSON.parse(out).api_error_status === 401) code = "auth_failed";
        } catch {
          // 読めなければ cli_failed のまま
        }
        return finish(502, { code });
      }
```
:139 のログはそのまま（`body.code` が `auth_failed` になる）。

### 2-2 assistant.py
```python
    if resp.status_code == 502:
        agent_code = None
        try:
            body = resp.json()
            if isinstance(body, dict):
                agent_code = body.get("code")
        except ValueError:
            pass
        if agent_code == "auth_failed":
            raise _fail(503, "auth_failed")
        if agent_code == "cli_failed":
            raise _fail(502, "agent_failed", "cli_failed")
        raise _fail(502, "unreadable")
```
docstring の直しは無い（assistant.py:1-8・:78 に code の並びは無い。審査で確かめ済み）。

### 2-3 SecretaryDraftInvoice.tsx
- :41 の後に足す:
```ts
/** 保存側は小数 2 けたまで（backend/app/schemas/invoice.py:35）。"1e-7" のような書き方も 3 けた以上とみなす */
function hasTooManyDecimals(value: string): boolean {
  const trimmed = value.trim();
  return /\.\d{3,}$/.test(trimmed) || /e-/i.test(trimmed);
}
```
- `isValidUnitPrice` の return を `trimmed !== "" && Number.isFinite(Number(trimmed)) && Number(trimmed) >= 0 && !hasTooManyDecimals(trimmed)` にする。
- :73 の後に `const priceTooPrecise = items.some((i) => hasTooManyDecimals(i.unitPrice));`。
- :172 の後に `{priceTooPrecise && <p className="secretary-draft__hint">{t("secretary.priceDecimals")}</p>}`。
- 単価の `TextField`（:155-162）に `step={0.01}` を足す（数の欄 :151 の `step={1}` と同じ書き方）。
- :49 は変えない（丸めない）。

## 3. 試験
### 3-1 server.test.mjs
- 偽の claude: `cat >/dev/null; echo '{"type":"result","is_error":true,"api_error_status":401,"result":"Failed to authenticate. API Error: 401 OAuth access token is invalid."}'; exit 1` → 502 `{code:"auth_failed"}`、使い捨てディレクトリが残らない。
- 偽の claude: 同じ形で `"api_error_status":500` と exit 1 → 502 `{code:"cli_failed"}`。
- ログ: `startServer` は今 `stdio: "ignore"`。この試験だけ標準出力を受け取れるよう、`startServer` に省略できる引数（例: `{ captureStdout: true }`）を足し、戻り値に標準出力を貯めた文字列を返す入れ物を足す。ほかの試験の動きは変えない。
- 待ち方: server.mjs:139 のログは応答（:140）の直前に出るが、試験側に届く順は決まらない。応答を受け取ったあと、標準出力に `"code":"auth_failed"` が届くまで 50 ミリ秒ごとに見て、上限 2 秒で待つ。届かなければ失敗。そのうえで `Failed to authenticate` の文字が無いことを確かめる。

### 3-2 test_assistant_router.py
- 容器 502 `auth_failed` → 503 `{"code":"auth_failed"}`、ログの行に `code=auth_failed`。
- 容器 502 `cli_failed` → 502 `{"code":"agent_failed"}`、ログの行に `code=cli_failed`。
- 容器 502 `unreadable` → 502 `{"code":"unreadable"}`（今のまま）。

### 3-3 SecretaryChat.test.tsx（英語の言葉で確かめる今の作法に合わせる）
- 503 `auth_failed` → authFailed の英語の言葉が出る。"rephrase" 系の unreadable の言葉は出ない。
- 502 `agent_failed` → agentFailed の英語の文が全体で一致する（`/Something went wrong/` だけで探すと generic でも通るため）。generic の文 "Please try again" が出ていないことも確かめる。
- 502 `unreadable` → unreadable の言葉（今の試験が無ければ足す）。
- 単価欄への入力は今の作法 `fireEvent.change(getByLabelText("Unit price"), { target: { value } })`（SecretaryChat.test.tsx:185）に合わせる。jsdom の type=number は "1000.255" をそのまま持つ（審査で実測済み）。
- 下書きの単価欄に 1000.255 を入れる → priceDecimals の言葉が出て「作る」が押せない。
- 1000.5、1000.25 → 「作る」が押せて、`/invoices` に送る unit_price が 1000.5・1000.25。
- 下書き `unit_price: 1000.255` → 欄の値が "1000.255"・priceDecimals の言葉・「作る」が押せない。

## 4. 受入（実装役が自分で流して生の出力をファイルに残す）
| 基準 | 検証方法 |
|---|---|
| 容器（CI では走らない。生の出力を PR に添える） | `cd secretary-agent && node --test` |
| backend | `cd backend && python -m pytest tests/test_assistant_router.py -q`（今の作法でDBが要るならそれに従う） |
| 画面の試験 | `cd frontend && npx vitest run src/features/secretary` |
| 型 | `cd frontend && npx tsc --noEmit` |
| lint | `cd frontend && npx eslint src/features/secretary` |
| 金型外 | `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD node scripts/check-ui-governance.js` |
| 言葉 | ja/en の `secretary` のキー差 0 件。`frontend/CLAUDE.md` の grep セルフチェックで直書き 0 件 |
| ダーク | `cd frontend && npm run check:dark-parity` |
| 触らない範囲 | `git diff --name-only origin/main...HEAD` が 1 の表のファイルだけ（fix1/ の書類と親設計 design.md は含まない） |

## 5. 想定分岐（迷ったら止まる）
- :95 や :103-111 の中身が上の「前」と違う → `BLOCKED:`。
- `TextField` が `step` を受け取らない → 足さずに PR 本文に書く（金型を変えない）。
- backend の試験が DB 無しで動かない → 今の CI と同じやり方を探し、無ければ CI の結果を受入にして PR 本文に書く。

## 6. 進め方
- コミットの最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- PR は `--base main`。本文の「標準ワークフロー確認」: recon docs/handoff/secretary-chat/fix1/recon.md、設計 docs/handoff/secretary-chat/fix1/design.md、対象ADR ADR-1056・ADR-027・ADR-144・ADR-067、区分 B-1、触るファイルを全部列挙。
- マージしない。終わったら PR の URL と受入の生の出力の置き場を返す。
- 本番の確かめ（design A9）は実装役はしない。設計担当が配備後に行う。
