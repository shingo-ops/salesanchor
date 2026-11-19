# 実装カード 便T: 秘書の窓に声の聞き取りの印を付ける（試しの便）

正本: docs/handoff/secretary-voice-input/design.md §14（試しの便）。ADR-1082（Proposed）。
PO の承認: 2026-11-19「1」（無料のやり方で試しの画面から）。
ブランチ: release/secretary-voice-input。行番号は origin/main 21b431389 の値。

## 作業場所の作り方（クラウド）

1. `bash scripts/new-worktree.sh release/secretary-voice-input`（origin/main から同じ名前のブランチを作る）
2. `git -C ~/worktrees/salesanchor/release-secretary-voice-input merge --ff-only origin/release/secretary-voice-input`（設計のコミットを取り込む。ff できなければ BLOCKED:）
3. 以後の作業はすべてこの worktree の中で行う。clone のまま commit しない。

## 触るファイル（これ以外は触らない）

1. nginx/nginx.conf（:100 の 1 行だけ）
2. frontend/src/constants/icons.tsx
3. frontend/src/features/secretary/useSecretaryListen.ts（新規）
4. frontend/src/features/secretary/useSecretaryListen.test.ts（新規）
5. frontend/src/features/secretary/SecretaryChat.tsx
6. frontend/src/features/secretary/SecretaryChat.css
7. frontend/src/features/secretary/SecretaryChat.test.tsx
8. frontend/src/locales/ja.json・frontend/src/locales/en.json（`secretary` の塊の中だけ）

触らない: backend・migrations・.github・`nginx/nginx.conf:323`・useSecretaryVoice.ts・下書きの部品・design.md・ADR。

## 手順

design.md §14-2 の（１）〜（７）を、書かれた順に行う。そこに書いた名前・値・文をそのまま使う。補足は次のとおり。

- （２）`SECRETARY_ICONS` は icons.tsx の末尾の `LeadChatIcon` の前に置く。`Icon` 型は同じファイルが既に読み込んでいるものを使う（無ければ `./icons-base` から型だけ読み込む）。
- （３）部品の型（`SpeechRecognition` など）は lib.dom に無い前提で、同じファイルに最小の interface を書く。`any` は使わない。`start()` の順番は design §14-2（３）の 1〜6 のとおりにする。
- （４）翻訳の鍵の組み立ては、今の `SecretaryChat.tsx:141` と同じ書き方にする。
- （４）入力欄と印は `<div className="secretary-chat__input-row">` で包む。PC（`isMobile=false`）のときも包みは置き、印だけ出さない。
- （５）色・寸法はトークンだけ。数値を直に書かない。
- （７）試験では `window.SpeechRecognition` を偽物の class に差し替え、試験の後で元に戻す。日本語の文字は `String.fromCharCode` で作る。

## 確かめ（commit の前に全部流し、最後の 10 行を報告に貼る）

1. `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/secretary`
2. `cd frontend && npx tsc --noEmit -p .`
3. `cd frontend && npx eslint src/features/secretary src/constants/icons.tsx`
4. `cd frontend && node scripts/check-i18n-missing-keys.js`
5. `git diff --stat origin/release/secretary-voice-input` で触ったファイルが上の 8 種だけであること

## 想定される分岐（当たったらその場で止める）

- `MicrophoneIcon` が `@heroicons/react/24/solid` に無い → BLOCKED:
- IconToggleButton の props が design §14-2（４）と違う → BLOCKED:
- 試験が落ちて直し方が設計に無い → 期待値を書き換えず BLOCKED:
- 見張り・フックに止められた → 言い換えず原文を書いて BLOCKED:

## commit と push

- commit は 1 つ。文の末尾は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- `git -C ~/worktrees/salesanchor/release-secretary-voice-input push origin release/secretary-voice-input`（--no-verify・force を付けない）
- PR は作らない（Opus が作る）。
