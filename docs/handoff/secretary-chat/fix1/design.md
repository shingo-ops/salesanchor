# 秘書チャット 直し1 — 設計（鍵が使えないときの文言・単価の小数）

第2版（2026-11-02。第1版の審査 REVISE の指摘 MEDIUM 3・LOW 3 を反映）。設計担当 Opus。
現在地: docs/handoff/secretary-chat/fix1/recon.md ／ 親設計: docs/handoff/secretary-chat/design.md §5-7 ／ ADR-1056・ADR-027・ADR-144・ADR-067
区分: B-1（画面・backend・容器の小さな直し。migrations・deploy.yml・本番 scripts は触らない）

## 1. 目的と成功条件（PO 承認 2026-11-02「1」）
PO が秘書に頼んで失敗したとき、画面の文言で本当の理由が分かる。見積の単価で、作れない入力を作る前に止める。

| 基準 | 検証方法 |
|---|---|
| A1 鍵が使えない（claude が 401）とき、画面に「秘書の鍵が使えなくなっています。管理者に知らせてください」。「言い方を変えてください」は出ない | 偽の claude が 401 の JSON を出して exit 1 → 容器 502 `auth_failed`（server.test.mjs）→ backend 503 `auth_failed`（pytest）→ 画面の言葉（vitest） |
| A2 AI の側が別の理由で止まった（0 以外で終了・401 以外）とき「うまくいきませんでした。少し待ってからもう一度送ってください」 | 偽の claude が 500 の JSON・出力なしで exit → 容器 502 `cli_failed` → backend 502 `agent_failed` → 画面の言葉 |
| A3 「言い方を変えてください」は、AI は答えたが中身を読めなかったときだけ | 容器 502 `unreadable`・形の検査落ち → backend 502 `unreadable` → 画面の言葉（今の試験を残す） |
| A4 裏側の記録に「鍵が使えない」と残る | 容器のログの code が `auth_failed`（server.test.mjs で標準出力を読む）、backend のログの code が `auth_failed`（pytest caplog） |
| A5 単価の小数が 3 けた以上なら「単価は小数2けたまでです」と出て「作る」が押せない | vitest: 1000.255 を入れる → 案内あり・ボタン無効 |
| A6 小数 2 けたまでなら作れる | vitest: 1000.5・1000.25 → ボタン有効・送る値が 1000.5・1000.25 |
| A7 AI の下書きの単価が 3 けた以上でも同じ案内。勝手に丸めない | vitest: 下書き unit_price 1000.255 → 欄の値 "1000.255"・案内あり・ボタン無効 |
| A8 ふだんの請求書作成画面と保存側の決まりは変えない | 差分に `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx`・`backend/app/schemas/invoice.py` が無い（`git diff --name-only`） |
| A9 本番で鍵をわざと壊して試さない | 本番の確かめは次の 2 つだけ。(1) 配備後に PO が 1 回頼んで成功し、予定か請求書の行が 1 件増える（設計担当が本番DBを読むだけの道で確かめる。recon 1-1 と同じやり方）。(2) 設計担当が PO から許された鍵で、容器のログを読むだけのコマンド（`docker logs secretary-agent --since <配備時刻>`）を流し、その頼みの行の code が `ok`。エージェント用の制限付き鍵ではログを読めない（docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58）ので、実装役はこの確かめをしない |

## 2. 変更前 → 変更後

### 2-1 容器 secretary-agent/server.mjs
- 前: 終了コードが 0 以外 → 502 `cli_failed`（標準出力を読まない。:95）。
- 後: 終了コードが 0 以外 → 標準出力を JSON として読んでみる。読めて `api_error_status === 401` なら 502 `{"code":"auth_failed"}`。読めない・401 以外は今までどおり 502 `cli_failed`。
- ログの code はその code（`auth_failed`／`cli_failed`）。利用者の文・標準エラー・result の文字はこれまでどおり記録しない。
- 理由: 本番で観測した出力は標準出力の JSON の `api_error_status: 401`（recon 1-1）。標準エラーは記録しない決まり（:3・:83）を変えずに判別できる。

### 2-2 backend/app/routers/assistant.py `_call_agent`
- 前: 容器 502 は全部 画面 502 `unreadable`（ログだけ `cli_failed`）。
- 後（容器の 502 の本文の code で分ける）:

| 容器の 502 の code | 画面へ | ログの code |
|---|---|---|
| `auth_failed` | 503 `{"detail":{"code":"auth_failed"}}` | `auth_failed` |
| `cli_failed` | 502 `{"detail":{"code":"agent_failed"}}` | `cli_failed` |
| `unreadable`・本文が読めない・その他 | 502 `{"detail":{"code":"unreadable"}}` | `unreadable` |

- 503・429・504・200 と、形の検査落ち（:141-159）はそのまま。
- 理由: 鍵の問題は「頼み方」でなく「使えない状態」なので 503。AI 側の失敗は 502 のまま code だけ分ける。

### 2-3 画面
- `frontend/src/features/secretary/secretaryApi.ts` の `SecretaryErrorKind` に `authFailed`・`agentFailed` を足し、`KNOWN_CODES` に `auth_failed: "authFailed"`・`agent_failed: "agentFailed"` を足す。
- 言葉（ja/en 同じキー・ADR-027）:
  - `secretary.error.authFailed` = 「秘書の鍵が使えなくなっています。管理者に知らせてください」／ "The assistant's key no longer works. Please tell your administrator."
  - `secretary.error.agentFailed` = 「うまくいきませんでした。少し待ってからもう一度送ってください」／ "Something went wrong. Please wait a moment and send it again."
  - `secretary.priceDecimals` = 「単価は小数2けたまでです」／ "Unit price can have up to 2 decimal places."
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx`:
  - 小数の桁の判定 `hasTooManyDecimals(value)`: 空白を除いた値が `/\.\d{3,}$/` に合う、または `/e-/i` を含む（`String(0.0000001)` が "1e-7" になるため）なら true。最後の 0 も 1 けたと数える（"1000.250" も止める。厳しめだが害はない）。
  - `isValidUnitPrice` は今の条件に `&& !hasTooManyDecimals(value)` を足す。
  - 案内: どれかの行で `hasTooManyDecimals` が true なら、`priceRequired` の案内の下に同じ金型の書き方（`secretary-draft__hint`）で `t("secretary.priceDecimals")`。
  - 単価の欄に `step="0.01"`（ふだんの作成画面 `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:389` と同じ）。
  - 下書きの値は丸めない（:49 はそのまま）。
- 新しい金型・色・CSS は足さない（既存の `secretary-draft__hint` を使う）。

### 2-4 文書
- 親設計 `docs/handoff/secretary-chat/design.md` §5-7 の表（:90）と :93・:165 に「直し1で分けた（fix1/design.md）」と追記する。消さない。設計担当がこの設計 PR で済ませる。

## 3. 触らない範囲
- `backend/app/schemas/invoice.py`・`frontend/src/pages/invoice-create/InvoiceCreatePage.tsx`・`secretary-agent/schema.json`・`prompt.txt`・`Dockerfile`・deploy.yml・compose・migrations・`scripts/ops/place-secretary-token.sh`。
- `/health` の `ready`（鍵があるかだけ見る）は今回変えない。

## 4. 代替案
- (a) 標準エラーを読んで判別 → 記録しない決まり（server.mjs:3）に反し、出力の形も未観測。不採用。
- (b) 画面で「鍵」の文言を出さず generic のまま → PO の基準 A1 を満たさない。不採用。
- (c) 単価を小数 2 けたに自動で丸める → PO の基準 A7（勝手に丸めない）に反する。不採用。
- (d) 401 に加えて 403・429 も鍵扱い → 出力が未観測（recon 3）。推測になるので不採用。2 の表では `cli_failed` に入り、A2 の文言になる。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| claude の版が上がり `api_error_status` の名前が変わる | Dockerfile で 2.1.314 に固定。上げるときは server.test.mjs の 401 の見本を実物に合わせる。変わっても `cli_failed`（A2 の文言）に落ちるだけで止まらない |
| 401 の JSON に鍵の値が含まれる | 観測した出力に鍵の値は無い（recon 1-1 の生の出力で `sk-ant` 0 件）。そもそもログには code しか書かない |
| ja/en のキーずれ | 今の i18n の検査とキー差 0 件の確認 |

## 6. 計画
1 枚のカード（docs/handoff/secretary-chat/fix1/card.md）で Sonnet が実装 → 審査役 Opus → CI → マージ → 配備 → 配備後の確かめ（A9）。

## 7. 維持の仕組み
- 守り手: .github/workflows/test.yml（backend の対応の試験 backend/tests/test_assistant_router.py）と .github/workflows/e2e.yml（画面の試験 frontend/src/features/secretary/SecretaryChat.test.tsx）。容器の試験 secretary-agent/server.test.mjs は CI で走らないため、手元で流した生の出力を PR に添える。
- 3 か所（容器・backend・画面）の code の対応は、それぞれの試験（server.test.mjs・test_assistant_router.py・SecretaryChat.test.tsx）で固定する。
- backend（test.yml）と画面（e2e.yml）の試験は CI で走る。容器の試験 server.test.mjs を流す CI は無い（.github/workflows/ で secretary-agent を指すのは deploy.yml だけ）。なので容器の試験は、実装役と審査役が手元で `node --test` を流し、生の出力を PR に添える。CI に入れるかは別の件として残す（この直しには足さない）。
- 単価の桁は保存側の決まり（invoice.py:35）が正本。画面の判定はその写しなので、カードの試験に 2 けた・3 けたの両方を入れる。

## 8. 外部・過去事例の参照と我々への応用
- 不要。理由: 自社の 3 か所の対応を揃える小さな直しで、判断の根拠は本番で観測した出力（recon 1-1）と保存側の決まり（invoice.py:35）で足りる。

## 9. 設計審査（同じ AI による自己審査）
- 判定: APPROVE。
- 根拠: 成功条件 A1〜A9 はすべて試験か差分で○×が出る。変更は recon の行番号と一致。401 以外を推測で鍵扱いにしていない。危険なパスを含まない。
- 未解決: なし（403・429 の扱いは 4(d) で決めた）。
