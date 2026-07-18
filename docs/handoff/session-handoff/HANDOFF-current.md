# セッション引き継ぎ書（実測確定版・色実装立て直しフェーズ）

> 【最重要・次セッションの設計パートナーへ】
> 本書はリポジトリ実測で書いている。開始時に必ず `git fetch --prune origin` と `git rev-parse origin/main` で現在地確認。
> §6の再検証コマンドで裏取りしてから作業。過去の「マージした」報告を信用しないこと。
> マージ後は必ず SHA前進＋成果物実在を独立実測してから完了とする（前々セッションのマージ誤認の教訓）。

## 基準SHA
origin/main 51f910ed2c434d2f912be098b8869e0e4fd41761

鮮度更新: 51f910ed2c434d2f912be098b8869e0e4fd41761 時点で全項目再実測・事実に変化なし（色実装未反映のまま）

## 0. これまでの経緯（要点）
- 色SSOTの設計・エビデンス初版・コンポーネントSSOT計画は main に在る（本物）。
- だが色SSOTの「実装」（icon集約 / navy別名化 / リンク青 / .tsx関所）は未マージ。OPEN PR #2911 / #2914 / #2926 は main から大きく遅れている。
- 方針決定: 遅れたブランチをこじ開けず、今の main ベースで差分だけ新規実装する（道3・§4.5差分設計）。#2911 / #2914 / #2926 は後でクローズ対象。
- 実測で二重適用リスク無しを確認済み（main の色実装は素の状態＝全部直値hex/直書き色が残る）。
- 前版の引き継ぎ書では `TSXGUARD_NOT_IN_MAIN` / `HANDOFF_ON_MAIN` を取り違えたため、本版は `origin/main` の現在値で再確定した。

## 1. 今やろうとしている作業（色実装の立て直し・未反映3項目）
今の main に、以下3項目を差分として当て直す。設計docは既に main に在るので設計不要・実装のみ。

### ① icon色トークン集約（多ファイル・要対応表転記）
- `index.css` に `--icon-*` を定義（設計doc §3-1 のとおり。nav/action/status/decorative系。ライト/ダーク両方・値は既存土台トークン参照）。
- 設計doc §3-2 の「10箇所の集約対応表」に沿って生指定を `var(--icon-*)` に置換。
- 生指定の実箇所: `frontend/src/constants/icons.tsx:320` の `color="white"`（PlatformIcon）→ `--icon-platform-mail`。他は §3-2 の10行（`.icon-btn/components.css`, `.sidebar-item/sidebar.css`, `.nav-item-list__item/mobile-shell.css`, `.db-section-icon/DashboardPage.css`, `.inbox-search-icon`・`.karte-lock-icon`/InboxPage.css, `.comp-empty__icon/EmptyState.css`, `.comp-badge/Badge.css`, `GoogleCalendarStatusBar.tsx:123-173`）。
- 正: `docs/specs/design-tokens-ssot/color/icon/design.md`（§3-1定義・§3-2対応表・§5受入基準）。実装カードには対応表を逐語転記すること（推測置換禁止）。

### ② navy別名の一本化（見た目不変・index.css 1ファイル）
- ライト: `--indicator` / `--sidebar-item-active-color` / `--sidebar-item-active-border` の `#1e3a8a` → `var(--accent)`。
- ダーク: `--indicator:#5b8dd9` / `--sidebar-item-active-border:#5b8dd9` → `var(--accent)`。
- 保持: ダーク `--sidebar-item-active-color:#93c5fd` は役割違いで独立（統合しない）。

### ③ リンク青（index.css 1ファイル）
- ライト `--link:#1e3a8a` → `#1a73e8`（Google青）。ダーク `--link:#7baee0` は据え置き。

## 2. 未決の分岐（次セッションでPOに諮る）
実装の分け方が未決:
- A案: 3項目を1本の差分PRで当てる（gate 1回・①の対応表転記でカード大）。
- B案（設計パートナー推奨）: 軽い②③（index.css 1ファイル単純置換）を先に1本、①icon集約（多ファイル・複雑）を次に1本。①の複雑さを②③と混ぜない。
→ PO の選択待ちで中断。

## 3. gate要件（新規PRに必要・設計docが在るので満たせる）
- 触るファイル宣言（PR本文）、対象ADR: ADR-067、recon: docs/handoff/color-tokens-ssot/recon.md、設計: docs/specs/design-tokens-ssot/color/icon/design.md。
- `frontend/src` を触る＝PO自筆 GO #番号 必須。
- 受入基準（icon）: `color="white"` 等 0件 / `index.css` に `--icon-*` 定義本数 / §3-2 の10箇所全置換 / `guard-hex-increase` pass。

## 4. その後の宿題（順序）
- 3項目マージ後: OPEN PR #2911 / #2914 / #2926 を正式クローズ。#2924 すり替わり（head=`release/inbox-invoice-form-send-design`・`.tsx`ガード成果物なし）を調査。
- `.tsx` 色ガード（block版 `check-tsx-style-colors.js`）は main 未導入。#2926 相当を今の main ベースで入れ直す要否を判断。
- コンポーネントSSOT化（`PLAN.md`）: 優先1「ページタイトル」深掘りrecon から。
- 保留: §4.5 本文に第4状態「不明」追記（危険操作・要GO）、design-system README §15 に `PLAN.md` リンク追記。

## 5. main に確実に在るもの（実測 EXISTS・信頼できる完了）
- `design-partner.md` §4.5 / `design-phase-definition.md` / `SSOT-EVIDENCE.md` / `component-ssot/PLAN.md` / `icon/design.md` / `ideal-state.md`。

## 6. 再検証コマンド（本書の真偽を次セッションが自分で確かめる）
- 色実装反映: `git show origin/main:frontend/src/index.css | grep -E "\-\-icon-nav:|\-\-link:\s*#1a73e8"`（空なら未反映のまま＝本書と整合）
- 設計doc: `git cat-file -e origin/main:docs/specs/design-tokens-ssot/color/icon/design.md`
- OPEN PR: `for p in 2911 2914 2926; do gh pr view $p --json state,headRefName; done`
- icon対象: `grep -rn 'color="white"' frontend/src --include=*.tsx`

## 7. 運用の約束（不変）
- 事実はリポジトリ実測を正とする。マージは独立実測（SHA 前進＋成果物実在）で確認。
- 1ターン1決定・PO 短合意・カード方式（先頭に定型文）。正本編集/危険操作は PO自筆 GO #番号 必須。書類は GO 不要。
- 設計パートナーは repo を読まない。事実確認は実装役(shingo-cc)に列挙して任せる。

## 8. 実測ログ（証跡・改ざん検出用）
```text
BASE=51f910ed2c434d2f912be098b8869e0e4fd41761
== 色実装が main に入っていないことの再確認 ==
0
== 設計docは在るか ==
ICON_DESIGN_EXISTS
== OPEN PR状態 ==
#2911 OPEN head=release/color-tokens-ssot-merge
#2914 OPEN head=release/color-token-dedup
#2926 OPEN head=release/guard-tsx-style-color
== color=white 生指定の残り（icon集約の対象） ==
frontend/src/constants/icons.tsx:320:        <EnvelopeIcon width={iconSize} height={iconSize} color="white" aria-hidden="true" />
== 現行 handoff の基準SHA 行（更新後） ==
9:origin/main 51f910ed2c434d2f912be098b8869e0e4fd41761
```

## 9. 次セッションでの確認ポイント
- `main` は未反映のままなので、まずは `color="white"` の icon 集約と `index.css` の navy/link 差分を新規実装する。
- `TSXGUARD_NOT_IN_MAIN` は前版の誤認で、実際には `.tsx` 関所は未導入。実装カードではその前提で書くこと。
- コンポーネントSSOTは計画書まで完了。次は「ページタイトル」の深掘りrecon から入る。
