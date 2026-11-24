<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 実装カード 段階4 便3 — 障害記録の「見張りの名前」と「強さ」を相談係に見せる（C3-2）

> この文書は何か: AI 保守運用 24 時間化 段階4 の 3 便目の段取り表です。相談係（クラウドの AI）が読む伏せた窓で、障害記録の見張りの名前（alertname）と強さ（severity）を伏せるのをやめます。PO 決定 D3 をそのまま実装します。`migrations/` のファイルを変えるので危険便（GO #番号が要る）です。

- 設計: `docs/handoff/ai-ops-247/stage4-design.md` §0 E5（:18）、§2 C3-2（:63）、§12 D3（:189）
- 対象ADR: ADR-1012（段階4）、ADR-1052（伏せた窓）
- 状態: 設計案作成済み。設計審査（クラウド）は未。実装は未着手
- 危険便: はい（`migrations/20261024_100300_create_ai_cloud_views.sql` を変える。ADR-135・ADR-136）。GO #番号が要る（POの委任に基づくClaude Opus発行）
- 実装担当: クラウドの Sonnet（RemoteTrigger の一回実行）。push して止まる。PR は Opus が作る
- PO の決定: D3「C3-2 を採る。alertname と severity を伏せる対象から外す（実装カードで行う）」（設計 §12 :189）。この表で新しく PO に聞くことは無い

## 0. 前提の事実（origin/main f6d54446e で行番号を確かめた）

分類の正本と流れ:
- 伏せた窓の分類の正本は `migrations/20261024_100300_create_ai_cloud_views.sql`。冒頭の注記「分類表 ai_cloud_meta.column_class を空にして下の 1165 行を入れ直す（このファイルが正本…）」（:3）。元の表は `docs/handoff/cloud-case-ai/stage1-column-class.tsv`（:6）。
- 今の行: `('public','ops_incidents',ARRAY['alertname'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),`（:166）と `('public','ops_incidents',ARRAY['severity'],'mask', 同じ理由),`（:168）。status は allow（:169）。
- tsv は alertname の行（:232）と severity の行（:240）。
- 分類表の決まり: class は allow / mask / mask_bare、allow なら reason が空でない（`migrations/20261024_100000_create_ai_cloud_meta.sql:16-19`）。
- このファイルは記録の対象ではない。毎回の移行の最後に EXIT trap が流す（`scripts/run_all_migrations.sh:425-449`）。記録の対象は `^run_(sql|py)` の行だけ（`scripts/lib/migration_record.sh:61-86`）で、このファイルは `docker exec … < "${REPO_DIR}/${AI_CLOUD_CREATE_SQL}"` で流れる（`scripts/run_all_migrations.sh:448`）。だからファイルを変えても記録の食い違い（(b)）にはならない。前例: 2026-11-16・11-18・11-20 に同じファイルを変えて本番に出した（`git log origin/main -- migrations/20261024_100300_create_ai_cloud_views.sql`）。

値はどこから来るか:
- 見張りの知らせの口は、知らせのラベルの alertname（無ければ `unknown`）と severity をそのまま入れる（`backend/app/routers/ops.py:253-254`）。口は鍵が要る（同 :230 `require_ops_ingest`）。
- 人の報告の口は alertname に決まった語 `discord-bug-report` を入れ、severity は入れない（`backend/app/routers/ops.py:559-567`）。
- 本番の今の値（2026-11-24 18:52 JST、読み取りの鍵の道 `ai_ro.public__ops_incidents`。生の出力 /tmp/CC報告ファイル/verify3/alertnames.tsv）: alertname は 16 種類、最長 22 字（BruteForceAttempt・SustainedAuthFailure・ContainerUnhealthy・HighMemoryUsage・ViewerInventoryStale・KumaMonitorDown・ServiceDown・BackendHighLatency・RecoveryCheckFailed・BackendWorkerSaturated・ContainerStateStale・CeleryHeartbeatStale・CeleryQueueBacklog・OpsPipelineTest・BackupTimestampAbsent・discord-bug-report）。severity は critical・warning・info・空の 4 種類。人の名前・メール・お客様の文は 0 件。

相談係の指示書:
- `docs/ai-agents/ops-incident-agent.md:132` に「通知の名前（alertname）と強さ（severity）は今は伏せてある」とある。この便で直す。

ほかに伏せてあることを前提にしたコード・試験:
- `backend/tests/ops/test_ai_cloud_views.py` に ops_incidents・alertname・severity の語は 0 件（`grep`）。分類の行数の試験は `== 1165`（:486）。この便は行の数を変えない（class と reason だけ変える）。
- 伏せた数の試験（:424-445）は「ビューの masked の数 = mask 系の列の数」を毎回数え直すので、数を書き換える所は無い。

開いている PR で同じファイルを触る物: #5248（会社の連絡手段の表を消す。PO 本人の GO 待ち）。行は違う所。

## 1. 範囲

変える（このほかは触らない）:
- `migrations/20261024_100300_create_ai_cloud_views.sql` の :166 と :168 の 2 行
- `docs/handoff/cloud-case-ai/stage1-column-class.tsv` の :232 と :240 の 2 行
- `backend/tests/ops/test_ai_cloud_views.py` に試験を 1 つ足す（:1017 の後ろ、:1060 の前）
- `docs/ai-agents/ops-incident-agent.md` の :132 の 1 行
- 台帳 `.claude-pipeline/active-work.d/release-ai-ops-stage4-bin3-allow.md`

触らない: labels・annotations など ops_incidents のほかの列の分類（mask のまま）、`backend/app/` のコード、`scripts/`、ほかの表の分類、行の数（1165 のまま）。

## 2. 作り方（ブランチ release/ai-ops-stage4-bin3-allow）

（１）`migrations/20261024_100300_create_ai_cloud_views.sql`
- :166 を次の 1 行にする:
  `  ('public','ops_incidents',ARRAY['alertname'],'allow','値は自分たちの見張りの規則の名前と口の決まった語（unknown・discord-bug-report）だけ・口は鍵が要る（PO 決定 D3）'),`
- :168 を次の 1 行にする:
  `  ('public','ops_incidents',ARRAY['severity'],'allow','値は自分たちの見張りの規則の強さ（critical・warning・info）だけ・口は鍵が要る（PO 決定 D3）'),`
- 行の並び・ほかの行・:3 の「1165 行」は変えない。

（２）`docs/handoff/cloud-case-ai/stage1-column-class.tsv`
- :232 の alertname の行の class を `allow`、reason を（１）の alertname と同じ文にする。data_type は `text` のまま。
- :240 の severity の行も同じ（reason は（１）の severity の文）。
- 区切りはタブのまま。ほかの行は変えない。

（３）`backend/tests/ops/test_ai_cloud_views.py` に `test_t10_ops_incidents_alertname_severity_are_allowed` を足す。形は :1017 の `test_t10_calendar_color_key_is_classified_on_bootstrapped_db` に合わせる:
- `_new_db(cluster.control, "ai_cloud_t10_ops")` で専用の DB を作り、終わったら `DROP DATABASE IF EXISTS … WITH (FORCE)` で消す（:1054-1057 と同じ）。
- 流す順: `salesanchor_app` のロールが無ければ作る（`backend/tests/test_ops_case_router.py:140` と同じ文）→ `_read(_AI_READER_SQL)` → `_read(_ROLE_SQL)` → `_read(_META_SQL)` → `_read("20261016_100000_create_ops_incident_tables.sql")` → `_read(_CREATE_SQL)`。
- 確かめること:
  - `ai_cloud_meta.column_class` の `schema_pattern='public' AND table_name='ops_incidents'` で、alertname と severity の行がそれぞれ 1 行・class が `allow`・reason が空でない。
  - `ai_cloud_meta.build_columns` の `view_name='public__ops_incidents'` で、alertname と severity の mode が `pass`。
  - 同じ view で labels・annotations・fingerprint・root_cause・review_note の mode が `pass` でない（伏せたまま）。
- ほかの試験は変えない。

（４）`docs/ai-agents/ops-incident-agent.md:132` の「通知の名前（alertname）と強さ（severity）は今は伏せてある（…）。名前は、サーバーが起こすときの文で渡す（…）。」を、次の文にする:
  「通知の名前（alertname）と強さ（severity）も見える（`migrations/20261024_100300_create_ai_cloud_views.sql` の ops_incidents の行。PO 決定 D3）。labels・annotations などほかの列は伏せたまま。」
  同じ行の前半（障害の記録の読み方・時刻・状態・kind）は変えない。

（５）台帳を 1 つ足す（形は `.claude-pipeline/active-work.d/release-ai-ops-stage4-card-bin2.md` と同じ。状態 IN_PROGRESS・PR# は空）。

（６）試験を流す: `backend/tests/ops/test_ai_cloud_views.py` 全部（新しい試験を含む）。手元に PostgreSQL が無く流せないときは、流せなかったことと理由を書く（CI で見る）。

（７）commit して push して止まる。PR は作らない。

## 3. 想定される分岐（ここに無い分岐は止まって報告）

| 起きたこと | すること |
|---|---|
| 行番号が実物とずれる | 中身（`'ops_incidents',ARRAY['alertname']` などの語）で同じ行を探す。中身も違えば止まる |
| ops_incidents の alertname・severity の行が 2 行以上ある | 止まる |
| `:486` の数が 1165 でない | 止まる（誰かが行を足した。数を合わせて直さない） |
| 新しい試験で `20261016_100000_create_ops_incident_tables.sql` を流すところが失敗する | 名前と生の出力を出して止まる。移行のファイルは変えない |
| 新しい試験で alertname の mode が pass にならない | 生の出力を出して止まる。生成の関数（`migrations/20261024_100000_create_ai_cloud_meta.sql`）は変えない |
| ほかの試験が 1 つでも赤 | 名前と生の出力を出して止まる |
| tsv の列の数（6 列）が合わない行ができる | 直してから進む（タブの抜け）。直せなければ止まる |

## 4. 本番での確かめ（Opus。本番反映の後）

読み取りの鍵の道（`ai_ro`）には `ai_cloud` と `ai_cloud_meta` が無い（2026-11-24 に 42P01 を確かめた）。そこで PO の許可（2026-11-24「必要な権限は全て…使用して良い」）の範囲で、無制限の鍵で本番の DB を読むだけで確かめる。SQL はファイルに書き、`BEGIN READ ONLY` と `ROLLBACK` で包む。値は名前と強さだけ読み、ほかの列は読まない。

| # | 確かめること | 合格の形 |
|---|---|---|
| V1 | 反映の前に、`ai_cloud.public__ops_incidents` を ai_reader_cloud の役で読んだ alertname・severity | 伏せた値（今の形の基準値） |
| V2 | 反映の後の `ai_cloud_meta.build_log` の最新行 | 反映の時刻より後・ok |
| V3 | 反映の後の `ai_cloud_meta.column_class` の行数と、ops_incidents の alertname・severity の class | 1165 行・2 つとも allow |
| V4 | 反映の後に ai_reader_cloud の役で読んだ alertname・severity の種類と数 | 読み取りの鍵の道（`ai_ro.public__ops_incidents`）で同じ時に数えた種類と数に一致 |
| V5 | 反映の後の labels・annotations | 伏せたまま（V1 と同じ形） |

## 5. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 分類表で alertname・severity が allow（理由つき） | 新しい試験が CI で緑 |
| 伏せた窓で 2 列がそのまま見え、ほかの列は伏せたまま | 新しい試験（mode）・本番 V3〜V5 |
| 分類の行数は 1165 のまま | `backend/tests/ops/test_ai_cloud_views.py:486` が緑・本番 V3 |
| 伏せた窓の作り直しが成功 | 本番 V2 |
| 相談係の指示書が今の見え方と合う | `docs/ai-agents/ops-incident-agent.md:132` の差分を Opus が読む |
| 触ったファイルが §1 の範囲だけ | `git diff --name-only origin/main...HEAD` を Opus が読む |

## 6. 戻し方

- この便の PR を revert して本番に出す。次の移行の終わりの作り直しで 2 列はまた伏せる（分類表は毎回空にして入れ直すため）。表の形は変えていないので、戻しのファイルは要らない。
- revert の PR も `migrations/` を変えるので危険 PR で、GO #番号が要る。
- 戻した後、§4 の V2・V3（2 つとも mask）を同じやり方で確かめる。

## 7. 実装を頼む手順（Opus）

（１）この段取り表の審査（クラウド）→ 書類の PR を合流。
（２）クラウドの Sonnet に §0〜§3 を渡して頼む（preflight → `bash scripts/new-worktree.sh release/ai-ops-stage4-bin3-allow` → 書く → 試験 → push して止まる）。頼む文は送る前に `scripts/card-lint.sh` で違反 0 にする。報告の形: ①preflight ②`git diff --stat origin/main...HEAD` ③試験の生出力 ④HEAD の sha と push の結果。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い>。
（３）§4 の V1 を読む（反映の前の基準値）。
（４）Opus が PR を作り（Draft）、審査役 APPROVE・CI 緑・GO 記録（POの委任に基づくClaude Opus発行・GO #番号）→ 合流 → 本番反映 → §4 の V2〜V5 → 設計 §13 に結果を書く。
（５）次の本番の変更（便4）は、この便の本番反映から 24 時間あける（C6）。

## 8. 外部・過去事例

- 過去事例（同じリポジトリ）: 分類を変えて allow にした前例は `docs/handoff/event-color/card-bin1.md`（color_key を allow・理由は値の決まり）。この便は値の決まり（CHECK）ではなく「値の出どころが自分たちの規則」を理由にする点が違う。それは PO 決定 D3 の理由そのもの（設計 §2 :63）。
- 外部事例: 使わない。この便は分類の行を 2 つ変えるだけで、成否は §4 の本番の確かめで直接見られるため。

## 9. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

- 判定: APPROVE（段取り表として）。クラウドの設計審査はこれから。
- 根拠:
  - 変える所が 2 行×2 ファイル・試験 1 つ・指示書 1 行で、どれも行番号を確かめた（§0）。
  - ファイルは記録の対象の外で、毎回の移行の終わりに流れるので、記録の食い違いで止まらない（§0）。同じファイルを変えた前例が 3 回、本番に出ている。
  - 本番の今の値（16 種類・4 種類）に人の名前・お客様の文が無いことを読み取りの鍵の道で数えた（§0）。
  - 戻しは revert だけで済む（§6）。
- 残る点:
  - 見張りの口の鍵を持つ人は、規則に無い名前も入れられる。鍵が漏れたときの話で、この便の範囲の外（理由の文に「口は鍵が要る」と書いた）。
  - 本番の確かめに無制限の鍵を使う（§4）。読み取りの鍵の道に `ai_cloud_meta` を足すのは別の話で、この便ではしない。

## 維持の仕組み

- 守り手: 新しい試験が CI の必須の backend 試験で毎回走る。分類表は毎回空にして入れ直すので、正本のファイルの行がそのまま効く。
- 担当: ADR-1012 のテーマとして Opus が持つ。
- 見直し: 新しい見張りの規則を足すときは、名前と強さに人の名前やお客様の文を入れない（今の規則はすべて英字の名前と 3 つの強さ）。
