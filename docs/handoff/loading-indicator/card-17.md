# 実装カード 段階3 便8a — 確認の小窓の確定ボタンに「押している間」を渡す口を足し、チャンネル画面の2か所を丸＋元の言葉にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」、便7のあとの残件着手 2026-10-26「1」
- 起点: 最新 origin/main（便7b #4774 合流 59202abec を含むこと。含まなければ BLOCKED:）。ブランチ `release/loading-button-bin8a`
- 根拠: /tmp/CC報告ファイル/loading-button-bin8/recon/（A2-ConfirmModal.tsx.txt・A1-channelspage-612-660.txt ほか）
- 対象ADR: ADR-144（UI ガバナンス・金型）・ADR-027
- 作業場所: `bash scripts/new-worktree.sh release/loading-button-bin8a --claude` で作った worktree の絶対パスへ毎回 cd する。`core.hooksPath` の変更や `--no-verify` で hook を外さない
- 便8 の分け方（Opus 判断）: 便8a＝本カード（金型の口と2か所）。便8b＝使われない辞書キーの片付け（本カードで参照0になる channels.disconnecting・channels.discordDisconnecting も 8b で扱う）。便8c＝検査の取りこぼし4形。理由: 金型の変更・削除・検査は壊れ方と戻し方が違うため1つずつ変える

## 1. 変更
(1) frontend/src/components/ConfirmModal.tsx
- Props に `confirmLoading?: boolean` を足す（コメント: 押した処理が終わるまで確定ボタンに丸を出し押せなくする。既定 false（後方互換））
- 分割代入に `confirmLoading = false` を足す
- 確定の `<Button>`（:38-46）に `loading={confirmLoading}` を足す。`disabled={confirmDisabled}` はそのまま。言葉 `{resolvedConfirmLabel}` もそのまま
- 取消ボタン・Modal・それ以外は触らない

(2) frontend/src/pages/channels/ChannelsPage.tsx
- :627 `confirmLabel={disconnecting ? t("channels.disconnecting") : t("channels.disconnect")}` → `confirmLabel={t("channels.disconnect")}` と `confirmLoading={disconnecting}` の2行
- :643 `confirmLabel={discordDisconnecting ? t("channels.discordDisconnecting") : t("channels.discordDisconnect")}` → `confirmLabel={t("channels.discordDisconnect")}` と `confirmLoading={discordDisconnecting}` の2行

## 2. 実装前の実物確認（結果を /tmp/CC報告ファイル/loading-button-bin8a/impl/precheck.md に）
a. frontend/src/components/Button.tsx の loading の扱い（disabled・aria-busy・Spinner の行番号）を書き写す。loading が disabled を兼ねないなら BLOCKED:
b. ChannelsPage の performDisconnect と handleDiscordDisconnect で、disconnecting / discordDisconnecting を true にしてから小窓を閉じるまでの順番を行番号つきで書く（押している間に小窓が開いたままか）。開いたままでない（先に閉じる）なら、丸は見えないが害はないので進め、その事実を書く
c. ConfirmModal の stories（`git grep -ln "ConfirmModal" -- frontend/src '*.stories.tsx'`）があるか。あれば §3 のとおり足す
d. 対象外2件の確認: ProfileSection.tsx:145 の labels.uploading が AvatarUpload の中でどの要素に出るか、ExtractionErrorLogPanel.tsx:357 の emptyState がどの要素に出るか、行番号つきで書く。どちらかが `<button>` か金型 Button の中の言葉なら NEEDS_DECISION:（今回は直さない）

## 3. 試験・見本
- 試験: ConfirmModal の確定ボタンについて、`confirmLoading` 指定なしで aria-busy なし・押せる（今と同じ）、`confirmLoading` true で aria-busy="true"・押せない・言葉は confirmLabel のまま・丸（Spinner）がある、の2件を足す。置き場所は既存の SharedButtonMigration.test.tsx に ConfirmModal の試験があればそこ、無ければ frontend/src/components/ConfirmModal.test.tsx を新しく作る
- 見本: §2c で stories があれば、confirmLoading true の見本を1つ足す。無ければ作らない

## 4. 触らない範囲
- 辞書（channels.disconnecting・channels.discordDisconnecting はまだ消さない。便8b で扱う）
- ConfirmModal を使う他の 48 か所、Button.tsx、Modal.tsx、scripts/、.github/workflows/
- ProfileSection・ExtractionErrorLogPanel（§2d の確認だけ）

## 5. 文書
- design.md 3-7 の残件①（prop の三項）の行に「便8a（card-17）で ConfirmModal に confirmLoading を足し、ChannelsPage の2か所を直した」を足す
- 本カードを docs/handoff/loading-indicator/card-17.md として同じ PR に入れる
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin8a.md

## 6. 検証（生出力は /tmp/CC報告ファイル/loading-button-bin8a/impl/）
| 基準 | 検証方法 |
|---|---|
| 2か所の三項が消えた | `git grep -n "disconnecting ?" -- frontend/src/pages/channels/` と `git grep -n "Disconnecting ?" -- frontend/src/pages/channels/` が 0 件 |
| 口が渡っている | `git grep -n "confirmLoading" -- frontend/src` が ConfirmModal.tsx（型・分割代入・Button へ渡す行）と ChannelsPage.tsx の2行と試験だけ |
| 他の使い方が変わらない | 既存試験（SharedButtonMigration.test.tsx ほか）が pass |
| 型 | frontend で `npx tsc --noEmit` exit 0 |
| 単体試験 | frontend で `npx vitest run` pass。落ちたら origin/main の写しでも同じ試験を走らせ、同じ落ち方かを比べて報告する |
| 辞書 | `node scripts/check-i18n-missing-keys.js` exit 0 |
| UI ガバナンス | `BASE_SHA=<起点> HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が ConfirmModal.tsx・ChannelsPage.tsx・試験1ファイル・（stories があれば）stories・design.md・card-17.md・台帳 だけ |

## 7. 想定分岐
- Button の loading が disabled を兼ねない → BLOCKED:（金型の動きを変える判断は Opus）
- 試験の描画で Modal が portal 等で探せない → 既存の ConfirmModal 試験の探し方に合わせる。それでも探せなければ BLOCKED:
- §2d で対象外2件のどちらかがボタンの言葉 → 直さずに NEEDS_DECISION: で報告して、本カードの残りは進める
