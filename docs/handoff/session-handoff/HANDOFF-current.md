# セッション引き継ぎ書（実測確定版）

> 【最重要・次セッションの設計パートナーへ】
> 本書は「設計パートナーの記憶」ではなく「リポジトリ実測」で書いている。
> 開始時に必ず: `git fetch --prune origin && git rev-parse origin/main` で現在地を確認。
> §5の再検証コマンドで本書の記載を自分で裏取りしてから作業すること。記憶や過去の「マージした」報告を信用しないこと（下記の教訓参照）。

## 基準SHA
origin/main 633a64a527ce00e7bc954d341772b97b06af31d0

## 0. 前セッションの重大な教訓（必読）
前セッションでは、設計パートナーが複数のPRを「マージ成功」と扱ったが、実測すると未マージ（OPEN）だった。原因: マージカード実行後、実装役の「MERGED」報告を、`origin/main` のSHA前進・成果物実在の独立実測で裏取りせずに完了扱いした。
→ 対策（次セッションの鉄則）: マージ後は必ず「`git rev-parse origin/main` が前進したか」「成果物が `git cat-file -e origin/main:<path>` で在るか」を独立実測してから完了とする。report の MERGED を鵜呑みにしない。

## 1. main に確実に在るもの（実測 EXISTS・信頼できる完了）
- 設計手順SSOT: `docs/ai-agents/design-partner.md` §4.5「designモードの定義（差分設計）」実在（SEC45_OK）。
- 記録: `docs/specs/design-partner-loop/design-phase-definition.md`（§4.5全部入り記録・テスト走行§11含む）。
- 色SSOTエビデンス初版: `docs/handoff/color-tokens-ssot/SSOT-EVIDENCE.md`。
- コンポーネントSSOT全体計画: `docs/specs/design-system/component-ssot/PLAN.md`。
- `docs/ai-agents/design-partner.md` §6 に逐語検収の空行diff教訓。
→ つまり「決めたこと・記録・計画・設計手順」は本物。

## 2. 未マージ（OPEN PR・実装は main に入っていない・要マージ検証）
- #2911 色トークンSSOT統合（icon/navy/tokens-cal/design 4本）: OPEN / head=`release/color-tokens-ssot-merge` / NOT_IN_MAIN。
- #2914 色トークン辞書整理（別名化＋リンクGoogle青）: OPEN / head=`release/color-token-dedup` / NOT_IN_MAIN。
- #2926 色エビデンス更新（.tsxスコープ＋関所§7追記）: OPEN / head=`release/guard-tsx-style-color` / NOT_IN_MAIN。
- #2924 は `MERGED` だが head が `release/inbox-invoice-form-send-design` で、`check-tsx-style-colors.js` は main に存在せず・workflow接続もなし。→ 実質「.tsx色ガードは未導入」。要調査（PR番号と中身の対応が壊れている疑い）。
→ 実測事実: main の `index.css` に `--icon-*` / リンク青 / 別名化 は入っていない。.tsx 色ガードのスクリプトも無い。

## 3. 色SSOTの正しい現在地（誇張なし）
- 「決めたこと・設計・エビデンス初版」は在る。「色統合・辞書整理・リンク青・.tsx関所」の実装は未マージ。
- 前セッションで報告した「色SSOT完成」は実装が入っていないため未達。OPEN の PR は生存しているので、正しくマージし直せば復元可能（ブランチは消えていない）。
- 次の一手候補: #2911 → #2914 → #2926 を順に、マージ後の独立実測付きで正式に main へ入れる。ただし各PRの CI 現況（GO 要否・gate 赤）を先に実測すること。

## 4. 進行中/未着手テーマ
- 進行中: コンポーネントSSOT化（PLAN.md）。次アクション=優先1「ページタイトル」の深掘りrecon。
- 未反映の宿題: §4.5 本文へ第4状態「不明」追記（保留）／design-system README §15 に PLAN.md リンク追記／px撲滅はコンポーネントSSOTに吸収。
- 別テーマ（今日未着手）: DB設計SSOT 等。

## 5. 再検証コマンド（本書の真偽を次セッションが自分で確かめる）
- 色実装が入ったか: `git show origin/main:frontend/src/index.css | grep -E "\-\-icon-nav:|\-\-link:\s*#1a73e8"` （空なら未マージのまま）
- `.tsx` ガード: `git ls-tree -r --name-only origin/main | grep tsx-style-colors` （無ければ未導入）
- OPEN PR: `for p in 2911 2914 2924 2926; do gh pr view $p --json state,headRefName; done`
- §4.5: `git show origin/main:docs/ai-agents/design-partner.md | grep "^## 4.5"`
- 計画書: `git cat-file -e origin/main:docs/specs/design-system/component-ssot/PLAN.md`

## 6. 運用の約束（不変）
- 事実はリポジトリ実測を正とする（報告・記憶より実測）。マージは独立実測で確認。
- 1ターン1決定・PO短合意・カード方式（先頭に定型文）。正本編集/危険操作は PO自筆 GO #番号 必須。書類はGO不要。
- 設計パートナーはrepoを読まない。事実確認は実装者(shingo-cc)に列挙して任せる。

## 7. 実測ログ（証跡・改ざん検出用）
```text
BASE=633a64a527ce00e7bc954d341772b97b06af31d0
== 確実にmainに在る文書（EXISTS確認） ==
EXISTS: docs/ai-agents/design-partner.md
EXISTS: docs/specs/design-partner-loop/design-phase-definition.md
EXISTS: docs/handoff/color-tokens-ssot/SSOT-EVIDENCE.md
EXISTS: docs/specs/design-system/component-ssot/PLAN.md
112:## 4.5 designモードの定義（差分設計）
SEC45_OK
== 未マージOPEN PR の状態 ==
#2911 OPEN head=release/color-tokens-ssot-merge merged=null
#2914 OPEN head=release/color-token-dedup merged=null
#2924 MERGED head=release/inbox-invoice-form-send-design merged=2026-07-15T12:44:15Z
#2926 OPEN head=release/guard-tsx-style-color merged=null
== 色実装が main に入っていないことの確認 ==
0
TSXGUARD_NOT_IN_MAIN
```

## 8. 次セッションでの確認ポイント
- `TSXGUARD_NOT_IN_MAIN` は現時点の `origin/main` の事実。文書化された意図と一致しないため、PR #2924 の取り込み状況とワークツリーの状態を再確認すること。
- コンポーネントSSOTは計画書まで完了。次は「ページタイトル」の深掘りrecon から入る。
