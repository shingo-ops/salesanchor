# 実装カード 段階4 順番8 — ログイン失敗の見張りの鳴る条件を直す

> この文書は何か：ログイン失敗の見張り 2 本（BruteForceAttempt・SustainedAuthFailure）は、今は数字の一部の「403」やセッション切れの 401 まで数えて、通知の記録の 85% を占めています。この便では、承認済みの設計どおり、ログインの入口 6 つの「失敗（401）」と「締め出し（429）」だけを数えるように、見張りの式・しきい値・手順書を直します。

- 設計: `docs/handoff/ai-ops-247/login-alert-design.md` §3（PO 承認 2026-11-20「1」）
- 親: `docs/handoff/ai-ops-247/stage4-requirements.md`（ロードマップ順 8・C6）
- 対象ADR: ADR-1012
- 状態: 設計は PO 承認済み。実装の承認は PO 2026-11-20「1」（ログイン失敗の見張りを本番に入れる）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。ただし prod2 への反映は本番の変更なので、C6（前の本番の変更 便H 2026-11-20 18:18 の 24 時間後）より後に、Opus が「POの委任に基づくClaude Opus発行」の GO を記録してから行う
- 担当: 実装 Sonnet（クラウド）／審査・GO・マージ・prod2 への反映・確かめ Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らないと明記 | ○（§10。PR は Opus が作る） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（ログイン失敗の見張り 2 本の式・しきい値・手順書だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に変更前と変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3 は数が違えば原文を貼る） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main 77971367b で目印の行と今の本数を確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限 | ○（§5・§10） |
| guards/03-file.md | 編集は Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さない | ○（§10） |
| guards/08-vps.md | 本番（prod1・prod2）には触らない | ○（§8 は Opus） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階4 順番8 ログイン失敗の見張りの実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/loki/rules/jarvis/alerts.yml` の BruteForceAttempt・SustainedAuthFailure の式・コメント・説明文（§4-1）
2. `monitoring/tokens.yml` のしきい値 2 行（§4-2）
3. `docs/runbooks/alerts.md` の 2 節（§4-3）
4. このカードの §13 の報告欄

入れない:
- ほかの Loki の見張り 4 本・Prometheus の見張り・Alertmanager・札（severity・tier）・`for:` の値・`runbook_url`
- アプリのコード（`backend/`）
- prod2 への反映（§8。Opus が行う）

## 2. 前提の事実（origin/main 77971367b・Opus が手元で確かめた）

- `monitoring/loki/rules/jarvis/alerts.yml:7-31` が 2 本の見張り（§4-1 の「変更前」と一字一句同じ）
- `monitoring/tokens.yml:108-109` がしきい値（`brute_force_per_5m: 20`・`auth_failure_per_1h: 50`）
- `docs/runbooks/alerts.md:130-144` が 2 節
- `python3 monitoring/scripts/check_alert_rules.py` の今の出力: `OK: Prometheus 41 rules, Loki 6 rules, runbook 47 sections`。この便で本数・節の数は変わらない
- 式は設計 §3-1 のとおり。設計 §2-4 で本番 Loki の 14 日をこの式で数え直し済み（5 分の最大 2 件・1 時間の最大 6 件）

## 3. 触るファイル（これ以外は触らない）

| ファイル | すること |
|---|---|
| `monitoring/loki/rules/jarvis/alerts.yml` | §4-1 の置き換え |
| `monitoring/tokens.yml` | §4-2 の置き換え |
| `docs/runbooks/alerts.md` | §4-3 の置き換え |
| `docs/handoff/ai-ops-247/card-login-alert-bin8.md`（このカード） | §13 の「（未記入）」を報告で書き換える（Opus が後で同じブランチに入れる。担当はこのファイルを作らない・触らない） |

## 4. 作り方（すべて Edit。変更前の塊を探して変更後の塊に置き換える）

### 4-1. `monitoring/loki/rules/jarvis/alerts.yml`

変更前（7〜31 行目）:

```yaml
      # 認証失敗が5分間に20回以上（ブルートフォース攻撃の可能性）
      - alert: BruteForceAttempt
        expr: |
          sum(count_over_time({job="containerlogs"} |~ "401|403|auth.*fail|login.*fail|Unauthorized" [5m])) > 20
        for: 1m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "ブルートフォース攻撃の可能性を検知"
          description: "直近5分間に認証失敗が20回以上発生しています。即時確認してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#bruteforceattempt"

      # 認証失敗が1時間に50回以上（低頻度の攻撃）
      - alert: SustainedAuthFailure
        expr: |
          sum(count_over_time({job="containerlogs"} |~ "401|403|auth.*fail|Unauthorized" [1h])) > 50
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "認証失敗が継続的に発生しています"
          description: "直近1時間に認証失敗が50回以上です。"
```

変更後:

```yaml
      # ログインの入口6つの失敗(401)と締め出し(429)が5分間に10件超（攻撃の可能性）
      # 数えるのはバックエンド(uvicorn)の行だけ。入口(nginx)の行は "401 <数字>" の形なので当たらない
      # 10件 = アプリが1つのIPを締め出す回数（backend/app/cache.py の AUTH_FAIL_MAX）。設計: docs/handoff/ai-ops-247/login-alert-design.md
      - alert: BruteForceAttempt
        expr: |
          sum(count_over_time({job="containerlogs"} |~ "\"POST /api/v1/(auth/login|auth/passkey/login/verify|auth/password-reset/confirm|auth/login-requests/recovery|viewer/login|viewer/password-reset/confirm) HTTP/[0-9.]+\" (401 Unauthorized|429 Too Many Requests)" [5m])) > 10
        for: 1m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "ログインの失敗が急に増えています（攻撃の可能性）"
          description: "直近5分間にログインの失敗(401)と締め出し(429)が10件を超えました。即時確認してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#bruteforceattempt"

      # 同じ数え方で1時間に20件超（5分に10件未満でゆっくり続く失敗）
      - alert: SustainedAuthFailure
        expr: |
          sum(count_over_time({job="containerlogs"} |~ "\"POST /api/v1/(auth/login|auth/passkey/login/verify|auth/password-reset/confirm|auth/login-requests/recovery|viewer/login|viewer/password-reset/confirm) HTTP/[0-9.]+\" (401 Unauthorized|429 Too Many Requests)" [1h])) > 20
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "ログインの失敗が続いています"
          description: "直近1時間にログインの失敗(401)と締め出し(429)が20件を超えました。"
```

（`runbook_url` の行と、その後ろの行は変えない）

### 4-2. `monitoring/tokens.yml`

変更前（108〜109 行目）:

```yaml
  brute_force_per_5m:     20    # BruteForceAttempt: > 20
  auth_failure_per_1h:    50    # SustainedAuthFailure: > 50
```

変更後:

```yaml
  brute_force_per_5m:     10    # BruteForceAttempt: > 10（ログインの入口6つの 401・429 だけを数える）
  auth_failure_per_1h:    20    # SustainedAuthFailure: > 20（同じ数え方の1時間）
```

### 4-3. `docs/runbooks/alerts.md`

変更前（130〜144 行目）:

```markdown
## BruteForceAttempt

- 札：page
- 何が起きているか：認証失敗らしきログ（401・403 など）が 5 分間に 20 件を超えた状態が 1 分続いた。攻撃の可能性。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "401|403|auth.*fail|login.*fail|Unauthorized"`、どの経路・どのテナントか。
- 直し方：正常な利用の失敗か攻撃かを切り分け、攻撃の疑いなら security-reviewer と Opus に報告する。
- 止め方：`amtool silence add alertname=BruteForceAttempt --duration=PERIOD --comment=REASON`

## SustainedAuthFailure

- 札：ticket
- 何が起きているか：認証失敗らしきログが 1 時間に 50 件を超えた状態が 5 分続いた。低頻度の継続的な失敗。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "401|403|auth.*fail|Unauthorized"` を時間帯別に見る。
- 直し方：特定の利用者の設定ミスか攻撃かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=SustainedAuthFailure --duration=PERIOD --comment=REASON`
```

変更後:

```markdown
## BruteForceAttempt

- 札：page
- 何が起きているか：ログインの入口 6 つ（`/api/v1/auth/login`・`/auth/passkey/login/verify`・`/auth/password-reset/confirm`・`/auth/login-requests/recovery`・`/viewer/login`・`/viewer/password-reset/confirm`）で、ログインの失敗（401）と締め出し（429）が 5 分間に 10 件を超えた状態が 1 分続いた。10 件はアプリが 1 つの IP を締め出す回数（`backend/app/cache.py` の `AUTH_FAIL_MAX`）。攻撃の可能性。パスワードの再設定と復旧の入口は失敗が 400 なので、締め出し（429）だけを数える。
- 最初に見るもの：Loki で `{job="containerlogs"} |~ "\"POST /api/v1/(auth/login|auth/passkey/login/verify|auth/password-reset/confirm|auth/login-requests/recovery|viewer/login|viewer/password-reset/confirm) HTTP/[0-9.]+\" (401 Unauthorized|429 Too Many Requests)"`。同じ時刻の入口（nginx）の行で、どの IP・どの端末からかを見る。
- 直し方：正常な利用の失敗か攻撃かを切り分け、攻撃の疑いなら security-reviewer と Opus に報告する。uvicorn の版を上げた後は、わざと 1 回失敗させて上の式で数に出ることを確かめる（ログの形が変わると黙って数えなくなる）。
- 止め方：`amtool silence add alertname=BruteForceAttempt --duration=PERIOD --comment=REASON`

## SustainedAuthFailure

- 札：ticket
- 何が起きているか：BruteForceAttempt と同じ数え方（ログインの入口 6 つの 401・429）で、1 時間に 20 件を超えた状態が 5 分続いた。5 分に 10 件未満でゆっくり続く失敗。
- 最初に見るもの：BruteForceAttempt の節の式を、窓を `[1h]` にして時間帯別に見る。
- 直し方：特定の利用者の設定ミスか攻撃かを切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=SustainedAuthFailure --duration=PERIOD --comment=REASON`
```

## 5. 確かめ方（担当が実行し、出力を報告に書く）

5-1. 見張りの検査：作業場所で `/tmp/v312/bin/python monitoring/scripts/check_alert_rules.py 2>&1 | tail -5` が `OK: Prometheus 41 rules, Loki 6 rules, runbook 47 sections`（本数は変わらない。origin/main が先に進んで数が違うときは、origin/main で同じコマンドを流した数と同じであればよい）
5-2. YAML：`/tmp/v312/bin/python -c "import yaml,sys; [yaml.safe_load(open(p)) for p in sys.argv[1:]]; print('yaml ok')" monitoring/loki/rules/jarvis/alerts.yml monitoring/tokens.yml` が `yaml ok`
5-3. 差分：`git diff origin/main --stat` が §3 の 3 ファイルだけ（カードは含まない）。`git diff origin/main | grep -E '^-' | grep -v '^--- ' | wc -l` が `15`（alerts.yml 8 行・tokens.yml 2 行・alerts.md 5 行。Opus が写しで置き換えを試して数えた）。数が違うときは `git diff origin/main | grep -E '^-' | grep -v '^--- '` の原文を貼る
5-4. 式の一致：`grep -c -F 'auth/login|auth/passkey/login/verify|auth/password-reset/confirm|auth/login-requests/recovery|viewer/login|viewer/password-reset/confirm) HTTP/[0-9.]+' monitoring/loki/rules/jarvis/alerts.yml docs/runbooks/alerts.md` が alerts.yml `2`・alerts.md `1`
5-5. lokitool は手元で動かさない（CI の monitoring-check が流す）。CI は待たない

## 6. 分岐ごとの対処

- §4 の変更前の塊が見つからない（ほかの PR が先に変えた）→ 置き換えずに NEEDS_DECISION: で `git show origin/main:<そのファイル> | sed -n '<前後の行>p'` の原文を貼る
- §5 が期待と違う → commit せず原文を添えて BLOCKED:
- §4 の変更後に誤りと思われる箇所がある → 直さずに NEEDS_DECISION: で、行と理由を書く

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| A1 CI の見張りの検査が通る | CI `monitoring-check`（lokitool rules check・check_alert_rules.py・tokens 構文）が緑 |
| A2 tokens.yml とルールのしきい値が一致 | PR の差分で `brute_force_per_5m: 10`・`auth_failure_per_1h: 20` とルールの `> 10`・`> 20` を照合（Opus） |
| 触ったファイルが §3 だけで、ほかの見張りは 1 行も変わっていない | §5-3 |
| A3 prod2 に新しいルールが入り Loki が読んでいる | §8-4 の生出力（ruler の API で式が新しいもの・state inactive） |
| A4 本当の失敗を数える | §8-5（反映後 24 時間で、新しい式の数が 1 以上。自然に起きるログインの失敗で確かめる） |
| A5 誤って鳴らない | 反映後 7 日で 2 本の鳴った回数 0（本当の攻撃が無い限り） |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 と照らし、CI が緑なら審査役（reviewer・opus）の APPROVE を受ける
2. C6：前の本番の変更（便H 2026-11-20 18:18 JST）の 24 時間後＝2026-11-21 18:20 JST より後にだけ、3 以降に進む
3. GO を「POの委任に基づくClaude Opus発行」で PR に記録し、マージする。マージ後すぐ 4 に進む（毎日 09:23 の設定のずれの点検で鳴らさないため、マージと反映を同じ日に続けて行う）
4. prod2：今の `/opt/salesanchor-monitoring/monitoring/loki/rules/jarvis/alerts.yml` を `/opt/salesanchor-monitoring/backups/ai-ops-stage3/` に控えてから、main の版を置く（Loki の ruler は rules の置き場をおよそ 1 分ごとに読み直す）。2 分後に ruler の API で 2 本の式が新しいもの・state が inactive であることを確かめる（A3）。sha256 が main と一致すること
5. A4：反映から 24 時間の間に、新しい式の数（`[24h]`）が 1 以上であることを Loki で数える（設計 §2-3 で 1 日 2〜49 件の自然な失敗がある）。本番でわざと失敗させる操作はしない
6. A5：反映後 7 日で鳴った回数を数え、`stage4-requirements.md` の K5 に書く
7. 生出力は /tmp/CC報告ファイル/ai-ops-stage4/login-alert-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：ログイン後の画面での 401・403 の急増（権限の不具合）は、この 2 本では鳴らなくなる（設計 §3-3。5xx は別の見張りが見る）
- 弊害：uvicorn のログの形が変わると黙って数えなくなる（手順書の直し方に確かめ方を書いた）
- 戻し方：この PR の revert を main にマージ → prod2 の控えから `alerts.yml` を戻す（ruler が約 1 分で読み直す）

## 10. 作業場所と記録

- 作業場所：`bash scripts/new-worktree.sh release/login-alert-bin8`（origin/main 起点。クラウドでは `--claude` を付けない）。出力はパイプに通さない。最後に「Input must be provided」と出て終了コードが 1 でも、作業場所ができていれば進む。出力に出た場所へ `cd` し、以後すべてその中で作業する。clone のまま commit しない
- commit は §3 の 3 ファイルだけを add する。commit 文：`fix(monitoring): ログイン失敗の見張りをログインの入口6つの401・429だけで数える`（最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。`--no-verify`・amend・force push・rebase はしない
- `git push -u origin release/login-alert-bin8` を単独で流す。PR は作らない（Opus が作る）

## 11. 報告

- 冒頭の受領文／§5-1〜5-4 の出力の要点の行／commit の sha と push の結果／判断を要した点（事実のみ）
- 停止したときは：停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 最後の行は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツールで行う（ヒアドキュメントで書かない）
- 本番のサーバーと DB に接続しない。秘密の値を貼らない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当の報告を Opus が転記）

- 実行: クラウドの Sonnet（2026-11-20 14:50〜14:51 UTC・実行記録 cse_01HHUUpS6aK3ZfmqPKTkCGUx）。受領文あり
- 作業場所: new-worktree.sh で release/login-alert-bin8（起点 origin/main 77971367b）
- §5-1: `OK: Prometheus 41 rules, Loki 6 rules, runbook 47 sections`
- §5-2: `yaml ok`
- §5-3: 3 files changed, 17 insertions(+), 15 deletions(-)・削除行 `15`
- §5-4: alerts.yml `2`・alerts.md `1`
- commit: a77af99ef0636e9e48b3d45a9a8074eb8729fed9（push 済み）
- Opus の照合: 3 ファイルとも、Opus が手元の写しで §4 の置き換えを試した結果と `cmp` で一致

END OF CARD
