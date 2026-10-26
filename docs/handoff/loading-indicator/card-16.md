# 実装カード 段階3 便7b — 使われなくなった読み込み中の言葉と見た目の設定を片付ける

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」（design.md 3-3 便7）、便7 着手 2026-10-26「1」
- 起点: 最新 origin/main（便7a #4767 の合流を含むこと。含まなければ BLOCKED:）。ブランチ `release/loading-button-bin7b`
- 根拠: /tmp/CC報告ファイル/loading-button-bin7/keys.tsv（段階3で消えた参照のうち参照0の52キー）、dyn-hits-for-zero-keys.txt（組み立てキーの疑い）、css.tsv
- 対象ADR: ADR-027（辞書は ja/en 同一キー）・ADR-144
- 作業場所: `bash scripts/new-worktree.sh release/loading-button-bin7b --claude` で作った worktree の絶対パスへ毎回 cd する。使い捨ての worktree を使うときも ~/worktrees 配下に作る。`core.hooksPath` の変更や `--no-verify` で hook を外さない

## 1. 消すもの
(1) 辞書キー: keys.tsv の52キーのうち、§2 の確認をすべて通ったものだけ
- 本体辞書（check-i18n-missing-keys.js が読む ja.json・en.json）と、viewer の辞書（同スクリプトの VIEWER_LOCALE_FILES の ja・en）から、同じキーを同じ commit で消す。viewer_*_line が空のキーは本体だけ、viewer.* の5キーは viewer だけ
- キーを消して親の入れ物が空になったら、その空の入れ物も消す（空の {} を残さない）
(2) CSS: frontend/src/pages/inbox/InboxPage.css の `.outbound-translation-send-btn` の規則（css.tsv で :1775・:1782・:1783 の3規則）。消す前に `git grep -n "outbound-translation-send-btn" origin/main -- frontend/` が CSS の3か所だけであることを確かめる

## 2. 消す前の確認（キーごと。結果を /tmp/CC報告ファイル/loading-button-bin7b/impl/keys-check.tsv に1キー1行）
a. 値: 今の ja・en の値を書き出す。値が読み込み中の言葉（「…中」「...」「Saving…」等）でないものがあれば、消さずに理由を書いて残す
b. 直接の参照: `git grep -nF '"<キー>"' origin/main -- frontend/ e2e/` と `'<キー>'`・`` `<キー>` `` が 0 件
c. 組み立てキーの疑い: dyn-hits-for-zero-keys.txt で1件以上あるキーは、テンプレートの変数が取りうる値の一覧を型・定数から実物で特定し、キーの最後の部分がその一覧に入らないことを示す。示せないものは消さずに残す。少なくとも次を確かめる
  - discordAutoSetup.running: DiscordConfigPage.tsx:312 `discordAutoSetup.${result.status}` の status の型。`running` を取りうるなら消さない
  - productDetail.saving: `productDetail.${field}`（ProductMasterDrawer.tsx:286・ReviewRegisterProductForm.tsx:491）の field の一覧
  - tcgAnalysisReview.productMasterDrawer.saving・adding・checking: ProductMasterDrawer.tsx:264 の blankLabels の値
  - accountSettings.saving・changing: ProfileSectionAvatar.test.tsx:107 の field の値
  - analysisRules.dashboard.importUploading ほか、件数が1以上のものすべて
d. 本体以外の使い道: GAS（gas/ 等）・backend/・scripts/ に同じキー文字列が無いこと（`git grep -nF '<キー>' origin/main` を frontend/ 以外も含めて実行し、辞書ファイル以外の当たりを数える）

## 3. 触らない範囲
- keys.tsv にない辞書キー（参照0の読み込み系45キー keys-loadingish-zero-ref-all.tsv を含む。今回は対象外）
- dist-btn・dist-btn--primary（まだ使われている）。manual-record-save-btn（CSS 定義なし＝消すものが無い）
- .tsx・.ts の中身、金型、scripts/、.github/workflows/
- 辞書の値の書き換え・並べ替え（消すだけ。JSON の整形は既存の書式のまま。他の行の差分を出さない）

## 4. 文書
- design.md 3-3 の「便7a（card-15）…」の行に「便7b（card-16）= 辞書 N キーと CSS 1か所の片付け」を足す（N は実際に消した数）
- 残件の記録として design.md 3-7 の下に次の3つを書く: ①prop の三項（ChannelsPage.tsx:627・:643 の ConfirmModal confirmLabel）は検査の対象外で残っている ②参照0の読み込み系45キーは対象外で残っている ③検査が取りこぼすまれな形4つ（同じ行の JSX テキストに `'` が2つ、テンプレートの入れ子、t の第2引数、i18n.t）
- 本カードを docs/handoff/loading-indicator/card-16.md として同じ PR に入れる
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin7b.md

## 5. 検証（生出力は /tmp/CC報告ファイル/loading-button-bin7b/impl/）
| 基準 | 検証方法 |
|---|---|
| 消したキーが ja/en で同じ | 本体・viewer それぞれ、消す前後のキー集合を平らにして書き出し、「前−後」が ja と en で完全一致し、かつ消したキー一覧と一致する（diff が空） |
| 消し過ぎていない | 「前−後」の件数＝keys-check.tsv で「消す」にした件数。それ以外のキーの値が1つも変わっていない |
| 辞書の検査 | `node scripts/check-i18n-missing-keys.js` が exit 0（欠けなし） |
| 型 | frontend で `npx tsc --noEmit` exit 0 |
| 単体試験 | frontend で `npx vitest run` が pass。落ちたら origin/main の写しでも同じ試験を走らせ、同じ落ち方かを比べて報告する |
| UI ガバナンス | `BASE_SHA=<起点> HEAD_SHA=HEAD node scripts/check-ui-governance.js` exit 0 |
| CSS | `git grep -n "outbound-translation-send-btn" -- frontend/` が 0 件 |
| 範囲 | `git diff origin/main...HEAD --name-only` が 本体 ja/en・viewer ja/en（消すキーがある場合のみ）・InboxPage.css・design.md・card-16.md・台帳 だけ |

## 6. 想定分岐
- §2 で残すキーが出た → 消さずに keys-check.tsv に理由を書いて進める（BLOCKED にしない）。10キー以上残るなら NEEDS_DECISION:
- 消すとビルドや試験が落ちる → そのキーは参照がある。戻して理由を書き、Opus へ BLOCKED:
- JSON を機械で書き直すと他の行の書式が変わる → 機械で書き直さず、該当行だけを消す。差分が消したキーの行（と空になった入れ物の行、直前の行末の `,`）だけであることを `git diff` で確かめる
- viewer の辞書の場所が check-i18n-missing-keys.js から特定できない → BLOCKED:
