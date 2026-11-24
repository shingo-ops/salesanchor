---
mode: handoff
---
# 実装カード 続ける仕組み B: パスキーの壊れの見張り2つ

親: [sustain-design.md](./sustain-design.md) §5-2・§5-4・§8（受入条件）

- 状態: カード作成済み（2026-11-24 Opus）。PO 実装承認: 2026-11-24 チャット「1,…PRマージ、デプロイまで完走させてくれ」（5-1・5-2・5-4 の3つ）。マージと prod2 への見張りの設置は Opus が行う（担当はしない）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断・prod2 への設置。
- 区分: B（本番の画面点検の1行・見張りの設定1本・手順書1節・しきい値の表2行。migrations・scripts・deploy.yml・backend・frontend を触らない）。

## 0. カード発行前チェック

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は作らない） | ○（§5 手順7 で push まで） |
| 3 | 報告の宛先（最後の返事に生出力の全文） | ○（§6） |
| 4 | 1便1目的（パスキーが壊れたら知らせる見張りだけ） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh） | ○（§5 手順1） |
| 7 | 合格基準を出力まで縛る（差分のファイル一覧） | ○（§5 手順6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 受領と終端の合図・停止の3点 | ○（§6） |
| 11 | 行番号は目印（ずれたら前後の文で探す） | ○ |
| 13 | sleep 禁止・Write/Edit で書く・フックに止められたら言い換えない | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に git log と ls-remote で実在を確かめる）、04-worktree.md（起点は origin/main・`new-worktree.sh` で作る・push は `git push -u origin HEAD`）、05-pr.md（`gh pr create` を直に使わない → PR は Opus が作る）。

基準: origin/main 1e37c0198。行番号はこの時点の目印。

## 1. 目的（利用者に見える変化）

- ログイン画面のメール欄からパスキーの候補の設定が消えたら、毎朝の本番の画面点検が不合格になり Discord に届く。
- パスキーのログインの道（options・verify）で本番が 5xx を返したら、10分以内に見張りが Discord に知らせる。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `tests/prod-check/prod-ui.spec.ts` | S1 に1行（§3-1） |
| `monitoring/loki/rules/jarvis/alerts.yml` | auth_anomaly に1本（§3-2） |
| `docs/runbooks/alerts.md` | 節を1つ（§3-3） |
| `monitoring/tokens.yml` | しきい値と for の行を1行ずつ（§3-4） |
| `docs/handoff/passkey-autofill-first/card-sustain-b.md` | 手順2 の取り込みで入るだけ。中身は変えない |

触らないもの: ほかの見張り・`.github/`・`monitoring/alertmanager/`・prod-ui-check.yml・S2 以降の点検。

## 3. 作るものの決まり（sustain-design.md §5-2・§5-4 が正。食い違えば報告する）

### 3-1. prod-ui.spec.ts（Edit・`:28-34` 目印）

変更前:
```ts
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    await expect(page.getByLabel("パスワード", { exact: true })).toBeVisible();
```
変更後:
```ts
    await expect(page.getByLabel("メールアドレス")).toBeVisible();
    // パスキーの候補をメール欄に出す設定（sustain-design §5-2）。消えたら毎朝の点検で知らせる
    await expect(page.getByLabel("メールアドレス"), "パスキーの候補の設定").toHaveAttribute("autocomplete", "email webauthn");
    await expect(page.getByLabel("パスワード", { exact: true })).toBeVisible();
```

### 3-2. alerts.yml（Edit・SustainedAuthFailure の最後の行 `:33` 目印の後、`- name: error_anomaly` の前）

変更前:
```yaml
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#sustainedauthfailure"

  - name: error_anomaly
```
変更後:
```yaml
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#sustainedauthfailure"

      # パスキーのログインの道(options・verify)で 5xx が10分に1件でも出た（sustain-design §5-4）
      # 数えるのは入口(nginx)の行だけ（"5xx" の後に送った量の数字が続く形）。処理の途中で落ちた500と502/504は auth_events に残らないため
      - alert: PasskeyServerError
        expr: |
          sum(count_over_time({job="containerlogs"} |~ "\"POST /api/v1/auth/passkey/login/(options|verify) HTTP/[0-9.]+\" 5[0-9][0-9] [0-9]+" [10m])) > 0
        for: 0m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "パスキーのログインで本番の誤りが出ています"
          description: "直近10分間に、パスキーのログインの道(options・verify)で 5xx が1件以上出ました。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#passkeyservererror"

  - name: error_anomaly
```

### 3-3. runbooks/alerts.md（Edit・`## SustainedAuthFailure` の節 `:147-153` 目印の後、`## BackendErrorSpike` の前）

変更前:
```markdown
- 止め方：`amtool silence add alertname=SustainedAuthFailure --duration=PERIOD --comment=REASON`

## BackendErrorSpike
```
変更後:
```markdown
- 止め方：`amtool silence add alertname=SustainedAuthFailure --duration=PERIOD --comment=REASON`

## PasskeyServerError

- 札：ticket
- 何が起きているか：パスキーのログインの道（`/api/v1/auth/passkey/login/options`・`/auth/passkey/login/verify`）で、本番が 5xx を返した記録が入口（nginx）の行に10分に1件以上ある。処理の途中で落ちた 500 と、入口が返す 502・504 は認証の記録（auth_events）に残らないので、入口の行で数える。設計: `docs/handoff/passkey-autofill-first/sustain-design.md` §5-4。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "\"POST /api/v1/auth/passkey/login/(options|verify) HTTP/[0-9.]+\" 5[0-9][0-9] [0-9]+"`。同じ時刻のバックエンドの行で、例外の名前と、配備・再起動の最中かを見る。
- 直し方：配備・再起動の最中の 502 だけなら様子を見る。続く・500 が出るなら、バックエンドの例外を Opus に報告する。パスワードのログインは別の道なので、利用者はパスワードでログインできる。
- 止め方：`amtool silence add alertname=PasskeyServerError --duration=PERIOD --comment=REASON`

## BackendErrorSpike
```

### 3-4. tokens.yml（Edit・2か所。`check_alert_rules.py` と `validate_tokens.py` はこの2行を読まない。しきい値の一覧を1か所にそろえるための記載）

(1) `:108-111` 目印のログ異常検知の表

変更前:
```yaml
  auth_failure_per_1h:    20    # SustainedAuthFailure: > 20（同じ数え方の1時間）
```
変更後:
```yaml
  auth_failure_per_1h:    20    # SustainedAuthFailure: > 20（同じ数え方の1時間）
  passkey_5xx_per_10m:     0    # PasskeyServerError: > 0（パスキーの道 options・verify の入口の 5xx）
```

(2) `:122-123` 目印の for の表

変更前:
```yaml
  auth_failure:      "5m"   # SustainedAuthFailure
```
変更後:
```yaml
  auth_failure:      "5m"   # SustainedAuthFailure
  passkey_server_error: "0m"  # PasskeyServerError
```

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続（prod2・Loki・本番の画面）・マージ・`main` への push・`--force`・ファイルの削除が要るとき／`check_alert_rules.py` が §3 の書き方のままで通らないとき。
- 行番号のずれは記録して続行し、報告に書く。
- 本番の画面点検（playwright）は流さない（本番に届くため。Opus が合流後に GitHub で流す）。
- PR を作らない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書く。`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に、`cd 作業場所` はそのパスに読み替える。1手順1命令。executor-preflight.sh はクラウドでは流さない（gh の認証が無く必ず失敗する・2026-11-24 実測）。PR の名義は PR を作る Opus が手元で確かめる。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/passkey-sustain-watch
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。

手順2 このカードを取り込む（Opus が push した枝）
    cd 作業場所 && git checkout origin/release/passkey-sustain-impl -- docs/handoff/passkey-autofill-first/card-sustain-b.md
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: card-sustain-b.md の1ファイルだけ。merge は使わない（クラウドの決まり）。

手順3 対象ファイルが基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 1e37c0198 origin/main -- tests/prod-check/prod-ui.spec.ts monitoring/loki/rules/jarvis/alerts.yml docs/runbooks/alerts.md monitoring/tokens.yml
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1〜§3-4 を Edit で直す。

手順5 検査を流す（.github/workflows/monitoring-check.yml と同じもの）
    cd 作業場所 && pip install pyyaml
    cd 作業場所 && python3 -c "import yaml; yaml.safe_load(open('monitoring/tokens.yml')); yaml.safe_load(open('monitoring/loki/rules/jarvis/alerts.yml'))"
    cd 作業場所 && python3 monitoring/scripts/validate_tokens.py
    cd 作業場所 && python3 monitoring/scripts/check_alert_rules.py
    cd 作業場所 && grep -c "PasskeyServerError" monitoring/loki/rules/jarvis/alerts.yml docs/runbooks/alerts.md monitoring/tokens.yml
    期待する出力: 上の3つは誤り 0 で終わる（validate_tokens.py の「警告」はよい。この変更の前からある警告かを報告に書く）。grep は alerts.yml が 1・alerts.md が 2・tokens.yml が 2。落ちたら直してからもう一度流す。3回直しても落ちたら停止して BLOCKED:（生出力の全文を付ける）。

手順6 差分のファイル一覧を確かめる
    cd 作業場所 && git add tests/prod-check/prod-ui.spec.ts monitoring/loki/rules/jarvis/alerts.yml docs/runbooks/alerts.md monitoring/tokens.yml docs/handoff/passkey-autofill-first/card-sustain-b.md
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: §2 の表の5ファイルだけ。deletions がある行は名前を報告に書く。`git add -A` は使わない（登録ファイルを巻き込む）。

手順7 記録して送る
    commit の文を Write で作業場所の外の一時の場所（以下 /tmp/commit-msg.txt と書く）に書く。1行目「feat(monitoring): watch passkey autofill attribute and passkey 5xx」、空行、最後の行「Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>」。
    cd 作業場所 && git commit -F /tmp/commit-msg.txt
    cd 作業場所 && git log -2 --oneline
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin refs/heads/release/passkey-sustain-watch
    期待する出力: git log の先頭が手順7 の commit。ls-remote の番号が `git rev-parse HEAD` と同じ。

## 6. 報告

- 受け取ったら最初に「カード 続ける仕組み B 見張り を受領」と1行書く（受領確認）。
- 報告は PR コメントにしない。最後の返事に、手順1・2・3・5・6・7 の出力の全文を書く。
- 止まったら（停止）、止まった手順・最後のコマンド・理由の原文を書き、最後の行を `BLOCKED:` か `NEEDS_DECISION:` で終える。終えたら最後の行を `DONE: ` と push した HEAD の40桁で終える。

END OF CARD
