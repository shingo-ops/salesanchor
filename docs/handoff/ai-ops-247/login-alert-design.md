# ログイン失敗の見張りの鳴る条件の見直し（設計）

- 状態: PO 承認済み（2026-11-20 PO「1」= 選択肢「この設計で承認する」への回答）。Opus 作成・設計の自己審査済み。本番への反映は別の GO で行う（実装未着手）。
- 親: `docs/handoff/ai-ops-247/stage4-requirements.md`（D4・C4・C6・K5・G4、ロードマップの順 5 と順 8）
- 対象 ADR: ADR-1012（24 時間保守運用・アラート札 page・auto・ticket）
- 対象の見張り: BruteForceAttempt（札 page）・SustainedAuthFailure（札 ticket）

## 1 目的（PO の言葉で）

ログイン失敗の通知が記録の 85% を占めている（10/16〜11/08 の 658 件中 562 件。`docs/handoff/ai-ops-247/stage4-recon.md` §3）。本当の攻撃や大量のログイン失敗のときだけ鳴るようにし、AI を無駄に起こさない（G4）。攻撃を見逃さないことは今と同じに守る。

## 2 現在地（recon。2026-11-20 Opus 実測）

### 2-1 今の鳴る条件

- `monitoring/loki/rules/jarvis/alerts.yml:8-24`（origin/main 0a0b2b141）
  - BruteForceAttempt: `sum(count_over_time({job="containerlogs"} |~ "401|403|auth.*fail|login.*fail|Unauthorized" [5m])) > 20`・for 1m
  - SustainedAuthFailure: `sum(count_over_time({job="containerlogs"} |~ "401|403|auth.*fail|Unauthorized" [1h])) > 50`・for 5m
- しきい値の正本: `monitoring/tokens.yml` の `brute_force_per_5m: 20`・`auth_failure_per_1h: 50`・`for_durations.brute_force: "1m"`・`for_durations.auth_failure: "5m"`
- 手順書: `docs/runbooks/alerts.md:130-145`
- CI の検査: `.github/workflows/monitoring-check.yml:104`（lokitool rules check）・`monitoring/scripts/check_alert_rules.py:15`（札・手順書リンク）
- Loki の保存期間 30 日（`monitoring/loki/loki-config.yaml:29`）。見張りは Loki の ruler が評価し Alertmanager へ送る（同 :31-37）

### 2-2 今の条件が何を数えているか（直近 24 時間・Loki で実測）

生出力: `/tmp/CC報告ファイル/ai-ops-stage3/login-alert-recon/`（classify-24h.txt・http-paths-24h.txt）

- 今の正規表現に当たった行 1681 行
  - 認証と関係ない行 1163 行（69%）: 数字の一部（例 `product_id=440303` の「403」、時刻やミリ秒の「,403」）
  - Grafana が Loki に投げた問い合わせの URL（正規表現の文字そのもの）1 行
  - HTTP 401 が 457 行・HTTP 403 が 60 行
- 401・403 の内訳（多い順）: セッション切れの更新 `POST /api/v1/auth/refresh` 401 が 213 行・`/me/permissions` 401 48・`/conversations` 401 48・**ログイン `POST /api/v1/auth/login` 401 48**・反映時の確かめ `GET /design/` 401 46（`.github/workflows/deploy.yml:1235` が 401 を期待）・`/login-approvals/pending` 401 36・`/roles` 403 34 ほか
- 過去 7 日、今の条件の 5 分の数の最大 939・20 を超えた 5 分枠 172（broad-7d.jsonl）。ほとんどがログイン失敗ではない。

### 2-3 本当のログイン失敗

- ログイン失敗を数える係: `backend/app/cache.py:307-337`（`AUTH_FAIL_MAX = 10`・15 分。同じ IP で 10 回失敗すると 429 で締め出す）
- この係を呼ぶ「ログイン前」の道（`backend/app/routers/auth.py`・`viewer.py` を AST で列挙）:
  `POST /api/v1/auth/login`・`/auth/passkey/login/verify`・`/auth/password-reset/confirm`・`/auth/login-requests/recovery`・`/viewer/login`・`/viewer/password-reset/confirm`
  （失敗は 401、締め出しは 429。`auth.py:395-422`・`auth.py:1096-1111`）
- 1 件の失敗はログに 2 行出る: 入口（nginx。`"POST ... HTTP/2.0" 401 32 ...`）とバックエンド（uvicorn。`"POST ... HTTP/1.1" 401 Unauthorized`）。上の 48 行は 24 件の失敗。
- 24 件はすべて同じ 1 つの Windows の Chrome から、ログイン画面で入力したもの（入口の行の利用者の情報）。反映（deploy）の直後に多い。誰の操作かは**未確認**（攻撃の形ではない: 5 分に 1 件以下）。
- Prometheus の `http_requests_total` は使えない: 14 日でログインの 401 が 167 件と出るが、バックエンドが反映のたびに立ち直り（24 時間で 23 回）、立ち直り後の最初の 1 件を数え落とす。Loki は全行を持つ（prom-login-14d.txt）。

### 2-4 新しい数え方で過去 14 日を数え直した結果

対象: 上の 6 つの道で、バックエンドの行の `401 Unauthorized` か `429 Too Many Requests` だけ（入口の行と二重に数えない）。
生出力: proposed6-5m-14d.jsonl・proposed6-14d.jsonl・proposed-7d.jsonl

| 枠 | 14 日の最大 | 今のしきい値 |
|---|---|---|
| 5 分（1 分刻みで数えた） | 2 件 | 20 件 |
| 1 時間（5 分刻みで数えた） | 6 件 | 50 件 |
| 1 日の合計 | 2〜49 件 | — |

## 3 設計

### 3-1 変えること（変更前 → 変更後）

`monitoring/loki/rules/jarvis/alerts.yml` の 2 本の `expr` を次の 1 つの数え方に揃える（窓としきい値だけが違う）。

```
sum(count_over_time({job="containerlogs"} |~ "\"POST /api/v1/(auth/login|auth/passkey/login/verify|auth/password-reset/confirm|auth/login-requests/recovery|viewer/login|viewer/password-reset/confirm) HTTP/[0-9.]+\" (401 Unauthorized|429 Too Many Requests)" [5m])) > 10
```

| 見張り | 窓 | しきい値 変更前 → 変更後 | for | 札 |
|---|---|---|---|---|
| BruteForceAttempt | 5 分 | 20 → **10** | 1m（不変） | page（不変） |
| SustainedAuthFailure | 1 時間 | 50 → **20** | 5m（不変） | ticket（不変） |

- しきい値は `monitoring/tokens.yml` の `brute_force_per_5m: 10`・`auth_failure_per_1h: 20` に直し、ルールの注釈と合わせる（正本は tokens.yml 1 か所）。
- 決め方:
  - 5 分 10 件 = アプリが 1 つの IP を締め出す回数（`cache.py:307`）。14 日の最大 2 件の 5 倍。
  - 1 時間 20 件 = 14 日の最大 6 件の 3 倍以上。5 分に 10 件未満でゆっくり続く失敗はこちらで拾う。
- 説明文（summary・description）を「ログインの失敗（401）と締め出し（429）」に直す。手順書 `docs/runbooks/alerts.md` の 2 節の「何が起きているか」「最初に見るもの」を新しい式に直す。
- 触らないもの: 他の Loki の見張り 4 本・Prometheus の見張り・アプリのコード・Alertmanager の送り先・札。

### 3-2 選ばなかった案

| 案 | 選ばない理由 |
|---|---|
| Prometheus の `http_requests_total` で数える | 反映のたびの立ち直りで最初の 1 件を落とす（14 日 167 件 vs Loki の行数）。反映が 1 日 20 回あるので数え落としが多い |
| アプリに専用の数を足す | バックエンドのコード変更と反映が要る。同じ数え落としの問題が残る。Loki で正確に数えられるので不要 |
| IP ごとに数える | IP が通知の文面に載る（個人に近い情報）。アプリが既に IP ごとに締め出す。合計で十分 |
| 入口（nginx）の行で数える | どちらでも同じ数。バックエンドの行は道の名前が確定していて、入口の画面の配信の行と混ざらない |
| しきい値だけ上げる | 数字の一部や 403 を数える誤りが残り、関係ない行の増減で鳴る |

### 3-3 弊害とその手当て

| 弊害 | 手当て |
|---|---|
| uvicorn のログの形が変わると黙って数えなくなる | 受入 A4 で反映後に 1 回わざと失敗させて数に出ることを確かめる。uvicorn の版を上げる PR では手順書の式を確かめる（手順書に書く） |
| ログイン後の画面での 401・403 の急増（権限の不具合）は鳴らなくなる | それはログイン失敗ではない。5xx などは別の見張り（BackendHighErrorRate）が見る。必要なら別テーマにする |
| しきい値が低すぎて正しい利用で鳴る | 14 日の最大の 3〜5 倍。反映後 7 日の鳴った回数を数える（A5） |

## 4 受入条件

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | CI の見張りの検査が通る | `monitoring-check`（lokitool rules check・check_alert_rules.py）が緑 |
| A2 | tokens.yml とルールのしきい値が一致 | PR の差分で `brute_force_per_5m: 10`・`auth_failure_per_1h: 20` とルールの `> 10`・`> 20` を目で照合 |
| A3 | prod2 に新しいルールが入り Loki が読んでいる | prod2 の Loki ruler の API でルールの式が新しいもの・状態 inactive |
| A4 | 本当の失敗を数える | 反映後に 1 回だけ存在しない宛先でログインを失敗させ、5 分以内に新しい式の数が 1 以上になる（締め出しの 10 回には遠い） |
| A5 | 誤って鳴らない | 反映後 7 日で 2 本の見張りの鳴った回数 0（本当の攻撃が無い限り）。前は 1 日約 23 件の記録 |
| A6 | 攻撃なら鳴る | 過去 14 日の数え直しで新しい式が数える行がある（2-4 表）。A4 で数が増えることを確かめる。10 回の失敗をわざと起こす試しは本番の締め出しと page を起こすので行わない |

## 5 反映の順番と戻し方

- 順番: 便G の 24 時間後（C6）以降・ロードマップ順 8（11/29〜12/2）。1 つの PR（ルール・tokens.yml・手順書）→ CI → 審査役 → GO（監視の設定のみ・DB 変更なし）→ main → prod2 にルールを写して Loki を読み直す（前回の Prometheus と同じく控えを取ってから）。
- 戻し方: PR を revert → prod2 の控えからルールを戻して読み直す。
- 測り方: A3〜A5。K5（1 週間のログイン失敗の通知の件数）を反映前後で比べる。

## 6 維持の仕組み

- 守り手: CI の `monitoring-check`（式の文法・札・手順書リンク）／tokens.yml がしきい値の正本／手順書の 2 節
- 数え直し: 反映後 7 日に K5 を数え、stage4-requirements の K5 に書く。

## 7 外部事例

- 事例は使わない。しきい値の根拠は本番 14 日の実測（2-4）とアプリの締め出し回数（cache.py:307）で、他社の数字より直接の根拠になるため。

## 8 設計の自己審査（Opus。同じ AI による審査で第三者の審査ではない）

- 判定: APPROVE（設計として実装に渡せる）
- 確かめたこと: 式の対象の道 6 つはコードの AST の列挙と一致／二重に数えない（バックエンドの行の `401 Unauthorized` だけ。入口の行は `401 <数字>` で当たらない）／tokens.yml と札は不変の部分が触られない／受入条件はすべて観測で ○× が出る
- 未解決: 毎日のログイン失敗 24 件の主（Windows の Chrome 1 台）は未確認。見張りの設計には影響しない（数が少なく攻撃の形ではない）
