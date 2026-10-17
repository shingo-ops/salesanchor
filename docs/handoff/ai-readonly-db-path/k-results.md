# ADR-1024 便4: K 試験の結果（2026-10-17、便3b 完了 16:00 JST の後）

基準は [design.md §2](design.md)。証跡の置き場は `/tmp/CC報告ファイル/readonly-db-path/`（以下 bin4/ = `bin4/`、bin3b/ = `bin3b/`）。bin3b/ktest/ は便3b 直後（07:00Z）に Opus が流した試験。

| # | 基準 | 方法 | 結果 | 証跡 |
|---|---|---|---|---|
| K1 | 許可なしで本番 DB を SELECT できる | 担当 Sonnet が reader 鍵で `SELECT count(*) FROM ai_ro.public__users` を実行 | ○ フックに止められず。初回は 07:05:52Z にデプロイ中で 42P01（UndefinedTable）、再実行（07:12:30Z）で count=13 | bin4/k1.err, k1.rc, k1-retry.out, k1-retry.err, deploy-39012243576.log |
| K2 | 書き込みが失敗する | INSERT を台本で試験。権限は public.users の直読みで試験 | ○ INSERT は台本で拒否（`result=rejected`）。public.users の直読みは 42501。pg_authid・nextval も 42501 | bin4/K4ins.err, K6b.err, bin3b/ktest/t2.err, t3.err, t4.err |
| K3 | サーバー側の記録（Loki） | - | 未測 | - |
| K4 | 既存の authorized_keys 行が不変 | 先頭 5 行を元バックアップと比較 | ○ 先頭5行が元バックアップと一致=はい | bin3b/fix-commit-20261017-155948.out |
| K5 | 調査メモを書いてもフックに止められない | ssh/psql/`</INSERT` を本文に含む md を Write | ○ 止まらない | bin4/k5-test.md |
| K6 | 秘密列が読めない | ai_ro の秘密列数。`password_argon2_hash` の直読み | ○ 秘密列 0 本。直読みは 42501 | bin4/K6.err, ktest.md, bin3b/ktest/t5.out, t5.err |
| K7 | BYPASSRLS・pg_read_all_data なし | pg_roles と pg_auth_members | ○ rolbypassrls=False、rolsuper=False。pg_read_all_data・pg_write_all_data の所属は 0 | bin4/K7a.out, K7b.out |
| K8 | 全テナントのビューが読める | ai_ro のスキーマ別ビュー数 | 一部。ビュー数は public 109、tenant_001 99、tenant_003 69、tenant_004 91、tenant_005 69、tenant_006 69。jarvis の値との件数照合は未実施。ベース表の直読み（tenant_001.products 等）は 42501 | bin4/K8a〜K8f.err, K8pub.out, ktest.md, bin3b/ktest/t8.out |
| K9 | 新しい表は fail-closed | - | 未測 | - |
| K10 | pg_authid が読めない | `has_table_privilege('ai_reader','pg_authid','SELECT')` | ○ False | bin4/K10.out |
| K11 | 設定迂回は境界でない証明 | - | 未測 | - |
| K12 | SET が拒否される | `SET log_statement='none'` を送る | ○ 台本で拒否（`result=rejected`）。DB 側の拒否は未測 | bin4/K12.err |
| K13 | 環境変数は AI_READER_DATABASE_URL のみ | - | 未測 | - |
| K14 | 固定コマンド以外は動かない | `sshd -T` は sudo が要るため PO が実行 | 未測 | - |
| K15 | 鍵に期限と制限 | authorized_keys の reader 行 | ○ restrict と expiry-time 20270115 が入っている | bin3b/commit-20261017-155439.out, bin3b/check.out |
| K16 | CODEOWNERS 必須 | Branch Protection の GUI 確認（PO） | 未測 | - |
| K17 | フック免除が完全一致のみ | 免除は入れていない。現在のフックは reader の呼び方に当たらない（`~/.claude/scripts/agent-danger-hook.sh:99-101,113`。リポジトリ外） | 免除そのものが不要 | bin4/recon-hooks.md, k1.rc |
| K18 | 負荷の上限 | 行数、60 秒、同時 3 本、大きな結果 | ○ 5000 行で打ち切り。60 秒で 57014（QueryCanceled、60525 ms）。同時 3 本は 1 本が OperationalError、2 本は rc=0。150 万行の結果でも 200 行で打ち切り、落ちない | bin4/K18a.err, K18b.err, K18c1.err, K18c1.rc, K18c2.rc, K18c3.rc, bin3b/ktest/t10.out, t10.err |

未測: K3、K9、K11、K13、K14、K16。K8 は件数照合が残り。
