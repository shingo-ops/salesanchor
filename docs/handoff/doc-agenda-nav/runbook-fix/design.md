# design: サーバー・運用の手順書15本の事実食い違いを直す

- テーマ: doc-agenda-nav（目次づくりの中で一緒に直す。PO「2」2026-10-23 で承認。docs のみ）
- 調査: [recon.md](./recon.md)（§1 食い違い 15文書・39行、§2 P1〜P10）
- 基準: origin/main 2a5512eec25c1fc5feda85907e47ad5976588885
- 状態: 設計案作成済み・設計審査済み（§8）・実装未着手

## 1. 目的（KGI）

手順書を読んだ人や AI が、今は無い仕組み（systemd・Slack・customers 表・bcrypt のパスワード等）を前提に作業しない状態にする。

| 基準 | 検証方法 |
|---|---|
| recon §1 の39行すべてが「実物と一致」または「本文に『まだ確かめていない』の注記あり」 | round3 と同じ照合表（文書・行・主張・実物・判定）を修正後のファイルで作り直し、不一致 0 行 |
| 誤判定だった2行（D-06 の POST /api/v1/admin/tenants、GET /api/v1/dashboard の道）は道を変えていない | 照合表で道の文字列が修正前と同じ |
| 変更ファイルは15本＋本フォルダの handoff 文書＋台帳だけ | `git diff --name-only origin/main...HEAD` |
| 危険な操作のコマンド文字列を新たに書き足していない | diff の追加行に強制リセット・DROP・rm -rf・force push が 0 件 |

## 2. 決まり（全15本に共通）

1. 書くのは recon の「パス:行」で確かめた事実だけ。
2. サーバーの中でしか分からないこと（実際の cron の出力先、Grafana 画面の中の設定、資格ファイルの置き方、チャンネル名）は書き換えない。該当する行の直後に「（まだ確かめていない: 〜）」を書き添える。
3. 同じ情報を2か所に書かない（SSOT）。一覧・ステップ・secrets の名前のように実物が正本で変わりやすいものは、文書に写さず「正本: パス」で案内する。
4. 文書の全面書き直しはしない。食い違う行とそのすぐ前後だけを直す。体裁・見出し・ほかの行は触らない。
5. 過去の時点の記録として価値がある文書は、本文を変えず冒頭に注記する。
6. 見張り（フック）に止められたら言い換えて再試行しない。その文書で止まり、報告する。

## 3. 文書ごとの変更（変更前 → 変更後・根拠）

行番号は cc000952 時点。実装時に行の文言で位置を確かめる。文言が見つからない場合は、その文書の作業を止める。

### 3-1 .github/workflows/README.md（6行）
| 行 | 変更前 | 変更後 | 根拠 |
|---|---|---|---|
| 1 付近 | 3本だけを扱う（範囲の注記が無い） | 冒頭に「この文書は Discord 通知2本と deploy の3本だけを説明する。全ワークフローは `.github/workflows/` の実物を見る」と注記 | recon §1 #12（76項目） |
| 7 | 通知タイトルの表 | 表の文言を写すのをやめ、「文言の正本: discord-pr-notify.yml（作成 :33／再オープン :68／レビュー :131／マージ :170／未マージで閉じた :205）」に置き換える | recon P8 |
| 50 | failure / timed_out | failure / timed_out / action_required（正本 discord-ci-notify.yml:53） | recon P8 |
| 59 | DISCORD_WEBHOOK_PR を共用 | DISCORD_WEBHOOK_CI（discord-ci-notify.yml:100） | recon P8 |
| 75 | 接続→pull→build付き起動 | 手順を写さず「段階の正本: deploy.yml の『Deploy to VPS』ステップ（:230〜）。取り込み・.env 追記・blue-green 切替・compose 起動をこの順で行う」 | recon P8 |
| 86 | Secrets は3つ | 「deploy.yml は約40種の secrets を参照する。名前の正本は deploy.yml の `secrets.` 参照」 | recon P8 |

### 3-2 docs/B-04_incident_response_playbook.md（2行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 3 | 対象を app.salesanchor.jp / api.salesanchor.jp に。jarvis-claude.uk は「全パスを app.salesanchor.jp へ転送するだけの旧住所」と注記 | nginx/nginx.conf:37-38、CLAUDE.md の本番 URL |
| 30 | DB のユーザー名・DB 名を jarvis / jarvis_db に（コマンドの形は変えず、2つの名前だけ置換） | deploy.yml:514,815 |

### 3-3 docs/B-13_mgmt-vps-governance.md（3行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 6 | 本文は変えず「（ADR-080 のステータスは Proposed のまま。docs/adr/README.md:90）」を添える | recon P2 |
| 211 | 存在しない3つの名前を消し、「期待するアラート名の正本: monitoring/prometheus/alert_rules.yml（例 ServiceDown・BackendHighErrorRate）。PostgresDown / HighErrorRate / High502Rate は今の規則に無い」 | recon P5 |
| 225 | 書き換えない。「（まだ確かめていない: Grafana 画面の中の設定。リポジトリの monitoring 配下には discord-ops は無く、alertmanager の送り先は discord-server-alerts / discord-recovery-info / ops-api）」を添える | recon P5 |

### 3-4 docs/D-06_firebase_credentials_setup.md（2行を直す・2行は触らない）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 152 | `/api/v1/customers` を `/api/v1/dashboard`（GET・実在）に替える | recon P7（customers は ADR-089 で廃止） |
| 152・166・181 の住所 | jarvis-claude.uk を api.salesanchor.jp に替える。**条件**: nginx/nginx.conf の api.salesanchor.jp の 443 ブロックに `/api/` を backend へ渡す location があることを実装時に確かめる。無ければ住所は替えず止まる | recon P1（jarvis は 301 転送のみ。POST は転送で崩れる） |
| 166・181 の道 | 変えない（実物と一致。round3 の誤判定） | recon P7 |
| 210 | 「GitHub Secretsで管理」を「GitHub Secrets には無い（deploy.yml に該当 0 件）。compose は compose と同じフォルダの firebase-credentials.json を読み取り専用で読む（docker-compose.yml:143,267）。git には入っていない。（まだ確かめていない: サーバーへの置き方）」 | recon P4 |

### 3-5 docs/DATA_CLASSIFICATION.md（3行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 16 | customers テーブル → companies テーブル（ADR-089） | recon P2 |
| 24 | 「パスワード: 今の既定（Firebase）では DB に持たない。自社ログイン（AUTH_PROVIDER=self）のときだけ users.password_argon2_hash に Argon2id で保存。bcrypt（12ラウンド）は bot の API キー（bots.py:58）だけ」 | recon P3 |
| 49 | 24行目と同じ事実に合わせる（1文） | recon P3 |

### 3-6 docs/INCIDENT_RESPONSE.md（2行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 20 | Slack等 → Discord。「（まだ確かめていない: 開設するチャンネル名）」を添える | recon §1・alertmanager の送り先 |
| 151 | Slack #jarvis-alerts → 「Discord（alertmanager の送り先 discord-server-alerts ほか。monitoring/alertmanager/alertmanager.yml）」 | recon P5 |

### 3-7 docs/ops/self-hosted-runner-credential-trap.md（1行）
冒頭に「過去時点の記録: ここに出てくる claude-pipeline.yml は今の .github/workflows に無い」と注記。本文は変えない。

### 3-8 docs/runbooks/discord-gateway-operations.md（7行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 13 | テナント別トークン → 共通の DISCORD_BOT_TOKEN 1本（docker-compose.yml:362）。ADR-146 は名前だけ出し「本文はリポジトリに無い」と添える | recon P2 |
| 24・37・38・62 | systemd の節を「docker compose のサービス discord-gateway（docker-compose.yml:350。restart: unless-stopped）。デプロイ時に deploy.yml:453 が起動する。環境変数は .env から入る」に置き換える。unit ファイル・WorkingDirectory・EnvironmentFile・daemon-reload の記述は消す | recon §1・P8 |
| 86 | 確認は `docker compose logs discord-gateway`、復旧は `docker compose restart discord-gateway` | docker-compose.yml:350 |
| 93 | inventory_parser_llm.py → 「GEMINI_API_KEY を読むのは backend と celery-worker（docker-compose.yml:95,230）。discord-gateway には渡していない」。**条件**: 実装時に docker-compose.yml の discord-gateway ブロック（:350〜:404）に GEMINI_API_KEY が無いことを確かめる。あれば止まる | recon P10 |

### 3-9 docs/runbooks/review-tenant-operations.md（2行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 1 | 題名は変えず直下に「ADR-028 は Superseded（scripts/setup_review_tenant.py と docs/META_APP_REVIEW_PRE_RECORDING_CHECKLIST.md に置き換え）」 | recon P2 |
| 121 | 「password_hash 列は廃止済み（migrations/20260612_150000_drop_password_hash.sql）。ADR-138 は ADR-1013 に置き換えられた」 | recon P2・P3 |

### 3-10 docs/runbooks/tenant-deletion-operations.md（1行）
110: 「GitHub PR コメントまたは Slack」→「GitHub PR（PR 本文の GO 記録とコメント。ADR-136）」

### 3-11 docs/SECURITY_ENHANCEMENT_ROADMAP.md（2行）
冒頭に「過去時点の計画書。対象の jarvis-claude.uk は今は app.salesanchor.jp へ転送するだけの旧住所」と注記。40行は直下に「（今の実物: secret-scan.yml と security-scan.yml の中身は実装時に1行ずつ確かめて書く。3種すべての組込はまだ確かめていない）」— 実装時に secret-scan.yml で gitleaks / trivy / semgrep の各語の行を確かめ、あった語だけ「secret-scan.yml:行」で書く。

### 3-12 docs/SECURITY.md（1行）
60: 3-5 の24行目と同じ事実に置き換える。

### 3-13 docs/TEST_ADMIN_PASSWORD_CHANGE_PROCEDURE.md（1行）
97: https://jarvis-claude.uk → https://app.salesanchor.jp（jarvis は全パスを転送するだけ。nginx/nginx.conf:37-38）

### 3-14 docs/ZERO_TRUST_POLICY.md（2行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 47 | read_only は redis だけ（docker-compose.yml:473） | recon P6 |
| 48 | healthcheck は 11 サービスのうち 9（無いのは certbot・gha-exporter） | recon P6 |

### 3-15 scripts/aws-setup/README.md（2行）
| 行 | 変更後 | 根拠 |
|---|---|---|
| 169 | 行は変えない。直後に「（まだ確かめていない: 実際の cron の出力先。スクリプト側のコメントは /var/log/s3_backup.log。backup_to_s3.sh:14、setup-s3-backup.sh:129）」 | recon P9 |
| 168 付近 | 3点を足す: 毎月1日に monthly-archives/ へ Glacier で永久保存（backup_to_s3.sh:138-154、s3-lifecycle.json:14-18）／成功時刻を backup_s3.prom に書き BackupS3Stale が見張る（:159-176）／失敗時は DISCORD_WEBHOOK_OPS へ通知（:56-73） | recon P9 |

### 3-16 追補（実装中に見つかった同じ種類の食い違い。2026-10-23 Opus 判断で範囲に含める）
39行だけ直すと、同じ文書の中に古い記述が残り、文書の中で話が食い違う。PO が承認した「15本を直す」の範囲内なので、同じ事実で揃える。
| 文書 | 行（実装時の実測） | 変更後 |
|---|---|---|
| B-04 | 39・44・56・73 の myapp_user / myapp_db | 30行目と同じく jarvis / jarvis_db（名前だけ置換） |
| D-06 | 172・177 の jarvis-claude.uk と customers | 3-4 と同じ（住所は api.salesanchor.jp、customers は /api/v1/dashboard） |
| D-06 | 155 付近の期待する応答「200 [] (空配列)」 | backend/app/routers/dashboard.py の応答の形を確かめ、空配列でなければ「200 が返る」だけにする |
| discord-gateway | 15〜22 のテナント別トークンの例 | 共通の DISCORD_BOT_TOKEN 1本の説明に置き換える（値は書かない） |
| discord-gateway | 119・129 の systemctl / journalctl | 3-8 の86行目と同じく docker compose の restart / logs |
| INCIDENT_RESPONSE | 見出し「Slackチャンネル（要設定）」 | 「Discord チャンネル（まだ確かめていない: チャンネル名）」 |

追補2（実装の報告を受けて Opus 判断）:
- D-06:172 は顧客を作る POST の例だった。上の表で「/api/v1/dashboard に替える」としたのは設計の誤り（GET 専用の道に POST する手順になる）。道は替えず、直下に「（この道は廃止済み。ADR-089 で customers は companies に統合）」を添える。
- discord-gateway:110 の `DISCORD_BOT_TOKEN_{TENANT_ID}` は共通の DISCORD_BOT_TOKEN にする。123 行付近の `/etc/sales-anchor/...` を読む記述は「.env から入る（deploy.yml）」にする。
- B-04:95 の health の住所は api.salesanchor.jp にする（/api/ は nginx/nginx.conf:498 で backend へ渡る）。

### 3-17 recon の誤りの訂正
- recon §1 SECURITY_ENHANCEMENT_ROADMAP #3 の「trivy・semgrep の文字列は secret-scan.yml にある」は誤り。実測: gitleaks のみ secret-scan.yml:15,24。trivy・semgrep は .github/workflows 全体で 0 件。
- 3-1 の「約40種」は実測 47 種（重複なし）。

### 3-17b 審査（model opus・1回目 REQUEST_CHANGES）を受けた訂正
- F1: パスワードの記述（DATA_CLASSIFICATION:24・:49、SECURITY:60）は次に揃える。DB に置くパスワードは Argon2id（backend/app/auth/passwords.py）。列は users.password_argon2_hash（自社ログインとパスワード再設定。再設定は AUTH_PROVIDER に関係なく動く: backend/app/routers/auth.py:350,468）と viewer_accounts.password_argon2_hash（閲覧ページ: migrations/20261016_150000_add_viewer_accounts.sql:12）。ログイン判定の既定は Firebase（self_tokens.py:20）。bcrypt（12ラウンド）は bot の API キー（bots.py:58）だけ。本番に行があるかはまだ確かめていない。
- F2: jarvis-claude.uk の 301 転送の根拠は nginx/nginx.conf:44-46（3-2・3-13 の :37-38 は誤り）。
- F3: deploy.yml の secrets は 45 種（3-17 の 47 は `secrets.X` のコメントと `.env.secrets.new` を数えた誤り）。
- F4: INCIDENT_RESPONSE:125 は人ごとの連絡先を書く表の列名で、仕組みの主張ではない。書き換えると推測になるため 3-18 の対象から外す。
- N1: D-06 の「3. 顧客一覧取得」は中身を /api/v1/dashboard にしたため、見出しを「3. ダッシュボード取得」にする。
- N3: aws-setup README の backup_to_s3.sh の行範囲を :140-158 / :161-177 に直す。

### 3-18 合格の確かめ方の追加
担当の照合表は人の判断で書いたため、機械の確認を足す: 修正後の15本に、次の古い語が「まだ確かめていない」の注記や過去記録の注記の外で残っていないことを grep で確かめる — `systemctl`・`journalctl`（discord-gateway）、`DISCORD_BOT_TOKEN_<`、`myapp_user`・`myapp_db`（B-04）、`/api/v1/customers`（D-06）、`jarvis-claude.uk`（D-06・TEST_ADMIN・B-04 の対象行）、`PostgresDown`・`High502Rate`（B-13）、`Slack`（INCIDENT_RESPONSE・tenant-deletion）、`bcrypt`（DATA_CLASSIFICATION・SECURITY の bot キー以外）。最終確認は model "opus" の審査役が独立に行う。

## 4. 触らない範囲
- 上の39行とその直前直後以外の本文、見出し、体裁
- コード・設定・workflow の yml・scripts の .sh / .json（README.md 以外）
- B-04 と INCIDENT_RESPONSE の重複（範囲外として §7 に記録のみ）
- 規則1の25本・規則2の7本

## 5. 選んだ方法と代わりの案
- 採用: 食い違う行だけを直し、変わりやすい一覧は正本へ案内。理由: 写した一覧はまた食い違う（今回の workflows README がその例）。
- 不採用: 全面書き直し（範囲が広がり確かめきれない）／文書の削除（PO は「消さない」方針で棚卸しを承認）。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 行番号のずれで別の行を直す | 文言で位置を確かめ、無ければ止まる |
| 見張りに止められた後の言い換え | 止まって報告（決まり6） |
| scripts/ 配下の README が危険な PR と判定される | PR の判定を確かめ、危険扱いなら止まって Opus へ |
| サーバー内の事実を推測で書く | 決まり2の注記のみ |

## 7. 範囲外として記録
- B-04 と INCIDENT_RESPONSE は同じ題材の文書が2本ある。どちらを正にするかは別件。
- ADR-146 は本文がリポジトリに無い（compose のコメントだけ）。

## 8. 設計審査（Architect・同一AIの自己審査）
- 判定: APPROVE
- 確認したこと: 39行すべてに変更後か注記の方針がある（3-1〜3-15 の行数合計 6+2+3+4+3+2+1+7+2+1+2+1+1+2+2=39）。根拠はすべて recon の「パス:行」。条件付きの項目（3-4 の住所、3-8 の93行、3-11 の40行）は実装時の確かめ方と止まる条件を書いた。
- 未解決: サーバーの中の事実4点（cron の出力先、Grafana の設定、資格ファイルの置き方、チャンネル名）は注記で扱い、確かめない。
- 外部事例: 不要。社内文書を実物に合わせる作業で、外部の事例が判断を変えない。

## 9. 維持の仕組み
今回は直すだけ。食い違いの再発を見張る仕組みは、目次づくり（doc-agenda-nav）の本体で扱う。
