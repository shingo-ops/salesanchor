# 実装の手順書 — 毎朝の本番の画面点検を配備と重なっても待って行う（card-prod-ui-check-wait-deploy）

- 設計: [design.md](design.md) ／ 現在地: [recon.md](recon.md) ／ 自己審査: [review-opus.md](review-opus.md)
- 状態: 手順書（Opus 作成 2026-11-15）。PO 実装承認あり（2026-11-15 チャット「1. 実装に進む」。design.md の「状態」）。
- ブランチ `release/prod-ui-check-wait-deploy-impl`。PR は作らない（Opus が作る）。危険 PR ではない（migrations・`.github/workflows/deploy.yml`・本番 scripts を触らない）。
- 「前」の文面はすべて origin/main = 777582130 のもの。行番号は目安で、置き換えは文面の一致で行う。

## 読んだ節

- docs/handoff/design-partner-card-ops/guards/00-common.md ○
- docs/handoff/design-partner-card-ops/guards/03-file.md ○
- docs/handoff/design-partner-card-ops/guards/10-executor.md ○
- docs/handoff/design-partner-card-ops/guards/11-lint.md ○
- docs/ai-agents/design-partner.md §5.5 の照合: 1 記号はバッククォートで囲んだ ○ ／ 2 PR は作らせない（下書きの心配なし）○ ／ 3 報告は完了報告の本文に生の出力のパスと最後の行を含める ○ ／ 4 1 便 1 目的（点検の設定と ADR の改訂だけ）○ ／ 5 新しいブランチを origin/main から作る ○ ／ 6 commit の文は実例で示した ○ ／ 7 合格は exit と出力の文言とファイルの数まで書いた ○

## 受領確認

着手前に、報告の 1 行目へ「受領確認: card-prod-ui-check-wait-deploy を読んだ」と書く。

## この便で決めたこと

|決めたこと|理由・出典|
|---|---|
|毎朝・手動の点検は、配備が終わるまで 1 分ごとに数え直して最大 50 分待つ。待ち切れたら gate を失敗にする|design.md §3 案 A・§4-2|
|配備の後の点検（workflow_run）は今と同じ（10 分待って 1 回だけ確かめ直し、まだなら見送り）|design.md §4-2・K4|
|待ち切れの知らせは今の Discord の段を使い、文言だけ変える|design.md §4-3|
|速さの記録は gate が success のときだけ動く|design.md §4-4|
|仕事の上限を 60 分から 110 分にする|design.md §4-1|

## やること（この順）

### 1. 準備

- (1a) `cd /Users/tanizawashingo/salesanchor 2>/dev/null || cd "$(git rev-parse --show-toplevel)"; git fetch origin main`
- (1b) `git branch --list release/prod-ui-check-wait-deploy-impl` の出力が空であること。空でなければ `BLOCKED: 同名のブランチがある` で止まる。
- (1c) `bash scripts/new-worktree.sh release/prod-ui-check-wait-deploy-impl`（`--claude` は付けない）
- (1d) `git worktree list` に `$HOME/worktrees/salesanchor/release-prod-ui-check-wait-deploy-impl` があること。以下この場所を `$REPO` と書く（`REPO="$HOME/worktrees/salesanchor/release-prod-ui-check-wait-deploy-impl"`）。以降のコマンドはすべて `cd "$REPO"` してから流す。
- (1e) `cd "$REPO" && ./scripts/dev/executor-preflight.sh`。クラウドでは [1/3]・[2/3] が FAIL でもよい。[3/3] と [4/4] は OK であること。OK でなければ `BLOCKED:` で止まる。
- (1f) 次の出力が空であること（空でなければ `NEEDS_DECISION: 777582130 から変わったファイル（一覧）` で止まる）:

```
cd "$REPO" && git diff --stat 777582130 HEAD -- .github/workflows/prod-ui-check.yml docs/adr/ADR-1051-prod-ui-black-box-check.md
```

- (1g) `mkdir -p /tmp/CC報告ファイル`

### 2. 編集のきまり

- 編集は Edit ツールで行う（ヒアドキュメント・`sed -i`・`python -c` で書かない）。
- 書き換えは 1 か所ずつ。「前」の文面がファイルの中にちょうど 1 回だけあることを確かめてから「後」に置き換える。0 回か 2 回以上なら `BLOCKED: 前が一致しない（ファイル名・節の番号）` で止まる。
- 字下げ（行頭の空白の数）も「前」「後」のとおりにする。書いていない行は触らない。

### 3. `.github/workflows/prod-ui-check.yml`

#### 3-1. 仕事の上限（今の :35-36）

前:

```
    # 速さの記録の段（最大 40 分で打ち切る）を含めて 60 分
    timeout-minutes: 60
```

後:

```
    # 配備の待ち（最大 50 分）と速さの記録の段（最大 46 分）を含めて 110 分
    timeout-minutes: 110
```

#### 3-2. 「配備中の確認」の段（今の :38-61 の全体）

前:

```
      - name: 配備中の確認
        id: gate
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          count_active() {
            total=0
            for st in in_progress queued waiting; do
              c=$(gh run list --repo "${{ github.repository }}" --workflow deploy.yml --status "$st" --json databaseId --jq length)
              total=$((total + ${c:-0}))
            done
            echo "$total"
          }
          n=$(count_active)
          if [ "${n:-0}" -ge 1 ]; then
            sleep 600
            n=$(count_active)
          fi
          if [ "${n:-0}" -ge 1 ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            echo "配備中のため見送り" >> "$GITHUB_STEP_SUMMARY"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi
```

後:

```
      - name: 配備中の確認
        id: gate
        env:
          GH_TOKEN: ${{ github.token }}
          EVENT_NAME: ${{ github.event_name }}
        run: |
          count_active() {
            total=0
            for st in in_progress queued waiting; do
              c=$(gh run list --repo "${{ github.repository }}" --workflow deploy.yml --status "$st" --json databaseId --jq length)
              total=$((total + ${c:-0}))
            done
            echo "$total"
          }
          n=$(count_active)
          if [ "$EVENT_NAME" = "workflow_run" ]; then
            # 配備の後の点検は今までどおり: 10 分待って 1 回だけ確かめ直す
            if [ "${n:-0}" -ge 1 ]; then
              sleep 600
              n=$(count_active)
            fi
            if [ "${n:-0}" -ge 1 ]; then
              echo "skip=true" >> "$GITHUB_OUTPUT"
              echo "配備中のため見送り" >> "$GITHUB_STEP_SUMMARY"
            else
              echo "skip=false" >> "$GITHUB_OUTPUT"
            fi
          else
            # 毎朝・手動の点検は見送らない: 配備が終わるまで 1 分ごとに数え直す（最大 50 分）
            deadline=$(( $(date +%s) + 3000 ))
            while [ "${n:-0}" -ge 1 ] && [ "$(date +%s)" -lt "$deadline" ]; do
              sleep 60
              n=$(count_active)
            done
            if [ "${n:-0}" -ge 1 ]; then
              echo "配備が 50 分以上続き、点検を始められませんでした（未実行）" >> "$GITHUB_STEP_SUMMARY"
              exit 1
            fi
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi
```

注: 「後」の中の `sleep` は GitHub の機械の上で動く設定の文面で、実装役が待つためのものではない。

#### 3-3. 不合格の知らせの段の env（今の :123 の下に 1 行足す）

前:

```
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          if [ -z "${DISCORD_WEBHOOK_OWNER_PING:-}" ]; then
```

後:

```
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
          GATE_OUTCOME: ${{ steps.gate.outcome }}
        run: |
          if [ -z "${DISCORD_WEBHOOK_OWNER_PING:-}" ]; then
```

#### 3-4. 不合格の知らせの文言（今の :145）

前:

```
          label = " / ".join(names) if names else "点検を最後まで実行できませんでした"
```

後:

```
          if os.environ.get("GATE_OUTCOME") == "failure":
              label = "配備が 50 分以上続き、点検を始められませんでした（未実行）"
          else:
              label = " / ".join(names) if names else "点検を最後まで実行できませんでした"
```

#### 3-5. 速さの記録の段の if と注記（今の :158-160）

前:

```
        if: always() && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'
        continue-on-error: true
        # 試験の上限 45 分 + 1 分。この段が延びても仕事の上限 60 分の中で終わらせる（設計 5-8）
```

後:

```
        if: always() && steps.gate.outcome == 'success' && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'
        continue-on-error: true
        # 試験の上限 45 分 + 1 分。配備の待ち（最大 50 分）があってもこの段が仕事の上限 110 分の中で終わる（設計 5-8・prod-ui-check-wait-deploy §4-1）
```

### 4. `docs/adr/ADR-1051-prod-ui-black-box-check.md`

#### 4-1. What の配備中の行（今の :27）

前:

```
- 配備（deploy.yml）が動いている間は 10 分待って 1 回だけ確かめ直し、まだ動いていれば見送る（不合格にしない）。
```

後:

```
- 配備（deploy.yml）が動いている間、配備の後の点検は 10 分待って 1 回だけ確かめ直し、まだ動いていれば見送る（不合格にしない。次の配備の後の点検が続けて動くため）。毎朝と手動の点検は見送らず、配備が終わるまで 1 分ごとに確かめ直して最大 50 分待つ。50 分を超えたら不合格にして Discord に「未実行」と知らせる（2026-11-15 改訂）。
```

#### 4-2. 表の備考の行の終わり（今の :6 の末尾）

前:

```
Claude Opus が決めた（設計 docs/handoff/prod-ui-check-schedule-s13/design.md） |
```

後:

```
Claude Opus が決めた（設計 docs/handoff/prod-ui-check-schedule-s13/design.md）。改訂 2026-11-15（毎朝と手動の点検は配備の終わりを最大 50 分待ち、待ち切れたら不合格にして知らせる）は PO の選択 2026-11-13「2」・成功条件の承認 2026-11-14「1」・実装の承認 2026-11-15「1」に基づき Claude Opus が決めた（設計 docs/handoff/prod-ui-check-wait-deploy/design.md） |
```

#### 4-3. ADR の一覧を作り直す

- (4a) `cd "$REPO" && node scripts/generate-adr-index.js > /tmp/CC報告ファイル/adr-index.txt 2>&1; echo "exit=$?"` → exit=0
- (4b) `cd "$REPO" && node scripts/generate-adr-index.js --check > /tmp/CC報告ファイル/adr-index-check.txt 2>&1; echo "exit=$?"` → exit=0
- `docs/adr/README.md` が変わっても変わらなくてもよい。変わったかどうかを報告に書く。

### 5. 確かめ（どれも生の出力を /tmp/CC報告ファイル/ に保存し、全文を読んでから報告する。値は記録して続ける。判定は Opus が行う）

- (5a) 設定の形を読む: `cd "$REPO" && uv run --no-project --python 3.12 --with pyyaml python -I -c "import yaml; d=yaml.safe_load(open('.github/workflows/prod-ui-check.yml', encoding='utf-8')); j=d['jobs']['check']; s=j['steps']; print(j['timeout-minutes'], len(s), s[0]['name'], s[0]['env']['EVENT_NAME'], s[9]['env']['GATE_OUTCOME'], s[10]['if'])" > /tmp/CC報告ファイル/yaml.txt 2>&1; echo "exit=$?"` → 期待は exit=0 で、出力の 1 行目が `110 11 配備中の確認 ${{ github.event_name }} ${{ steps.gate.outcome }} always() && steps.gate.outcome == 'success' && steps.gate.outputs.skip != 'true' && github.event_name != 'workflow_run'`。違っても止まらず、出力をそのまま報告に貼る。
- (5b) 配備中の確認の台本の文法: `cd "$REPO" && uv run --no-project --python 3.12 --with pyyaml python -I -c "import yaml; print(yaml.safe_load(open('.github/workflows/prod-ui-check.yml', encoding='utf-8'))['jobs']['check']['steps'][0]['run'])" > /tmp/CC報告ファイル/gate.sh 2>&1; echo "exit=$?"` のあと `cd "$REPO" && bash -n /tmp/CC報告ファイル/gate.sh; echo "exit=$?"` → どちらも exit=0
- (5c) 知らせの段の台本の文法: `cd "$REPO" && uv run --no-project --python 3.12 --with pyyaml python -I -c "import yaml; print(yaml.safe_load(open('.github/workflows/prod-ui-check.yml', encoding='utf-8'))['jobs']['check']['steps'][9]['run'])" > /tmp/CC報告ファイル/notify.sh 2>&1; echo "exit=$?"` のあと `cd "$REPO" && bash -n /tmp/CC報告ファイル/notify.sh; echo "exit=$?"` → どちらも exit=0
- (5d) 知らせの段の python の文法: `cd "$REPO" && uv run --no-project --python 3.12 python -I -c "import re,ast; t=open('/tmp/CC報告ファイル/notify.sh', encoding='utf-8').read(); m=re.search(r\"<<'PY'\n(.*?)\nPY\n\", t, re.S); ast.parse(m.group(1)); print('python ok')" > /tmp/CC報告ファイル/notify-py.txt 2>&1; echo "exit=$?"` → exit=0 で出力が `python ok`
- (5e) `cd "$REPO" && git diff --check > /tmp/CC報告ファイル/diff-check.txt 2>&1; echo "exit=$?"` → exit=0
- (5f) `cd "$REPO" && git diff --stat` を報告に貼る。変わるのは `.github/workflows/prod-ui-check.yml` と `docs/adr/ADR-1051-prod-ui-black-box-check.md`（と、(4a) で変わったときだけ `docs/adr/README.md`）。`.github/workflows/prod-ui-check.yml` の数は、削除 12 行・追加 32 行（手元の写しで数えた値）。違ったら数を記録して続ける。
- (5g) `cd "$REPO" && git diff > /tmp/CC報告ファイル/diff.txt; echo "exit=$?"`（Opus が手順書の「後」と照合する）

### 6. 記録（commit）と送り出し（push）

- (6a) `cd "$REPO" && git status --short` を報告に貼る。期待は変更 2 個か 3 個（§5f の名前）。それ以外の名前があれば `NEEDS_DECISION:`。
- (6b) `cd "$REPO" && git add .github/workflows/prod-ui-check.yml` と `cd "$REPO" && git add docs/adr/ADR-1051-prod-ui-black-box-check.md`。README が変わったときだけ `cd "$REPO" && git add docs/adr/README.md`（`git add -A`・`git add .` は使わない）。
- (6c) commit の文を Write ツールで `/tmp/CC報告ファイル/commit-msg.txt` に書き、`cd "$REPO" && git commit -F /tmp/CC報告ファイル/commit-msg.txt` で記録する。文は次のとおり（1 字も変えない）:

```
ci(prod-ui-check): wait for deploys before the daily check instead of skipping

- schedule / workflow_dispatch: recheck every minute for up to 50 minutes
- still busy after 50 minutes: fail the gate and send the Discord notice
- workflow_run keeps the current 10-minute recheck and skip
- job timeout 60 -> 110 minutes; page-speed step runs only when the gate succeeded
- ADR-1051: revise the deploy-overlap rule (2026-11-15)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

- (6d) `cd "$REPO" && git log --oneline -1` を報告に貼る。
- (6e) `cd "$REPO" && bash scripts/dev/check-before-submit.sh > /tmp/CC報告ファイル/check-before-submit.txt 2>&1; echo "exit=$?"` → exit=0（落ちたら生の出力のパスと最後の 20 行を添えて `NEEDS_DECISION:`）
- (6f) `git -C "$REPO" push -u origin release/prod-ui-check-wait-deploy-impl`（ほかの命令とつなげずに単独で流す。push 前の確かめで数分かかる）

## 触らない

- `.github/workflows/deploy.yml`（ADR-136）・ほかの `.github/workflows/` のファイル・`tests/prod-check/`・`frontend/`・`backend/`・`migrations/`・本番の `scripts/`
- `prod-ui-check.yml` の `on:`（毎朝の起動時刻）・`concurrency`・「本番の画面点検を実行」の段・secrets の名前
- PR は作らない（Opus が作る）。台帳（`.claude-pipeline/active-work.d/`）は commit しない。

## 想定される分かれ道

|起きたこと|すること|
|---|---|
|(1f) で 777582130 から変わったファイルがある|直さずに `NEEDS_DECISION:` で一覧を出す|
|「前」がちょうど 1 回一致しない|`BLOCKED:` でファイル名と節の番号を出す|
|(5a) の出力が期待と違う|止まらずに出力をそのまま報告に貼り、§6 へ進む|
|(5b)〜(5d) のどれかが exit 0 でない|直さずに、生の出力のパスを添えて `NEEDS_DECISION:`|
|`uv` が無い|`NEEDS_DECISION: uv が無い` で止まる（ほかの道具に替えない）|
|push が見張りに止められる|言い換えずに止められた文面を貼って `BLOCKED:`|

## Opus が合流の前に確かめること（実装役はしない）

- 差分の全文をこの手順書の「後」と照合する。
- CI の結果（必須の確かめが緑）。
- マージ前の審査役（reviewer・model opus）の判定。
- 合流の後: 手動の点検を 1 回流し、gate が「待ちなし」で success になり、点検 12 件と速さの記録が動くこと（K2 の一部）。毎朝の 14 日分は design.md §8 の予約で数える。

## 終わりの報告

- 1 行目: 「受領確認: card-prod-ui-check-wait-deploy を読んだ」
- 途中で停止するときも、停止した手順番号・最後に実行したコマンド・停止した理由と、ここまでの観測を書いてから下の BLOCKED: か NEEDS_DECISION: の行で終える（続きの作業はしない）。
- 最後の行は次のどれか 1 つ:
  - `DONE: release/prod-ui-check-wait-deploy-impl を push（commit の短い番号）`
  - `BLOCKED: 理由（生の出力のパス）`
  - `NEEDS_DECISION: 決めてほしいこと（生の出力のパス）`
- 間に: (1e)〜(1f) の結果・§4 と §5 の各 exit と出力・§6 のファイルの数と `git log --oneline -1`。報告に書くのは観測した事実だけ（生の出力のパスを添える）。
- 1 つの発言は 600 文字以内。長いときは番号付きの発言に分ける。

END OF CARD
