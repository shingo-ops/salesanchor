<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。新設ファイルはバッククォートに入れない。 -->
# Phase 3 設計 — viewer-setting-blank-guard（閲覧ページ停止の再発防止）

> この文書は何か（専門用語なしの1行）: 配信の設定が空で保存されてお客さんの在庫ページが止まった件を、二度と起こさず、起きても止まる前に気づくための設計。

**対象ADR**: ADR-1019（閲覧ページ）・ADR-1014（配信の行の正本）・ADR-1012（24 時間保守運用・経路の正本は Alertmanager）・ADR-1071（失敗の文）・ADR-027（i18n）・ADR-067／ADR-144（UI）・ADR-135／ADR-136（危険パスと GO）
**recon**: docs/handoff/viewer-setting-blank-guard/recon.md
**親**: [在庫の閲覧専用ページ](../../specs/inventory-management/inventory-viewer/README.md)（区分: 既存の延長）
**日付**: 2026-11-12 ／ **担当**: Claude Opus（Planner・Architect）
**状態**: 設計案 第3版・設計審査済み（別セッションの reviewer が APPROVE・§11）・KGI は PO 未承認・実装未着手

---

## 1. あるべき姿（PO の言葉）

- 「停止したということは意図していない」（2026-11-12）
- 「この仕組みを標準化して管理定着させて継続させるための機械的な仕組みも出来ているか…外れた原因と再発防止策、CI・CDによる機械的な防止も」（2026-11-12）
- 「再発を防ぐ仕組みの設計書を作る」（2026-11-12）
- 「開発ルールも確認してレビュアーにも設計案をレビューしてもらい事実ベースで確実に成功するエビデンスを確立してくれ」（2026-11-12）

## 2. KGI（案・PO 未承認）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| K1 | 設定「何時間以内の投稿を出すか」に、空・空白だけ・文字・マイナスを保存しようとすると断られ、保存済みの値は変わらない | 必須の CI pytest で 4 種（空・空白だけ・`abc`・`-1`）を送る | 断られた数 4/4・値が変わった数 0 |
| K2 | 正しい値（`0` と `48`）は今までどおり保存できる | 必須の CI pytest | 2/2 |
| K3 | 設定パネルを閉じているあいだ、パネルの入力欄と「保存」ボタンがページに無い | 必須の CI vitest（画面部品の試験） | 閉じているとき 0 個 |
| K4 | 読み込みに失敗したとき・値が正しくないとき、保存ボタンが押せない | 必須の CI vitest | 読み込み失敗 1/1・不正な値 4/4（空・空白・`-1`・`1.5`） |
| K5 | 在庫の作り置きが 6 時間書けないと、新しい静かな Discord の場所に知らせが届く。他の警報はそこに来ない | 警報の試験（promtool）・送り先の試験（amtool）・必須の CI pytest（規則と送り先が消えたら赤）・本番で 1 回の試し鳴らし | 6 時間で鳴る・5 時間 59 分で鳴らない・BruteForceAttempt が新しい場所に行かない・試し鳴らし 1/1 |
| K6 | AI がブラウザでプログラムからボタンを押す既知の 6 通りを、見張りが止める | 見張りの試験（必須の CI pytest から呼ぶ） | 止めた数 6/6・読むだけ 3/3 と座標の押下 1/1 は通す |
| K7（全体） | 同じ原因（設定の空保存）で閲覧ページが「準備中です」になった回数 | 本番 Loki を 30 日ごとに 3 回数える（保管 30 日のため） | 90 日で 0 回 |

## 3. KPI

- 達成 KGI 数 ◯/7（K1〜K6 は各便のマージと反映のとき、K7 は便1 反映から 30・60・90 日目）。

## 4. recon の要点（全文は recon.md）

- 空の保存を断る場所が 1 つも無い（recon §2 観点1・観点5）。
- 閉じた設定パネルの「保存」も DOM に残る（recon §2 観点2）。
- 警報は 14 件鳴ったが、対応の記録は 0 件。同じ場所に認証の警報が 86 件流れていた（recon §2 観点5）。
- AI のブラウザ操作に見張りが無い。今回は AI がプログラムで「保存」を押した（recon §3）。

## 5. design（技術 How）— 4 つの守り

守りの強さの順: 5-1 が本体（どこから送られても空は保存されない）。5-2 は画面の補助。5-3 は「万一止まっても気づく」。5-4 は「AI の押し間違い」の補助。5-1 だけで今回の原因は止まる（OWASP の考え方・§7）。

### 5-1. API で断る（便1・backend）

- 変更ファイル:
  - `backend/app/services/tcg_distribution_svc.py`
  - `backend/app/routers/tcg_distribution.py`
  - `backend/app/tasks/viewer_inventory_cache.py`
  - 新設: backend/tests/test_distribution_settings_validation.py
- svc: `update_setting`（backend/app/services/tcg_distribution_svc.py:859）の先頭で、key が `max_age_hours` のとき `_max_age_hours({"max_age_hours": value})`（backend/app/services/tcg_distribution_svc.py:202）を呼ぶ。None なら新しい例外 `InvalidSettingValue` を送出し、UPDATE は走らせない。読む規則と書く規則が 1 か所になる（SSOT）。
  - 既存の `MaxAgeHoursUnsetError`（backend/app/services/tcg_distribution_svc.py:198）は「配信のときに未設定」を表す別の意味なので使い回さない。
- router: backend/app/routers/tcg_distribution.py:216-228 で `svc.InvalidSettingValue` を受け、422 を返す。前例は backend/app/routers/tcg_distribution.py:106-111（svc の例外を router で 409・422 に変える）。detail の文は ADR-1071 に合わせ「起きたこと＋次にすること」にする（例「0 以上の整数を入れてください」）。
- 上限は設けない。理由: 大きな値は「古い投稿まで全部出す」という意味で、閲覧ページは止まらない（`0` の無制限と同じ側）。`+5`・`1_000` も 5・1000 として読まれ、止まらない。今回の害は「None になる値」だけで、それを全部断る。
- tasks: backend/app/tasks/viewer_inventory_cache.py:48-69 の `_record_failure` から、テナント 4 宛ての Discord 通知（backend/app/tasks/viewer_inventory_cache.py:56-69）を除く。ログと失敗回数（`FAIL_KEY`）は残す。理由: 届け先が 0 件で 1 度も届いていない（recon §2 観点3）。届け先の正本は Alertmanager（ADR-1012・FEATURE-INDEX 51 行）。
- 試験（新設ファイル）: K1 の 4 種で 422 と、svc の UPDATE が呼ばれないこと（呼び出しを mock で数えて 0 回）。K2 の 2 種で 200 と UPDATE 1 回。`_record_failure` が Discord を呼ばないこと。CI は必須チェック「pytest (SQLite + PostgreSQL RLS)」（.github/workflows/test.yml）で走る。
- 触らない: 読む側の `_max_age_hours` と `build_distribution_rows`。他の key の扱い。

### 5-2. 画面で押させない（便2・frontend）

- 変更ファイル:
  - `frontend/src/pages/super-admin/components/DistributionSettingsDrawer.tsx`
  - `frontend/src/locales/ja.json`
  - `frontend/src/locales/en.json`
  - 新設: frontend/src/pages/super-admin/components/DistributionSettingsDrawer.test.tsx
- (1) 中身（入力欄と保存ボタン）は `open` のときだけ描く。枠は共用の Drawer のまま（金型 `frontend/src/components/Drawer.tsx` は変えない）。
- (2) 読み込み済みの印 `loaded` を足す。GET が成功するまで保存ボタンは押せない。
- (3) GET に失敗したら、今の「空のまま編集可能」（frontend/src/pages/super-admin/components/DistributionSettingsDrawer.tsx:50）をやめる。エラー文を出し、保存ボタンを押せないままにする。
- (4) 値が `^\d+$`（空でない 0 以上の整数）でないとき、保存ボタンを押せない。入力欄の下に理由を出す。
- (5) 保存で 422 が返ったら、その理由を出す。
- 文言: `distributionSettings.errors.loadFailed` と `distributionSettings.errors.invalidValue` を ja.json・en.json に同じキーで足す（ADR-027・check:i18n-missing-keys）。ja は ADR-1071 の決まり（check:error-text-next-action が、失敗の文に次にすることを示す語を求める）に合わせる。例: loadFailed「設定を読み込めませんでした。画面を開き直してもう一度お試しください」、invalidValue「0 以上の整数を入れてください（0 は無制限）」。
- 色・余白は既存のトークンのみ（ADR-067・ADR-144）。
- 試験（新設ファイル・vitest＋Testing Library）: K3（`open=false` で入力欄と保存ボタンが 0 個）、K4（GET 失敗で disabled 1/1、不正な値 4 種で disabled 4/4）。CI は必須チェック「Lint & Dark Mode Check (ADR-067)」の中の vitest で走る。同じフォルダに vitest の前例が 5 本以上ある（例 `frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.test.tsx`）。Playwright は CI の主 job が止まっている（.github/workflows/e2e.yml の `if: false`）ので使わない。
- 触らない: `frontend/src/components/Drawer.tsx`（金型）と `frontend/src/pages/super-admin/AnalysisRulesPage.tsx`。

### 5-3. 止まる前に人が気づく（便3・監視）

- 変更ファイル:
  - `monitoring/prometheus/alert_rules.yml`
  - `monitoring/prometheus/tests/alert_rules_test.yml`
  - `monitoring/alertmanager/alertmanager.yml`
  - `monitoring/tokens.yml`
  - `docker-compose.monitoring.yml`
  - `.github/workflows/monitoring-check.yml`
  - `.github/workflows/test.yml`
  - `docs/runbooks/alerts.md`
  - 新設: backend/tests/test_viewer_inventory_alert_contract.py
- 新しい警報 `ViewerInventoryExpiring` を `monitoring/prometheus/alert_rules.yml` の 245 行目の群に足す。
  - 条件: `(time() - viewer_inventory_updated_timestamp_seconds{job="backend"}) > 21600` が 5 分続く。保留かどうかは問わない。
  - 札: `tier: page`、`severity: critical`。
  - 6 時間の理由: 写しの寿命は 24 時間（backend/app/tasks/viewer_inventory_cache.py:33）。夜中に鳴っても、朝に直す時間が 12 時間以上残る。
- 閾値を `monitoring/tokens.yml` に `viewer_inventory_expiring_sec: 21600` として足す（既存 `viewer_inventory_stale_sec` の隣）。続く時間 5 分も同じファイルの `for_durations` に `viewer_inventory_expiring: "5m"` として足す。
- ClockSkew の止め（`monitoring/alertmanager/alertmanager.yml` の inhibit_rules）の対象に `ViewerInventoryExpiring` を足す。時刻を比べる規則のため。
- 送り先: 新しい受け手 `discord-viewer-urgent` を足す。route は**規則名で照らす**（`alertname="ViewerInventoryExpiring"`、`continue: true`）。既存の受け手（discord-server-alerts・ops-api）の前に置く。札 `tier="page"` では照らさない。札で照らすと、Prometheus 10 本・Loki 4 本の page の警報（BruteForceAttempt など）も流れ込むため（独立審査 BLOCKER-1）。
- 鍵: 受け手は `webhook_url_file: /etc/alertmanager/secrets/discord-webhook-viewer-urgent`（コンテナの中の場所）。prod2 のホストでは /opt/salesanchor-monitoring/secrets/alertmanager-discord-webhook-viewer-urgent に置く。`docker-compose.monitoring.yml` の alertmanager の volumes に 1 行足す（既存の 2 行と同じ形・docker-compose.monitoring.yml の alertmanager 節）。
- 送り先の試験: `.github/workflows/monitoring-check.yml` の amtool routes test に 2 行足す。
  - `ViewerInventoryExpiring` → discord-viewer-urgent・discord-server-alerts・ops-api。
  - `BruteForceAttempt tier=page` → discord-server-alerts・ops-api（新しい場所に行かない）。
- 警報の試験: `monitoring/prometheus/tests/alert_rules_test.yml` に「6 時間で鳴る」「5 時間 59 分では鳴らない」の 2 件（既存 ViewerInventoryStale の試験の隣）。
- 必須チェックでの固定（新設 pytest）: monitoring-check は必須チェックではない（`docs/specs/rule-enforcement/required-checks.txt` に無い）。そこで必須の pytest で、規則名・閾値 21600・route の照らし方・受け手の鍵ファイル名を YAML から読んで確かめる。消したり札で照らすように戻したりすると赤になる。
  - 監視のファイルだけを変える PR でもこの試験が走るように、`.github/workflows/test.yml` の変更検出（detect-changes の filters・.github/workflows/test.yml:45-54）と push の paths（.github/workflows/test.yml:19-29）に `monitoring/**` と `docker-compose.monitoring.yml` を足す。今は対象外のため、監視だけの PR では pytest が飛ばされ緑になる（独立審査 MAJOR-A）。
  - repo 直下のファイルを yaml で読む前例は backend/tests/test_compose_worker_env.py:10-12（PG が無くても走る形で書く）。
- 手順書: `docs/runbooks/alerts.md` に `ViewerInventoryExpiring` の節を足す。最初に見るのは設定の値と `[viewer-cache]` のログ。直し方は「設定画面で 48 を保存し直す」。
- 本番への配置（マージの後・prod2・手作業。前例 docs/handoff/ai-ops-247/card-stage1-bin7.md §8）:
  - (1) PO が Discord に新しい場所と webhook を作り、鍵のファイルを prod2 に置く（secrets の変更。PO 本人の操作）。
  - (2) 控え: 本番の alert_rules.yml・alertmanager.yml・docker-compose.monitoring.yml を日付付きで写し、sha256 を出す。Alertmanager の止めている通知（silence）の一覧を出す。作り直すと silence と送信の記録が消えるため（データを残す場所が無い）。1 件以上あれば止めて Opus に返す。
  - (3) main の 3 ファイルを送り、promtool と amtool で確かめてから置く。
  - (4) Prometheus を reload する。Alertmanager はマウントが増えるので、alertmanager のコンテナだけ作り直す（`docker compose -f docker-compose.monitoring.yml up -d --no-deps alertmanager`。Context7 /docker/compose: マウントが変わると作り直される）。
  - (5) amtool で route を見て、試しの警報を 1 本送る。先にコンテナの中で `amtool alert add --help` を出し、`--annotation` の書き方を確かめる（違えば止めて Opus に返す）。alertmanager のコンテナの中で `amtool alert add --alertmanager.url=http://localhost:9093 alertname=ViewerInventoryExpiring tier=page severity=critical job=backend --annotation=summary="試し鳴らし（便3 配置）"` を 1 回だけ実行する。新しい場所に届いたのを PO が目で見る（K5）。ops-api にも届くので、障害記録に 1 件残ることを報告に書く。試しの警報は時間が過ぎると「解決」としてもう一度届くことも、PO への報告で先に伝える。
  - (6) 設定のずれ点検（monitoring-config-drift.yml）を手で 1 回流し、ずれ 0 を確かめる。
- 戻し方: (2) の控えを置き直し、Prometheus を reload、alertmanager を作り直す。repo は revert の PR。
- 対象外: AI の自動対応（ADR-1012 の routines）。ADR-1012 は Proposed で、まだ動いていない。

### 5-4. AI がブラウザでプログラムから押さない（便4・個人側の見張り）

- 位置づけ: 補助。今回の原因は 5-1・5-2 で止まる。この見張りは「AI が画面外のボタンを、うっかりプログラムで押す」ことを防ぐ。わざと言い換えて抜ける使い方（`['cl'+'ick']` など）は対象外とし、そう書く。
- 変更ファイル（新設）:
  - scripts/agent-hooks/browser-click-guard/guard.py
  - scripts/agent-hooks/browser-click-guard/install.sh
  - scripts/agent-hooks/browser-click-guard/rollback.sh
  - scripts/agent-hooks/browser-click-guard/test_guard.py
  - backend/tests/test_browser_click_guard_contract.py（必須の pytest から guard.py を読み込んで試験を回す。repo 直下を読み込む前例は backend/tests/test_adr119_backfill_source_guard.py:39-41）
  - 変更: `docs/ai-agents/executor-checklist.md`
- ADR: 前例（ADR-1029・ADR-1045）どおり、便4 の最初に ADR を起案する。置き方は `docs/specs/local-hooks-ssot/README.md`。
- 照らす道具と止める形（既知の 6 通り）:
  - (1) `mcp__claude-in-chrome__javascript_tool` の中に `.click(`・`dispatchEvent(`・`.requestSubmit(`・`.submit(` がある。
  - (2) `mcp__claude-in-chrome__browser_batch` の中の javascript_tool に (1) の形がある（中の道具名は短い名前 `javascript_tool` でも全体名でも止める。試験で両方を当てる）。
  - (3) `mcp__claude-in-chrome__browser_batch` の中の computer の押下に `ref` がある。
  - (4) `mcp__claude-in-chrome__computer` の押す操作（left_click など）に、座標でなく `ref` がある。
  - (5) `mcp__playwright__browser_evaluate` に (1) の形がある。
  - (6) `mcp__playwright__browser_run_code_unsafe` に (1) の形がある。
  - 止めたら `permissionDecision: "deny"` と日本語の理由「押すときは画面の座標で押し、押す前に画面写しで開いているパネルを確かめてください」を返す。形は既存の見張り scripts/agent-hooks/master-register-rules-guard.py:51-52 と同じ。
- 通すもの: DOM を読むだけのプログラム、座標での押下、`mcp__playwright__browser_click`。
  - browser_click は止めない。Playwright の押下は「inert でない・見えている・その場所で本当に押せる」を確かめてから押すため、閉じたパネルには届かない（Context7 /microsoft/playwright の actionability.md と dom.ts の `'non-inert'`）。
- 決まりの文: `docs/ai-agents/executor-checklist.md` に 1 行（「ブラウザで押すのは座標か Playwright の押下だけ。プログラムからの押下は見張りが止める」）。
- 本番への配置: Mac の ~/.claude/settings.json に入れる（install.sh）。戻し方は rollback.sh。

## 6. 弊害・トレードオフ

- 5-1: 空にして「配信を止める」使い方はできなくなる。→ 実測で、空の保存は 11/10・11/11 の 2 回だけで、どちらも意図しない操作だった（recon §1）。閲覧ページだけを止める正規の手段は今は無い（`TCG_AUTO_DISTRIBUTE` はシートへの自動配信の切り替え。backend/app/tasks/tcg_extraction.py:703）。必要になったら別の設計で足す。
- 5-1: テナント 4 宛ての Discord 通知が無くなる。→ もともと届いていない（届け先 0 件）。気づく役は 5-3 が持つ。
- 5-2: 読み込みに失敗すると設定を直せない。→ エラー文で知らせる。空のまま保存されるよりは安全。
- 5-3: 監視のファイルだけを変える PR でも backend の試験が走り、CI の時間が延びる（延びる分は未測定。便3 の PR で測る）。
- 5-3: Discord に場所が 1 つ増える。→ 照らすのは 1 本の規則だけなので、鳴るのは閲覧ページが 6 時間止まったときだけ。
- 5-4: AI のブラウザ作業が遅くなる（座標で 1 回ずつ押す）。→ 一括の作業は、画面でなく API の正規の道で行う（別テーマ）。正当に必要な場面は PO の 1 回限りの許可（permit-danger.sh）で通す。

## 7. 外部・過去事例の参照と我々への応用

- 事例1: OWASP Input Validation Cheat Sheet（https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html 、2026-11-12 参照）は「入力の確かめはサーバー側で必ず行う。画面側の確かめは使い勝手のためで、守りにはならない」とする。→ 応用: 5-1 を守りの本体とし、5-2 は補助にする。今回、画面以外（AI のプログラム）から空が送られたので、この考え方が当てはまる。
- 事例2: Google SRE book 第 6 章（https://sre.google/sre-book/monitoring-distributed-systems/ 、2026-11-12 参照）「お客さんに見える症状で知らせる」「すべての page は動ける内容にする」。→ 応用: 5-3 は「写しが消える＝お客さんの画面が止まる」前の症状で、雑音の無い場所に 1 本だけ送る。
- 事例3: Playwright の actionability（Context7 /microsoft/playwright、2026-11-12 参照）。押す前に「見えている・inert でない・その場所の一番上にある」を確かめる。→ 応用: 5-4 で Playwright の押下は止めず、プログラムの押下だけを止める根拠。
- 過去事例: 本件（2026-11-10〜12・recon §1）。鳴った 14 件が雑音と同じ場所に流れ、対応 0 件だった。
- 数値の効果を示す外部の実測は見つけていない。効果は K7 の 90 日の数で測る。

## 8. 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1: 空・空白・`abc`・`-1` が 422 で値が変わらない | 必須 CI pytest backend/tests/test_distribution_settings_validation.py（便1で新設） |
| K2: `0` と `48` が保存できる | 同上 |
| K3: 閉じているとき入力欄・保存 0 個 | 必須 CI vitest frontend/src/pages/super-admin/components/DistributionSettingsDrawer.test.tsx（便2で新設） |
| K4: 読み込み失敗・不正な値で保存を押せない | 同上 |
| K5: 6 時間で鳴り 5 時間 59 分で鳴らない・BruteForceAttempt は新しい場所に行かない・本番で 1 回届く | CI promtool と amtool（`.github/workflows/monitoring-check.yml`）＋必須 CI pytest backend/tests/test_viewer_inventory_alert_contract.py ＋本番の試し鳴らし（PO が目で見る） |
| K6: 既知 6 通りを止め、読むだけ 3・座標 1 を通す | 必須 CI pytest backend/tests/test_browser_click_guard_contract.py（便4で新設） |
| K7: 同じ原因の停止 0 回（90 日） | 本番 Loki を便1 反映の 29・58・87 日目と 90 日目に数える。各回は前回の終わりから今までの窓（重なり 1 日以上・保管 30 日以内）で、`viewer_inventory_not_ready` の 503 と設定の PUT を数える。先に件数を出し、150 行ずつに分けて照合する（reader 鍵は黙って行が切れることがあるため）。数えた窓の始まりと終わりを毎回記録する |

## 9. 計画票

| 便 | 内容 | 担当 | 危険パス（ADR-135） | GO | 戻し方 |
|---|---|---|---|---|---|
| 1 | API で断る（5-1）＋テナント 4 宛て通知を除く＋試験 | クラウドの Sonnet | いいえ | GO 記録あり（利用者に影響する道） | revert の PR |
| 2 | 画面で押させない（5-2）＋vitest＋文言 | クラウドの Sonnet | いいえ | GO 記録あり（利用者に影響する道） | revert の PR |
| 3 | 6 時間の警報と静かな送り先（5-3）＋試験＋手順書 | クラウドの Sonnet（repo）・Opus（prod2 への配置） | いいえ（monitoring/ は対象外） | GO 記録あり。secrets（Discord の鍵）は PO 本人の操作 | §5-3 の戻し方 |
| 4 | ブラウザの見張り（5-4）＋ADR | クラウドの Sonnet（原本）・Opus（Mac に入れる） | **はい**（scripts/） | GO #番号を受けるまで main に入れない | rollback.sh と revert の PR |

- 便1 を最初に出す。これだけで今回の原因（どこから送られても空は保存されない）が止まる。
- 1 便ずつ反映して測ってから次へ（変更は一度に 1 つ）。

## 10. 接触面分析（6 面）

- 逆参照: `max_age_hours`・`DistributionSettingsDrawer`・`ViewerInventoryStale`・`_record_failure` を拡張子を問わず grep（.md 含む）。recon §0・§2 に記載。
- ①人: PO は便3で Discord の場所と鍵を作る。設定画面で空を保存できなくなる（今まで空にする必要は無かった）。
- ②エージェント: ブラウザでプログラムから押せなくなる（便4）。executor-checklist に 1 行足して周知する。並行セッションには見張りの文で伝わる。
- ③機械: 必須の pytest・vitest に試験が増える。Alertmanager の route と受け手が 1 本ずつ増える。
- ④データ: 設定表 `tcg_distribution_settings` の値の形は変えない（列・表は増やさない）。tenant_004 のデータには触らない。
- ⑤本番: 便1・便2 は通常の配備。便3 は prod2 の手作業の配置（§5-3）。migrations は無い。
- ⑥外部: お客さん（閲覧者）への見え方は変わらない。止まりにくくなるだけ。Discord に場所が 1 つ増える。

## 11. 設計審査

- 第1版: 同一 AI の自己審査で APPROVE（review-opus.md）。
- 第1版の独立審査（別セッションの Opus reviewer・2026-11-12）: **REVISE**。BLOCKER 1・MAJOR 9・MINOR 7。全文は repo 外の審査メモ。
- 第2版での直し:

| 指摘 | 直したところ |
|---|---|
| BLOCKER-1 札 page で照らすと雑音が流れ込む | §5-3 規則名で照らす・amtool で BruteForceAttempt が来ないことを試す |
| MAJOR-1 Playwright が CI で走らない | §5-2・§8 vitest に替えた |
| MAJOR-2 守り手が必須チェックでない | §5-3・§5-4 必須の pytest で固定する試験を足した |
| MAJOR-3 便4 は危険パス | §9 危険パス・GO の列 |
| MAJOR-4 secrets は PO 本人 | §5-3 配置(1)・§9 |
| MAJOR-5 鍵の置き場の誤り | §5-3 ホストの場所と compose の 1 行 |
| MAJOR-6 prod2 の配置手順が無い | §5-3 配置(1)〜(6)と戻し方 |
| MAJOR-7 月次成績表は無い | §12 維持の仕組みから外した |
| MAJOR-8 見張りの抜け道 | §5-4 既知 6 通り・位置づけを補助に・Playwright の押下は根拠付きで通す |
| MAJOR-9 Loki は 30 日 | §2 K7・§8 30 日ごとに 3 回 |
| 再審査 MAJOR-A 監視だけの PR で固定試験が走らない | §5-3 test.yml の検出対象に monitoring を足す |
| 再審査 MINOR-a〜f | for_durations・silence の確認・K7 の窓・batch の道具名・amtool の完全な形・UPDATE を mock で数える |
| MINOR-1〜6 | router・上限を設けない理由・tokens.yml・ClockSkew・ADR-1071・recon の行番号・戻し方・維持の仕組みを末尾（§12）へ |
| MINOR-7 repo から確かめられない数字 | recon §2 観点5 に「本番を読み取りで実測・repo 外」と書いた |

- 第2版の再審査（同じ reviewer）: REVISE。17 件中 15 件解決・2 件一部（MAJOR-2 は MAJOR-A と同じ穴、MINOR-7 は本番の数字を審査役が確かめていない）。新しく MAJOR-A 1 件・MINOR 6 件。第3版で上の表のとおり直した。
- 第3版の最終確認（同じ reviewer）: **APPROVE**。守り 1〜4 と K7 はすべて実現できる（YES）。判定を変えない小さな点 3 件（amtool の書き方を先に確かめる・試しの警報の「解決」の再通知・CI の時間）は本版に反映した。
- 残る未確認: 監視だけの PR で pytest-run が実際に走るところ（便3 の PR の Actions 画面で確かめる）。
- 未解決（PO の判断が要る）: KGI 7 件の承認（特に K5 の「6 時間」と新しい Discord の場所）。

## 12. 維持の仕組み

- 守り手: `.github/workflows/process-artifacts-gate.yml`（この設計の recon・design の相互参照）
- 守り手: 必須 CI pytest（便1 の試験。空の保存が通るように戻すと赤）
- 守り手: 必須 CI vitest（便2 の試験。閉じたパネルに保存ボタンが戻ると赤）
- 守り手: 必須 CI pytest（便3 の固定試験。警報か送り先を消す・札で照らすと赤）と、必須でない monitoring-check（promtool・amtool）
- 守り手: 必須 CI pytest（便4 の見張りの試験）と、個人側の見張り browser-click-guard（原本は repo、変更は PR のみ）
- 守り手: 設定のずれ点検 `.github/workflows/monitoring-config-drift.yml`（prod2 の設定が main と違えば鳴る）
- 対象: 設定の書き口・設定パネル・閲覧の作り置きの警報・AI のブラウザ操作
