# recon: 本番 backend の環境変数が .env と食い違う（2026-10-17）

基準: origin/main 869b29869 時点。本番の実測は 2026-10-17 23:20〜23:40 JST（値は出さず、長さと印だけを記録）。

## 既存 ADR・設計の検索
- `git grep -i "env-file" docs/adr/` は該当なし。docs/adr/FEATURE-INDEX.md にも .env の読み方の項目はない。
- 関連する設計: docs/handoff/smtp-password-literal/design.md（#4461）。docs/handoff/zero-downtime-deploy/design.md（blue-green の元設計）。
- ADR-130（docs/adr/ADR-130-nginx-reload-policy.md:11）と ADR-137（docs/adr/ADR-137-nginx-config-deploy-reliability.md:87）は blue-green に触れるが、環境変数の渡し方は決めていない。

## 事実
1. .env の書き出しは /Users/tanizawashingo/salesanchor/.github/workflows/deploy.yml:323-360 の heredoc `<<'ENV_EOF'` で行う。区切り語に引用符が付いているので、書き出すときに shell の展開は起きない。単一引用符で囲む行は SMTP_PASSWORD（:351、#4461）だけ。
2. 本番 .env（78行・キー69）で、`$` を含むのは SMTP_PASSWORD だけ。単一引用符で囲む行は1つ（SMTP_PASSWORD）、二重引用符は1つ（REVIEW_MAIL_DISCORD_MENTION。deploy.yml は書いていない）。値の中に引用符・空白を含むものは0。重複キーも0（/tmp/CC報告ファイル/secrets_dollar/prod_scan.txt）。
3. compose で起動するサービス（12個）では、41組のすべてで .env の値とコンテナ内の値の長さが一致した（compare.txt）。compose config の "variable is not set" 警告は0。
4. backend だけは compose ではなく、/Users/tanizawashingo/salesanchor/scripts/blue-green-cutover.sh:56-68 の `docker run ... --env-file "${REPO_DIR}/.env"` で起動している。呼び出し元は deploy.yml:420 と :530。
5. 動いている backend（astro-webapp-backend-1、作成 2026-10-17T14:21:57Z）で、.env と長さが違うキーは69個中2個（backend_env_len.txt、live_backend.txt）。
   - SMTP_PASSWORD: .env の中身は31、backend では33で、先頭が `'`。
   - REVIEW_MAIL_DISCORD_MENTION: .env の中身は22、backend では24。
   原因: `docker run --env-file` は引用符を外さず、値の一部として渡す。
6. backend がメールを送る場所は4つ（/Users/tanizawashingo/salesanchor/backend/app/services/auth_mail.py:75、/Users/tanizawashingo/salesanchor/backend/app/routers/contact.py:40、/Users/tanizawashingo/salesanchor/backend/app/services/email_sender.py:44、/Users/tanizawashingo/salesanchor/backend/app/services/po_mailer.py:66）。/Users/tanizawashingo/salesanchor/backend/app/services/mail_config.py:24-25 は前後の空白を落とすだけで、引用符は外さない。
7. #4461 の前は、SMTP_PASSWORD に引用符が付いていなかった。そのため backend（--env-file・展開なし）は31文字で正しく、compose 側と S3 バックアップ側（source）が欠けていた。#4461 の後は逆になった。compose 側と source 側は正しくなり、backend が33文字になった。
8. S3 バックアップ（/Users/tanizawashingo/salesanchor/scripts/backup_to_s3.sh:49-52、`set -euo pipefail` の下で .env を source）は、10/16 と 10/17 の 03:30 に「.env: line 931: s: unbound variable」で止まっていた。最後に成功したのは 10/15（s3log_tail.txt）。今の .env は同じ読み方で SOURCE_OK（source_test.txt）。
9. 本番の docker で試した（env_pass_test.txt）。shell で `set -a; source` したあと `docker run --env NAME`（値を書かず名前だけ）で渡すと、次のようになった。
   - `A='ab$cd'` は5文字、先頭は `a`。
   - `B="<@123>"` は `<@123>`。
   - 空の値も空のまま渡った。
   - 後ろに書いた `--env C=override` が優先された。

## 未観測
- 10/17 19:30 頃から 23:40 までに、backend がメールの送信に失敗したかどうか。今の backend のログ（14:21Z 以後）には SMTP のエラーが0件。それより前のコンテナのログは確認していない。
