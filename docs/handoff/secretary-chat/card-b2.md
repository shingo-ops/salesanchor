# 実装カード B2 — 画面のチャットの窓（右下の印から開く）

親: docs/handoff/secretary-chat/design.md（第3版）§5-1・§5-5〜§5-7・§11 段2 ／ ADR-1056・ADR-027・ADR-144・ADR-067
前提: カード A（金型 `FloatingActionButton`・`ChatBubble`）とカード B1（`POST /api/v1/assistant/messages`）が main に入っていること。入っていなければ始めずに `BLOCKED:` で止める。
状態: 設計担当（Opus）作成。実装は Sonnet。PO の実装承認: 2026-11-01「…PRマージ、デプロイまで完走させてくれ」。画面だけの変更。

## 0. 始める前に
- `origin/main` から `bash scripts/new-worktree.sh release/secretary-chat-window --claude`。`./scripts/dev/executor-preflight.sh || exit 1`。
- `frontend/CLAUDE.md`・`docs/CC_UI_GOVERNANCE.md` を読む。

## 1. 作るもの・変えるもの（これ以外は触らない）
| ファイル | 中身 |
|---|---|
| `frontend/src/lib/api.ts` | `request` に 3 つ目の引数 `timeoutMs: number = FETCH_TIMEOUT_MS` を足し、`setTimeout(..., timeoutMs)` に使う。`api` に `postWithTimeout: <T>(path, data, timeoutMs: number) => request<T>(path, {method:"POST", body: JSON.stringify(data)}, timeoutMs)` を足す。今の呼び出しの動きは変えない |
| frontend/src/features/secretary/SecretaryChat.tsx・.css（新規） | 印と窓のまとまり。下の 2 |
| frontend/src/features/secretary/SecretaryDraftInvoice.tsx・SecretaryDraftEvent.tsx（新規） | 下書きの形。下の 3 |
| frontend/src/features/secretary/secretaryApi.ts（新規） | 口の呼び出しと型 |
| frontend/src/features/secretary/SecretaryChat.test.tsx（新規） | 下の 5 |
| `frontend/src/App.tsx` | `ShellSwitch`（`frontend/src/App.tsx:140-143`）を `<>{isMobile ? <MobileShell /> : <DesktopShell />}<SecretaryChat isMobile={isMobile} /></>` にする |
| `frontend/src/locales/ja.json`・`en.json` | `secretary` の名前空間を足す（同じキー） |

frontend/src/features/ が今の作法に無い置き場なら、今ある機能の置き場（`frontend/src/pages/` や `frontend/src/components/` の使い分け）を実物で確かめ、`frontend/CLAUDE.md` の決まりに合わせる。決まりで決められなければ止めて報告。

## 2. SecretaryChat
- 出す条件: `useFeatures().isEnabled("secretary_chat")` と `useSuperAdmin()` が両方 true のときだけ。読み込み中は出さない（`frontend/src/hooks/useFeatures.ts`・`frontend/src/hooks/useSuperAdmin.ts`）。
- 印: 金型 `FloatingActionButton`（`label={t("secretary.open")}`、`aboveTabbar={isMobile}`、アイコンは今のアイコンの決まり（`frontend/CLAUDE.md`）のチャットの印）。
- 窓: 金型 `Drawer`（`frontend/src/components/Drawer.tsx`）を右から開く。題名 `t("secretary.title")`。
- 会話: `useState` の配列だけ（保存しない。閉じたら消す）。吹き出しは金型 `ChatBubble`。
- 入力: 金型 `Textarea`（`frontend/src/components/Textarea.tsx`）と金型 `Button`。1000 字まで。送信中は入力と送信を止め、AI 側の吹き出しに `status="sending"`。
- 呼び出し: `api.postWithTimeout("/assistant/messages", {text}, 100_000)`。
- 失敗: `ApiError` の `detail.code` で `secretary.error.notReady`・`busy`・`timeout`・`unreadable` を出す。それ以外と通信の失敗は `secretary.error.generic`。403 は印を消す。
- AI の文字（`unknown.reply` を含む）は React の文字としてだけ出す（`dangerouslySetInnerHTML`・Markdown の描画を使わない）。

## 3. 下書き（送る欄は全部見せて、全部直せる）
- 請求書（SecretaryDraftInvoice）:
  - 会社と担当者: `candidates` が 1 件ずつならそれを選んだ状態。複数なら選ばせる（今の select の金型）。0 件、または利用者が変えたいときは `frontend/src/components/CompanyContactSelector.tsx` を使う。
  - 品物の行: 名前・数・単価。単価が空の行があれば「作る」を押せない。
  - 通貨（初期 JPY）・期日・メモ。
  - 会社と担当者の両方が決まるまで「作る」を押せない（`backend/app/schemas/invoice.py:41-42` で必須）。
  - 「作る」: 今の請求書の作成の呼び出し（今の請求書の画面が使っている関数があればそれ。無ければ `api.post("/invoices", {...})`）。送るのは company_id・contact_id・currency・due_date・notes・items だけ。
- 予定（SecretaryDraftEvent）:
  - 題名・始まり・終わり・終日・場所・説明・見える範囲（`personal` が初期。`shared` を選ぶと、その下に `t("secretary.event.sharedNote")`（会社全員に見え、Google にも映る）を出す）。
  - 「作る」: 今の予定の作成の呼び出し（今のカレンダーの画面が使っている関数があればそれ。無ければ `api.post("/calendar/events", {...})`）。
- 作れたら、AI 側の吹き出しに `t("secretary.created.invoice")` か `t("secretary.created.event")` と、その請求書・予定の画面へのリンク（今のルートを実物で確かめる）。失敗したら今の口の detail をそのまま出す。
- 入力欄はすべて今の金型（Input・Select・Textarea・DatePicker 等）。生の input・select は使わない（ADR-144）。

## 4. 言葉（ja/en 同じキー。直書き禁止・ADR-027）
`secretary.open`・`secretary.title`・`secretary.placeholder`・`secretary.send`・`secretary.create`・`secretary.cancel`・`secretary.error.notReady`（準備ができていません）・`secretary.error.busy`（いま考え中です。少し待ってから送ってください）・`secretary.error.timeout`・`secretary.error.unreadable`（うまく読めませんでした。言い方を変えてください）・`secretary.error.generic`・`secretary.invoice.*`（欄の名前）・`secretary.event.*`（欄の名前・sharedNote）・`secretary.created.invoice`・`secretary.created.event`・`secretary.priceRequired`。足りないキーは同じ名前空間に足す。

## 5. 試験（vitest）
- 出す条件: feature なし or super admin でない → 印が無い。両方 → 印がある。
- 送信 → `postWithTimeout` が 100000 で呼ばれる。
- invoice の下書き: 単価空で「作る」が押せない。会社・担当者が決まらないと押せない。押すと `/invoices` に決めた欄だけが送られる。押さなければ呼ばれない。
- event の下書き: 初期の見える範囲が personal。
- 503 `not_ready` で notReady の言葉。
- reply に `<b>x</b>` が来ても文字のまま出る。
- `api.ts`: `request` の既定の打ち切りが今のまま（既存の試験があれば通る）。

## 6. 受入（実装役が自分で流して生の出力を残す）
| 基準 | 検証方法 |
|---|---|
| 試験 | `cd frontend && npx vitest run src/features/secretary src/lib` が通る |
| 型 | `cd frontend && npx tsc --noEmit` |
| 金型外の検査 | `node scripts/check-ui-governance.js` |
| 言葉 | ja/en のキーが同じ（今の i18n の検査があればそれ）。`frontend/CLAUDE.md` の grep のセルフチェックで直書きの日本語 0 件 |
| ダーク | `cd frontend && npm run check:dark-parity` |
| lint | `cd frontend && npx eslint src/features/secretary src/App.tsx src/lib/api.ts` |

## 7. 想定分岐（迷ったら止まる）
- 請求書・予定の作成に今の画面が使う関数が複数ある → 止めて報告。
- `Drawer` の金型が右から開けない・幅の指定ができない → 止めて報告（自作しない）。
- `useFeatures`・`useSuperAdmin` が別々に `/me/permissions` を呼んで 2 回通信になる → そのままでよい（今の作り）。PR 本文に書く。

## 8. 進め方
- コミットの最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- PR 本文の「標準ワークフロー確認」: recon docs/handoff/secretary-chat/recon.md、設計 docs/handoff/secretary-chat/design.md、対象ADR ADR-1056, ADR-027, ADR-144, ADR-067、区分 B-1、触るファイルを全部列挙。
- マージしない。終わったら PR の URL と受入の生の出力の置き場を返す。
