# ADR-1024 便4: K 試験の結果（2026-10-17、便3b 完了 16:00 JST の後）

基準は [design.md §2](design.md)。証跡の置き場は `/tmp/CC報告ファイル/readonly-db-path/`（以下 bin4/ = `bin4/`、bin3b/ = `bin3b/`）。bin3b/ktest/ は便3b 直後（07:00Z）に Opus が流した試験。

| # | 基準 | 方法 | 結果 | 証跡 |
|---|---|---|---|---|
| K1 | 許可なしで本番 DB を SELECT できる | 担当 Sonnet が reader 鍵で `SELECT count(*) FROM ai_ro.public__users` を実行 | ○ フックに止められず。初回は 07:05:52Z にデプロイ中で 42P01（UndefinedTable）、再実行（07:12:30Z）で count=13 | bin4/k1.err, k1.rc, k1-retry.out, k1-retry.err, deploy-39012243576.log |
| K2 | 書き込みが失敗する | INSERT を台本で試験。権限は public.users の直読みで試験 | ○ INSERT は台本で拒否（`result=rejected`）。public.users の直読みは 42501。pg_authid・nextval も 42501 | bin4/K4ins.err, K6b.err, bin3b/ktest/t2.err, t3.err, t4.err |
| K3 | サーバー側の記録（Loki） | Grafana の Loki datasource の query_range を読み取りで照会（bin5） | ○ 便K3-2（2026-10-17 11:28Z、#4467 反映後）: G1 5 本の sha が {job="sshd"} に各 1 行・G2 結果値 0 件・G3 基準値と同一・rc=5 は 0 件。改訂前の × は台本 AUDIT が 23 種中 1 種のみ | bin9/prod/k3-2-result.md, g1.txt, g2.txt, g3.txt |
| K4 | 既存の authorized_keys 行が不変 | 先頭 5 行を元バックアップと比較 | ○ 先頭5行が元バックアップと一致=はい | bin3b/fix-commit-20261017-155948.out |
| K5 | 調査メモを書いてもフックに止められない | ssh/psql/`</INSERT` を本文に含む md を Write | ○ 止まらない | bin4/k5-test.md |
| K6 | 秘密列が読めない | ai_ro の秘密列数。`password_argon2_hash` の直読み | ○ 秘密列 0 本。直読みは 42501 | bin4/K6.err, ktest.md, bin3b/ktest/t5.out, t5.err |
| K7 | BYPASSRLS・pg_read_all_data なし | pg_roles と pg_auth_members | ○ rolbypassrls=False、rolsuper=False。pg_read_all_data・pg_write_all_data の所属は 0 | bin4/K7a.out, K7b.out |
| K8 | 全テナントのビューが読める | ai_ro のスキーマ別ビュー数と、元の表の件数照合（bin5） | ○ ai_ro ビュー public 109、tenant_001 99、tenant_003 69、tenant_004 91、tenant_005 69、tenant_006 69（計 506）。ビューの無い表は 0。ai_ro.public__users count=13 は pg_stat n_live_tup=13 と一致。tenant_001.products は 0 件で比較力は弱い。ベース表の直読み（tenant_001.products 等）は 42501 | bin5/k8-a.out, k8-b.out, k8-c.out, k8-d1〜d3, bin4/K8a〜K8f.err, K8pub.out, ktest.md, bin3b/ktest/t8.out |
| K9 | 新しい表は fail-closed | pg_default_acl、has_table_privilege、ロール属性（bin5） | ○ pg_default_acl に ai_reader を含む行は 0。ai_reader は rolsuper=False、rolbypassrls=False。通常表 506 と同スキーマ内ビュー 15 の計 521 は SELECT 権限 0。ai_ro のビュー 506/506 は SELECT 可。新しい表を実際に作る試験は書き込みになるため未実施 | bin5/k9-a〜k9-i |
| K10 | pg_authid が読めない | `has_table_privilege('ai_reader','pg_authid','SELECT')` | ○ False | bin4/K10.out |
| K11 | 設定迂回は境界でない証明 | set_config を台本で送る。pg_settings と has_parameter_privilege で補助確認（bin5） | △ 台本が set_config を rejected にする（rc=2、DB に届かない）。DB の 42501 は直接観測できず。補助として、ai_reader は rolsuper=False で has_parameter_privilege('ai_reader','log_statement','SET')=False、rolconfig に log_statement=all、default_transaction_read_only=on、statement_timeout=60s | bin5/k11-a〜k11-e |
| K12 | SET が拒否される | `SET log_statement='none'` を送る | ○ 台本で拒否（`result=rejected`）。DB 側の拒否は未測 | bin4/K12.err |
| K13 | 環境変数は AI_READER_DATABASE_URL のみ | origin/main の docker-compose.ai-reader.yml の定義を読む（bin5。コンテナ内の実測ではない） | ○ environment は :15-16 の AI_READER_DATABASE_URL のみ。env_file は無い。read_only、cap_drop ALL、no-new-privileges、mem_limit 256m、network backnet のみ | bin5/results.md |
| K14 | 固定コマンド以外は動かない | 引数付き実行、-L 転送、-tt を reader 鍵で試す（bin5） | ○ 引数 `id` は実行されず台本が rejected（rc=2）。-L は接続のたびに administratively prohibited。-tt は PTY allocation request failed（rc=255）。`sshd -T` は sudo のパスワードが要り取れないため、設定ファイル（Include 先は空・Match 節なし）と公式の既定値（sshd_config(5)）で照合した（2026-10-17、PO 承認「y」）。permituserenvironment=no・permituserrc は鍵の restrict で停止・forcecommand=none・acceptenv=LANG LC_* で、いずれも ○ | bin5/k14-a, k14-b3.err, k14-c, bin8/k14-result.md |
| K15 | 鍵に期限と制限 | authorized_keys の reader 行 | ○ restrict と expiry-time 20270115 が入っている | bin3b/commit-20261017-155439.out, bin3b/check.out |
| K16 | 台本・compose 定義の変更は GO 記録なしでは止まる（ADR-1024 改訂） | process-artifacts gate の模擬（設計 K16 改訂の G1・G2） | ○ GO 記録なしは rc=1、委任 GO 記録ありは rc=0（変更前は免除宣言だけで rc=0 だった） | この PR の本文に貼った実行結果 |
| K17 | フック免除が完全一致のみ | 免除は入れていない。現在のフックは reader の呼び方に当たらない（`~/.claude/scripts/agent-danger-hook.sh:99-101,113`。リポジトリ外） | 免除そのものが不要 | bin4/recon-hooks.md, k1.rc |
| K18 | 負荷の上限 | 行数、60 秒、同時 3 本、大きな結果 | ○ 5000 行で打ち切り。60 秒で 57014（QueryCanceled、60525 ms）。同時 3 本は 1 本が OperationalError、2 本は rc=0。150 万行の結果でも 200 行で打ち切り、落ちない | bin4/K18a.err, K18b.err, K18c1.err, K18c1.rc, K18c2.rc, K18c3.rc, bin3b/ktest/t10.out, t10.err |

K14 の `sshd -T` は設定ファイルと公式既定値の照合で代替した（2026-10-17、PO 承認）。bin5 で K3・K8・K9・K11・K13・K14 を測定。K3 は ×（便K3-2 で ○ に更新）、K11 は △。
