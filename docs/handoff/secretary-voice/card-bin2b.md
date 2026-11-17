---
mode: handoff
---
# 実装カード 便2b: 返事を待つ間に「声で返事」を変えたときの読み上げの直し

親: [design.md](./design.md) §3・§9（V3）・§12。前の便: [card-bin2.md](./card-bin2.md)（#5579 本番反映済み）

- 状態: カード作成済み（2026-11-17 Opus）。PO 実装承認: 2026-11-17 の便2 完了報告への PO の答え「1. 小さな直しを先に済ませる。そのあと鍵を置く相談に進む【おすすめ】」。便3（本番の鍵）の GO は兼ねない。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: A（画面の 1 ファイルと試験の 1 ファイルだけ。`migrations/`・`deploy.yml`・本番 `scripts/`・backend を触らない）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力） | ○（§7） |
| 4 | 1便1目的（待つ間の切り替えの直しだけ） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外のファイルが無いこと） | ○（§5 手順6） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4・§6） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。

基準: origin/main 3164c872a（2026-11-17・便2 #5579 合流後）。行番号はこの時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便2b で起きること）

便2 の審査役（opus）の任意指摘 1 の直し。今の `SecretaryChat.tsx` は、送った瞬間の「声で返事」の値（`voiceOn`）を返事が届いた後に使う。そのため:

- (a) 送った後・返事が届く前に「声で返事」を切ると、読み上げの部品がもう閉じているのに読み上げを頼み、「声を出せませんでした」の行が出る（`useSecretaryVoice.ts` の `speak` は音の箱が無いと `"failed"` を返す）。
- (b) 返事を待つ間に窓を閉じ、開き直して「声で返事」を入れると、閉じる前の古い返事が読み上げられうる。

直した後: 読み上げを頼むかどうかは「返事が届いた時点の」切り替えの値で決める。窓を閉じる前に送った返事は、開き直した後に読み上げない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `frontend/src/features/secretary/SecretaryChat.tsx` | §3-1 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | §3-2（`SecretaryChat voice reply` の describe の末尾に 2 件足すだけ） |
| `docs/handoff/secretary-voice/card-bin2b.md` | このカード（手順1 の早送りで入る。中身は変えない） |

`useSecretaryVoice.ts`・翻訳キー・CSS は変えない。

## 3. 作るものの決まり

### 3-1. `SecretaryChat.tsx`

- `import { Fragment, useRef, useState } from "react";` はそのまま（`useRef` は既にある）。
- `const nextId = useRef(1);` の次に 2 つ足す:
  - `const voiceOnRef = useRef(false);` （今の「声で返事」の値。画面の再描画を待たずに読む）
  - `const session = useRef(0);` （窓を閉じるたびに 1 増やす。閉じる前に送った返事を見分ける）
- `close` の中で `setVoiceOn(false);` の直前に `voiceOnRef.current = false;` と `session.current += 1;` を足す。
- `onVoiceChange` の中で `setVoiceOn(next);` の直前に `voiceOnRef.current = next;` を足す。
- `send` の中で、`setSending(true);` の直後に `const sentIn = session.current;` を足す。
- `send` の中の読み上げの 2 か所の条件を変える:
  - 変更前 `if (voiceOn && reply.draft.ask) void speakFor(...)` → 変更後 `if (voiceOnRef.current && sentIn === session.current && reply.draft.ask) void speakFor(...)`（中の引数は変えない）
  - 変更前 `if (voiceOn) void speakFor(pendingId, reply.draft.reply);` → 変更後 `if (voiceOnRef.current && sentIn === session.current) void speakFor(pendingId, reply.draft.reply);`
- `markCreated` の中: 変更前 `if (voiceOn) void speakFor(...)` → 変更後 `if (voiceOnRef.current) void speakFor(...)`（中の引数は変えない）。
- `Toggle` の `checked={voiceOn}` と `useState` の `voiceOn` はそのまま残す（画面の表示に使う）。
- 注記は日本語 1 行で足してよい（例: `// 返事が届いた時点の値で決める（送った時点の値を使わない）`）。画面の文字は増やさない。

### 3-2. 試験（`SecretaryChat.test.tsx` の `SecretaryChat voice reply` の末尾）

既存の V3-a〜e と同じ書き方（`renderChat`・`openChat`・`mock.postWithTimeout`・`mock.speech`）で 2 件足す。返事を待たせるには、`mock.postWithTimeout` に、外から解決できる Promise を返させる（`let resolveReply!: (v: unknown) => void; mock.postWithTimeout.mockReturnValue(new Promise((r) => { resolveReply = r; }));`）。

- `V3-f: turning the toggle off while waiting neither asks for speech nor shows the failure line`
  入れる → 送る → 返事が届く前に切る → `resolveReply({ kind: "unknown", draft: { reply: "late reply" }, candidates: none })` → `await screen.findByText("late reply")` → `expect(mock.speech).not.toHaveBeenCalled()` と `expect(screen.queryByText(i18n.t("secretary.voiceFailed"))).toBeNull()`。
- `V3-g: a reply sent before closing is not read aloud after reopening with the toggle on`
  入れる → 送る → 閉じる（`/close/i` のボタン）→ 開き直して入れる → `resolveReply({ kind: "unknown", draft: { reply: "old reply" }, candidates: none })` → 約束が片付くのを待つ（`await waitFor(() => expect(mock.postWithTimeout).toHaveBeenCalled())` の後に `await Promise.resolve()` を 2 回）→ `expect(mock.speech).not.toHaveBeenCalled()`。

既存の試験・期待値は書き換えない。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントや python/cat で書かない。
- PR は作らない（§6）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／§2 の表に無いファイルを変えないと試験・確かめが通らないとき／新しい部品（`package.json` の変更）が要ると分かったとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く。
- 画面の文字は `t()`。色・寸法はトークンだけ。金型（`components/`）を変えない。
- 本番・Google に接続しない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降は毎回その作業場所へ cd してから流す。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/secretary-voice-bin2b
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。違えば NEEDS_DECISION: で止まる。
    cd 作業場所 && git merge --ff-only origin/release/secretary-voice-bin2b-card
    期待する出力: このカードを足す commit 1 つが早送りで入る。早送りにならなければ NEEDS_DECISION: で止まる。

手順1.5 部品を入れる
    cd 作業場所/frontend && npm ci

手順2 §3-1・§3-2 を作る。

手順3 画面の確かめ
    cd 作業場所/frontend && npx tsc --noEmit -p tsconfig.json
    cd 作業場所/frontend && npm run check:all
    期待する出力: どちらも失敗 0。

手順4 画面の試験
    cd 作業場所/frontend && npx vitest run src/features/secretary --reporter=verbose
    期待する出力: 全部 passed。V3-a〜g の 7 件の名前が passed の行に出ること。

手順5 commit
    cd 作業場所 && git add frontend/src/features/secretary/SecretaryChat.tsx frontend/src/features/secretary/SecretaryChat.test.tsx
    commit 文は Write でファイルに書き（1行目 `fix: secretary read-aloud uses the toggle value at reply time (bin2b)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat

手順6 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表の 3 ファイルだけ。表に無いファイルがあれば名前を書いて止まる。

手順7 push（PR は作らない）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/secretary-voice-bin2b
    期待する出力: 手順5 の commit と同じ番号。

## 6. 受入条件と PR

| 基準 | 検証方法 |
|---|---|
| 待つ間に切ると、読み上げの頼み 0 回・失敗の行が出ない | V3-f（CI・名前つき） |
| 閉じる前に送った返事は、開き直して入れても読み上げない | V3-g（CI・名前つき） |
| 今までの V3-a〜e と全試験が変わらず通る | CI 全緑 |
| 触るのは §2 の 3 ファイルだけ | Opus が `git diff --stat` で照合 |

PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使い ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。欄の良い例: `触るファイル: frontend/src/features/secretary/SecretaryChat.tsx, frontend/src/features/secretary/SecretaryChat.test.tsx`（1行・カンマ区切り）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。`区分: A`・`対象ADR: ADR-1080`・`Opus 審査記録: docs/handoff/secretary-voice/review-opus.md`。

## 7. 報告

- 冒頭に「本報告はカード 便2b（待つ間の切り替えの直し）の実行結果である」と書く。
- 受領確認: 最初に「カード 便2b を受領」と1行書く。
- 手順1・3・4・5・6・7 の要点の行を生で貼る（vitest は V3-f・V3-g の行と最後の要約の行）。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容`。

END OF CARD
