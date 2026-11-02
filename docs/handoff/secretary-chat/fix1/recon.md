# 秘書チャット 直し1 — 現在地（recon）

親: docs/handoff/secretary-chat/design.md（第3版）・ADR-1056
土台: origin/main d97928fa7bd91639b3880f882c46babff22ee548（2026-11-02 08:40 JST に fetch）
調べた人: 設計担当（Opus）。行番号はすべて上の土台。

## 0. 既存 ADR の検索
- `git grep -i -l "secretary" docs/adr/` → ADR-1056-secretary-chat.md だけ。失敗の言葉の決まりは ADR に無く、設計 design.md §5-7 にある。
- 請求書の単価の桁: ADR に記載なし。正本は backend の受け口の検査（下の 2-1）。

## 1. 鍵が使えないときの文言

### 1-1 本番で起きたこと（観測）
- 2026-11-01 PO の頼み「あした10時に打ち合わせの予定を入れて」に、画面は「うまく読めませんでした。言い方を変えてください」と出した。
- 本番の容器の中で、同じ指定の claude を 2 回動かした生の出力（scratchpad の secretary-repro1.txt。鍵の値は含まない）:
  - 標準出力は 1 行の JSON。`"is_error":true`・`"api_error_status":401`・`"result":"Failed to authenticate. API Error: 401 OAuth access token is invalid."`・`"terminal_reason":"api_error"`。
  - 終了コードは 1（`exit1=1`・`exit2=1`）。
  - claude のバージョンは `secretary-agent/Dockerfile` の 2.1.314。
- 2026-11-02 08:13 に PO が鍵を作り直して置き直した後、08:25 の頼みは 秘書 200・予定作成 201 で成功（`tenant_004.calendar_events` id=10「打ち合わせ」2026-11-03 01:00 UTC）。

### 1-2 今の流れ（コード）
- `secretary-agent/server.mjs:95` 終了コードが 0 以外なら、標準出力を読まずに 502 `{"code":"cli_failed"}`。
- `secretary-agent/server.mjs:83` 標準エラーは捨てる（`stdio: ["pipe","pipe","ignore"]`）。
- `secretary-agent/server.mjs:139` 容器のログは「秒・code」の 1 行。
- `backend/app/routers/assistant.py:103-111` 容器の 502 は、`cli_failed` でも `unreadable` でも画面へ 502 `unreadable`。ログの code だけ `cli_failed` に分ける。
- `frontend/src/features/secretary/secretaryApi.ts:58-63` 画面が知っている code は `not_ready`・`busy`・`timeout`・`unreadable` の 4 つ。それ以外は `generic`。
- `frontend/src/locales/ja.json` の `secretary.error.unreadable` =「うまく読めませんでした。言い方を変えてください」、`generic` =「うまくいきませんでした。もう一度お試しください」。
- 設計 `docs/handoff/secretary-chat/design.md:90`・`:93`・`:165` は、トークン切れでも利用者には unreadable を出すと決めていた（第1段は PO だけなので許す、とした）。今回これを変える。

### 1-3 試験
- `secretary-agent/server.test.mjs:153-165` 偽の claude が出力なしで exit 3 → 502 `cli_failed`。
- `backend/tests/test_assistant_router.py:168-169` 容器 502 `cli_failed`・`unreadable` → 画面 502 `unreadable`。
- `backend/tests/test_assistant_router.py:239-247` `cli_failed` はログの code が `cli_failed`。
- `frontend/src/features/secretary/SecretaryChat.test.tsx:158` 503 not_ready の言葉、`:165` それ以外は generic。

### 1-4 配備
- `.github/workflows/deploy.yml:659-687` 配備のたびに secretary-agent のイメージを作り直し、`--force-recreate` で起こし直す。容器の直しは main に入れば配備で入る。deploy.yml は今回触らない。

## 2. 単価の小数

### 2-1 受け口の決まり
- `backend/app/schemas/invoice.py:35` `unit_price: Decimal = Field(ge=0, max_digits=15, decimal_places=2)`。小数 3 けた以上は 422。

### 2-2 秘書の下書き
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:38-41` `isValidUnitPrice` は「空でない・数・0 以上」だけ。小数の桁を見ない。
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:155-162` 単価の欄は `type="number" min={0}`。`step` は無い。
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:49` AI の下書きの単価は `String(i.unit_price)` で欄に入る（例: 1000.255 → "1000.255"）。
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:94` 送るのは `Number(i.unitPrice)`。
- `frontend/src/features/secretary/SecretaryDraftInvoice.tsx:172` 単価が空の行があると `secretary.priceRequired` の案内。
- `secretary-agent/schema.json:23` AI の答えの単価は `number|null`（桁の制限なし）。

### 2-3 ふだんの請求書作成画面（変えない・参考）
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:389` 単価の欄は `step="0.01"`。

## 3. 観測・仮説・未確認
- 観測: 鍵が無効のとき claude 2.1.314 は exit 1 で、標準出力の JSON に `api_error_status: 401` を出す（1-1）。
- 未確認: 有料プランが無いアカウントの鍵や、使用量の上限のときに出る `api_error_status` の値。今回は 401 だけを「鍵が使えない」とし、ほかはすべて「別の理由で止まった」に入れる（推測で 403・429 を鍵扱いにしない）。
