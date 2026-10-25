# 実装カード 段4 — frontend・backend の入口をそろえる（AGENTS.md を正本に、CLAUDE.md を取り込みだけに）

> この文書は何か：doc-agenda-nav 段4の作業指示書です。frontend・backend の AGENTS.md・CLAUDE.md を審査済みの案文どおりに入れ替え、ルートの入口から i18n・UI ガバナンスの2節を外し、行数の上限・目次・見張りの一覧・参照を合わせて直します。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §25: 段4の設計判断（この便の根拠）
  - §23: G1・G2（i18n・UI ガバナンスを段4で frontend/AGENTS.md へ移す）
  - §8 段4の行
- K11 の意味の対応表: docs/handoff/doc-agenda-nav/k11-map-stage4.md
- 対象ADR: ADR-1040（Accepted。Consequences に1行追記する）。関連: ADR-076、ADR-027、ADR-144、ADR-034
- 状態: 設計は Opus の設計判断（§25、2026-10-25）。PO の承認は 2026-10-25 の「1」（段4に進み、画面側とサーバー側の入口の文書も同じ形にそろえる）。
- 危険便かどうか: 触るファイルは scripts/check-process-artifacts.js の DANGEROUS_PATTERNS には当たらない（frontend/scripts/ は対象外）。ただし CLAUDE.md・AGENTS.md を触るので docs/ai-agents/executor-checklist.md §2 により GO の記録が要ります。PR 本文に `### GO記録` が要ります。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段4 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れるもの: §3 のファイル。

入れないもの:
- 案文（docs/handoff/doc-agenda-nav/draft/）、design.md、k11-map-stage4.md の変更（Opus がコミット済み）。
- 案文の言い回しの改善（写すだけ）。
- .github/ の全ファイル（migration-guard.yml の参照は見出しが残るので直さない。design.md §25）。
- frontend/eslint.config.js・frontend/scripts/check-css-fixed-position.js・frontend/scripts/check-page-layout.js の「frontend/CLAUDE.md 参照」（取り込みで本文に届く）。
- check-claude-size.js の未登録を見つける処理（:34-46）、claude-md-staleness-check.yml、frontend/.husky（段5）。
- migrations/・ADR-034・ADR-076・ADR-141・backend/tenant/CLAUDE.md・docs/recon・docs/audit。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた。起点は origin/main d7924ae70）

| # | 事実 | 出典 |
|---|---|---|
| F1 | frontend/CLAUDE.md 78行・frontend/AGENTS.md 63行・backend/CLAUDE.md 70行・backend/AGENTS.md 91行・AGENTS.md 53行・CLAUDE.md 9行・docs/INDEX.md 43行。案文 draft/frontend-AGENTS.md 77行・draft/backend-AGENTS.md 70行・draft/frontend-CLAUDE.md 3行・draft/backend-CLAUDE.md 3行 | `wc -l` |
| F2 | AGENTS.md:45 は `- 画面は \`frontend/AGENTS.md\`、サーバー側は \`backend/AGENTS.md\` の決まりにも従う`。:46 は空行、:47 は `## i18n 強制（ADR-027）`、:53 は UI ガバナンスの本文（`UI部品新設時は…詳細: \`docs/CC_UI_GOVERNANCE.md\``）で、:53 がファイルの最終行 | `sed -n '45,53p' AGENTS.md` |
| F3 | CLAUDE.md:7 は `- 作業場所は \`bash scripts/new-worktree.sh release/<topic> --claude\` で作る（\`--claude\` は作った場所で Claude Code を起動する）` | `sed -n 7p CLAUDE.md` |
| F4 | frontend/scripts/check-claude-size.js:28 は `  { path: 'frontend/CLAUDE.md', limit: 90 },`、:29 は `  { path: 'backend/CLAUDE.md', limit: 70 },` | `sed -n '28,29p'` |
| F5 | docs/INDEX.md:22 は `\| D 領域別ルール \| [frontend の決まり](../frontend/CLAUDE.md)・[frontend の AGENTS](../frontend/AGENTS.md) \| frontend/ のファイルを触るとき \|`、:23 は同じ形の backend。:36 は `2. \`frontend/\` だけに関係するか？ → YES: **\`frontend/CLAUDE.md\`** に追加`、:37 は同じ形の backend、:38 は `4. frontend と backend 両方に等しく関係するか？ → YES: **このファイル** に追加（i18n 等）` | `sed -n '22,23p;36,38p'` |
| F6 | .claude/hooks/check-freshness.sh:25 は `RULES="AGENTS.md CLAUDE.md docs/INDEX.md docs/STANDARD-WORKFLOW.md backend/CLAUDE.md frontend/CLAUDE.md"` | `sed -n 25p` |
| F7 | .claude/agents/governance.md:72 は `\| **CLAUDE.md 反映** \| \`grep -n <pattern> CLAUDE.md frontend/CLAUDE.md backend/CLAUDE.md\` \| 該当ルールの記載行 \|` | `sed -n 72p` |
| F8 | docs/onboarding/design-system.md:100 は `\| \`frontend/CLAUDE.md\` \| PageLayout / i18n / アイコンのルール \|` | `sed -n 100p` |
| F9 | docs/adr/ADR-1040-doc-agenda-nav-entry-index.md:46 は `- ADR-076 の §1 ルート行（120行）と §2 の命名の決まりは、本 ADR が Accepted になった時点で本 ADR の Decision 1・2 に置き換わる。frontend・backend の CLAUDE.md の上限と階層の決まりは ADR-076 のまま。` | `sed -n 46p` |
| F10 | 起点の目次の到達検査の SUMMARY は `unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`。起点の `node frontend/scripts/check-claude-size.js` は exit 0・PASSED（警告1行: tools/claude-channels/intake/CLAUDE.md 未登録） | /tmp/CC報告ファイル/an-s4/cdi-before.txt |
| F11 | K11 の検査スクリプト /tmp/CC報告ファイル/an-s4/sim/k11.sh と K3 の検査スクリプト /tmp/CC報告ファイル/an-s4/sim/k3.sh は Opus が作った。案文で試すと K11 は OK=129・MISSING=43、「missing but not in map」が出力なし、「in map but not missing」が `backend/CLAUDE.md:1`・`frontend/CLAUDE.md:1` の2行。K3 は `K3=1`（日本語 files=2 だけ） | design.md §25 |

## 3. 触るファイル（これ以外は触らない）

- 変更: `frontend/AGENTS.md`
- 変更: `frontend/CLAUDE.md`
- 変更: `backend/AGENTS.md`
- 変更: `backend/CLAUDE.md`
- 変更: `AGENTS.md`
- 変更: `CLAUDE.md`
- 変更: `frontend/scripts/check-claude-size.js`
- 変更: `docs/INDEX.md`
- 変更: `.claude/hooks/check-freshness.sh`
- 変更: `.claude/agents/governance.md`
- 変更: `docs/onboarding/design-system.md`
- 変更: `docs/adr/ADR-1040-doc-agenda-nav-entry-index.md`
- 変更: `docs/adr/README.md`（`node scripts/generate-adr-index.js` で作り直すだけ。手で書かない。変化が無ければ触らない）
- 変更: `docs/handoff/doc-agenda-nav/card-stage4.md`（このカード。担当は §11 の報告欄に追記するだけ）
- design.md §25・draft/ の4本・k11-map-stage4.md は Opus がコミット済み。担当は触らない。

## 4. 作り方

行番号はすべて、作業場所の起点（`B=$(git merge-base origin/main HEAD)`）でのもの。zsh では必ず `"${B}:AGENTS.md"` と書く。

### 4-0. .claude/agents/ を変える前に

`git fetch origin main` の後、`git diff "$B" origin/main -- .claude/agents/governance.md` が出力なしであることを確かめる（出力があれば何も変えずに NEEDS_DECISION:）。

### 4-1. frontend・backend の4本を案文で置き換える

- `frontend/AGENTS.md` を `docs/handoff/doc-agenda-nav/draft/frontend-AGENTS.md` と1バイトも違わない内容にする（`cp` でよい）。
- `frontend/CLAUDE.md` を `docs/handoff/doc-agenda-nav/draft/frontend-CLAUDE.md` と同じにする。
- `backend/AGENTS.md` を `docs/handoff/doc-agenda-nav/draft/backend-AGENTS.md` と同じにする。
- `backend/CLAUDE.md` を `docs/handoff/doc-agenda-nav/draft/backend-CLAUDE.md` と同じにする。

### 4-2. AGENTS.md（Edit）

- :45（F2）を次の1行に置き換える:

```
- 画面（`frontend/`）は `frontend/AGENTS.md`、サーバー側（`backend/`）は `backend/AGENTS.md` の決まりにも従う。触る前に開いて読む（Codex は作業場所より下の AGENTS.md を自動では読まない）
```

- :46-53 の8行（空行・i18n の節・UI ガバナンスの節）を消す。結果は45行で、最終行が上の :45 になる（末尾は改行1つ）。

### 4-3. CLAUDE.md:7 を1行だけ置き換える（Edit）

```
- 作業場所を作るときは `AGENTS.md`「ブランチと作業場所」の作り方に `--claude` を付ける（作った場所で Claude Code を起動する）
```

結果は9行のまま。

### 4-4. frontend/scripts/check-claude-size.js（Edit）

- :28-29 の2行（F4）を、次の4行に置き換える:

```
  { path: 'frontend/AGENTS.md', limit: 90 },
  { path: 'frontend/CLAUDE.md', limit: 10 },
  { path: 'backend/AGENTS.md', limit: 70 },
  { path: 'backend/CLAUDE.md', limit: 10 },
```

ほかの行は変えない。

### 4-5. docs/INDEX.md（Edit。5行を置き換えるだけ。行数は43のまま）

- :22 →

```
| D 領域別ルール | [frontend の決まり](../frontend/AGENTS.md) | frontend/ のファイルを触るとき |
```

- :23 →

```
| D 領域別ルール | [backend の決まり](../backend/AGENTS.md) | backend/ のファイルを触るとき |
```

- :36 →

```
2. `frontend/` だけに関係するか？ → YES: **`frontend/AGENTS.md`** に追加
```

- :37 →

```
3. `backend/` だけに関係するか？ → YES: **`backend/AGENTS.md`** に追加
```

- :38 →

```
4. frontend と backend 両方に等しく関係するか？ → YES: **このファイル** に追加（不可逆操作・ブランチ運用 等）
```

### 4-6. .claude/hooks/check-freshness.sh:25 を1行だけ置き換える（Edit）

```
RULES="AGENTS.md CLAUDE.md docs/INDEX.md docs/STANDARD-WORKFLOW.md backend/AGENTS.md backend/CLAUDE.md frontend/AGENTS.md frontend/CLAUDE.md"
```

### 4-7. .claude/agents/governance.md:72 を1行だけ置き換える（Edit）

```
| **CLAUDE.md 反映** | `grep -n <pattern> AGENTS.md CLAUDE.md frontend/AGENTS.md backend/AGENTS.md` | 該当ルールの記載行 |
```

### 4-8. docs/onboarding/design-system.md:100 を1行だけ置き換える（Edit）

```
| `frontend/AGENTS.md` | PageLayout / i18n / アイコンのルール |
```

### 4-9. ADR-1040:46 を1行だけ置き換える（Edit）

```
- ADR-076 の §1 ルート行（120行）と §2 の命名の決まりは、本 ADR が Accepted になった時点で本 ADR の Decision 1・2 に置き換わる。frontend・backend の階層の決まりは ADR-076 のまま。行数の上限（frontend 90・backend 70）は段4（2026-10-25）から本文の在る同じ場所の AGENTS.md に付け、CLAUDE.md は「@AGENTS.md」だけなのでルートと同じ 10 行にする。
```

- `node scripts/generate-adr-index.js` を実行する。docs/adr/README.md を手で直さない。

## 5. 確かめ方

担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-s4/impl/ に保存する。

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage4 && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 と合うかを確かめる。
- `git rev-parse --short "$B"` が d7924ae70。
- F1〜F9 の行を、§2 の出典の列のコマンドを `git show "${B}:AGENTS.md" | sed -n '45,53p'` の形（ファイル名と行は F の各行のもの）に直して取り出し、行数は同じ形で `wc -l` を付けて取り出して保存し、§2 と照らす。
- 違えば何も変えずに NEEDS_DECISION:。

5-1. 4本が案文と同じかを確かめる。4本の diff がどれも出力なし:

```
diff frontend/AGENTS.md docs/handoff/doc-agenda-nav/draft/frontend-AGENTS.md
diff frontend/CLAUDE.md docs/handoff/doc-agenda-nav/draft/frontend-CLAUDE.md
diff backend/AGENTS.md docs/handoff/doc-agenda-nav/draft/backend-AGENTS.md
diff backend/CLAUDE.md docs/handoff/doc-agenda-nav/draft/backend-CLAUDE.md
```

5-2. K11（外した決まりが移した先に在るか）。スクリプトは F11 のものを使い、書き換えない:

```
P=/tmp/CC報告ファイル/an-s4/impl
bash /tmp/CC報告ファイル/an-s4/sim/k11.sh "$B" $P frontend/AGENTS.md backend/AGENTS.md AGENTS.md CLAUDE.md frontend/CLAUDE.md backend/CLAUDE.md > $P/5-2.txt; cat $P/5-2.txt
```

期待: `OK=129 MISSING=43`。「--- missing but not in map:」の下が空。「--- in map but not missing:」の下が `backend/CLAUDE.md:1` と `frontend/CLAUDE.md:1` の2行だけ。

5-3. K3（同じ決まりの重なり）:

```
bash /tmp/CC報告ファイル/an-s4/sim/k3.sh AGENTS.md CLAUDE.md frontend/CLAUDE.md frontend/AGENTS.md backend/CLAUDE.md backend/AGENTS.md > $P/5-3.txt; cat $P/5-3.txt
```

期待: `K3=1`。2本以上に出る語は `日本語 files=2 frontend/AGENTS.md backend/AGENTS.md` だけ（別の決まりであることは design.md §25 の判断。担当は判断しない）。

5-4. 置き換えた行の確かめ: `git diff "$B" -- AGENTS.md CLAUDE.md frontend/scripts/check-claude-size.js docs/INDEX.md .claude/hooks/check-freshness.sh .claude/agents/governance.md docs/onboarding/design-system.md docs/adr/ADR-1040-doc-agenda-nav-entry-index.md docs/adr/README.md` の全文を保存する。期待:
- AGENTS.md: `-` 9行・`+` 1行で、`+` の行が §4-2 の全文と同じ。`wc -l AGENTS.md` が 45。
- CLAUDE.md: `-` 1行・`+` 1行で、`+` の行が §4-3 と同じ。`wc -l CLAUDE.md` が 9。
- check-claude-size.js: `-` 2行・`+` 4行で §4-4 と同じ。`node --check frontend/scripts/check-claude-size.js` が exit 0。
- docs/INDEX.md: `-` 5行・`+` 5行で §4-5 と同じ。`wc -l docs/INDEX.md` が 43。
- check-freshness.sh・governance.md・design-system.md・ADR-1040: それぞれ `-` 1行・`+` 1行で §4-6〜§4-9 と同じ。`bash -n .claude/hooks/check-freshness.sh` が exit 0。
- docs/adr/README.md: 変化なし、または「最終更新」の日付行だけ（ほかの行の変化が出たら NEEDS_DECISION:）。

5-5. 安全の決まりが入口に残るか（K7）: `grep -c '不可逆操作は必ず PO 確認' AGENTS.md`・`grep -c 'VPS 直作業禁止' AGENTS.md`・`grep -c '直接コミット禁止' AGENTS.md` がどれも 1 以上、`grep -cx '@AGENTS.md' CLAUDE.md frontend/CLAUDE.md backend/CLAUDE.md` がどれも 1。

5-6. 行数の検査:
- `node frontend/scripts/check-claude-size.js` の全文を保存し、exit 0 と `✅ CLAUDE.md サイズチェック PASSED` を確かめる（起点にあった警告1行は出てよい）。
- 逆の確かめ（上限を超えたら止まるか）: `cp backend/AGENTS.md $P/backend-AGENTS.keep` → `echo x >> backend/AGENTS.md` → `node frontend/scripts/check-claude-size.js` の全文を保存し exit 1 と `❌ backend/AGENTS.md: 71行（上限70行）` を確かめる → `cp $P/backend-AGENTS.keep backend/AGENTS.md` → `diff backend/AGENTS.md docs/handoff/doc-agenda-nav/draft/backend-AGENTS.md` が出力なし。
- 同じ手順を frontend/CLAUDE.md で行う（8行足して `❌ frontend/CLAUDE.md: 11行（上限10行）`・exit 1 → 戻して diff 出力なし）。

5-7. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（F10）と並べて書く。期待は、どの数も増えないこと。

5-8. 試験: `node scripts/tests/test-process-artifacts.js` の全文を保存し、exit 0 であること。

5-9. `git status --short` と `git diff "$B" --stat` を実行する。期待は §3 のファイル（と Opus がコミットした design.md・draft/ の4本・k11-map-stage4.md・このカード）だけ。

5-10. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けて1回だけ実行し、結果を貼る（待たない）。

## 6. 分岐ごとの対処

- 4-0・5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号は Opus が出し直す）。
- 5-1・5-4 で差が出る → 写し方か置き換え方の誤り。直して 5-1 からやり直す。2回直しても合わなければ BLOCKED:。
- 5-2 で数が違う、または「missing but not in map」に出力がある → その一覧と中身を貼って BLOCKED:（担当は対応表もスクリプトも直さない）。
- 5-3 で `K3=1` でない → 出力を貼って NEEDS_DECISION:（担当は文を直さない）。
- 5-5 で 0 が出る → 出力を貼って BLOCKED:。
- 5-6 の逆の確かめで exit 1 にならない → 出力を貼って BLOCKED:。ファイルを案文に戻したことは必ず確かめる。
- 5-7 で数が増える → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- 5-8 が失敗 → 失敗した試験名と出力を貼って NEEDS_DECISION:（担当は試験を直さない）。
- commit のときに pre-commit（frontend/.husky/pre-commit）に止められた → 止まった検査と出力の原文を貼って BLOCKED:（`--no-verify` は使わない）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行する。3回で通らなければ BLOCKED:。ただし `### GO記録` が無いことによる停止は想定どおり（Opus が後で書く）なので、その理由の原文だけを報告して PR 作成は続けてよいかを NEEDS_DECISION: で聞く。
- 見張りや自動判定に止められた → 言い換えずに、止まった手順、最後のコマンド、理由の原文を報告して停止する。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| frontend・backend の4本が審査済みの案文と1バイトも違わない | §5-1 の diff 4本が出力なし |
| 外した決まりが、移した先に 100% ある（K11） | §5-2 が OK=129・MISSING=43 で、対応表に無い不一致が0 |
| 同じ決まりの重なりが無い（K3） | §5-3 が K3=1（日本語＝別の決まり。design.md §25） |
| 安全の決まりが入口に残り、CLAUDE.md 3本が取り込みを持つ（K7） | §5-5 |
| 行数が上限内で、上限を超えたら止まる | §5-6 の PASSED と、逆の確かめ2つの exit 1 |
| 目次・見張り・参照・ADR が新しい置き場所を指す | §5-4 |
| 目次から届かない文書、行き先の無いリンクが増えない | §5-7 |
| 試験が通る | §5-8 が exit 0 |
| 触ったのは §3 のファイルだけ | §5-9 |

## 8. 戻し方

この PR の revert を main にマージする（4本・ルートの入口2本・上限・目次・見張り・参照・ADR の追記がすべて元に戻る）。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage4。Opus が作成済み（origin/main d7924ae70 が起点）で、このカードと design.md §25・draft/ の4本・k11-map-stage4.md のコミットも入っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage4`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage4 -1 --oneline` で確かめる。
- PR の作り方:
  - `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-s4/pr-body.md` を作り、別のコマンドで `--body-file` に渡す（同じコマンドで作ると pr-body-guard に止められる）。
  - 作る前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
  - ready で作る。base は main。担当はマージせず、GO 記録も書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076・ADR-027・ADR-144・ADR-034）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: frontend/AGENTS.md, frontend/CLAUDE.md, backend/AGENTS.md, backend/CLAUDE.md, AGENTS.md, CLAUDE.md, frontend/scripts/check-claude-size.js, docs/INDEX.md, .claude/hooks/check-freshness.sh, .claude/agents/governance.md, docs/onboarding/design-system.md, docs/adr/ADR-1040-doc-agenda-nav-entry-index.md, docs/adr/README.md, docs/handoff/doc-agenda-nav/design.md, docs/handoff/doc-agenda-nav/k11-map-stage4.md, docs/handoff/doc-agenda-nav/card-stage4.md, docs/handoff/doc-agenda-nav/draft/frontend-AGENTS.md, docs/handoff/doc-agenda-nav/draft/frontend-CLAUDE.md, docs/handoff/doc-agenda-nav/draft/backend-AGENTS.md, docs/handoff/doc-agenda-nav/draft/backend-CLAUDE.md`
  - `削除するファイル: frontend/AGENTS.md, frontend/CLAUDE.md, backend/AGENTS.md, backend/CLAUDE.md, AGENTS.md, CLAUDE.md, frontend/scripts/check-claude-size.js, docs/INDEX.md, .claude/hooks/check-freshness.sh, .claude/agents/governance.md, docs/onboarding/design-system.md, docs/adr/ADR-1040-doc-agenda-nav-entry-index.md, docs/adr/README.md, docs/handoff/doc-agenda-nav/design.md`
  - `区分: A（ADR-1015。入口を触るため GO 記録を付ける。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
  - `PO承認: 「1」（2026-10-25）`
  - `Opus 審査記録: コード審査はこれから`
- 本文には、§5-2 と §5-3 の出力、§5-6 の3つの結果、§5-7 の SUMMARY 行も貼る。
- 作る前に、`scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了の報告に書くこと:
  - 冒頭の受領文
  - §5-0〜5-10 の出力（長いものはファイルのパス）
  - PR の URL
  - 新しい HEAD の sha
  - 判断が必要だった点（事実のみ）
- 停止したときに書くこと:
  - 止まった手順の番号
  - 最後に実行したコマンド
  - 止まった理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれかにする。
- 委任のときの決まり:
  - sleep しない。
  - ファイルの作成と編集は Write/Edit ツールで行う（§4-1 の cp と §5-6 の一時的な書き足し・戻しを除く）。
  - PR を作る前に validate-pr-body.sh で exit 0 を確かめる。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

担当(Sonnet) 2026-10-25: §5-0〜5-9 を実行し全項目が期待どおり。生出力は /tmp/CC報告ファイル/an-s4/impl/。docs/adr/README.md の差分は「最終更新」日付行のみ。

END OF CARD
