# recon: deploy.yml が .env に書く secrets の `$` 展開の横展開（件1）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:5-9（#4481 件1）／docs/handoff/smtp-password-literal/design.md:30「他 secrets への横展開は別便とする」
> 基準: origin/main 88391573c。生出力: /tmp/CC報告ファイル/kenn1/recon/・/tmp/CC報告ファイル/kenn1/recon2/

## 既存 ADR
- `git grep -il "secrets\|\.env\|SMTP_PASSWORD" docs/adr/` で18件（kenn1/recon/adr_files.txt）。
- docs/adr/ADR-075-github-secrets-only-policy.md:24（本番は GitHub Secrets → VPS .env）、:64（deploy.yml で Secret を展開）。
- docs/adr/ADR-025_meta_integration_operational_hardening.md:17-21・:35（secrets を更新したら sed で消してから追記）。
- 引用符と `$` の扱いを決めた ADR は無い。docs/adr/FEATURE-INDEX.md に .env の書き方の項目も無い。

## 事実
1. 書き出し: .github/workflows/deploy.yml:276-313 の `sed -i.bak -e '/^KEY=/d' …` で36キー（35＋COMPOSE_FILE）の行を消す。:314 で `.env.bak` を消す。:323-360 の `cat >> .env <<'ENV_EOF'`（区切り語に引用符があるので shell 展開なし）で書き足す。:324-358 の35行のうち34行は `KEY=${{ secrets.X }}`（引用符なし）。:351 の SMTP_PASSWORD だけ `'…'`（#4461）。:359 の COMPOSE_FILE は固定値（kenn1/recon/env_lines.tsv）。
2. 書き出し（heredoc 以外）: :538-539 `echo "ADMIN_DATABASE_URL=${ADMIN_DATABASE_URL}" >> .env`（引用符なし・値は secrets.ADMIN_DATABASE_URL のまま、:547）。DATABASE_URL（:386・:520・:687）は urllib.parse.quote 済みなので `$` は `%24` になる。
3. 本番の今の値（2026-10-17 23:20 JST の実測、値は出さず長さと印だけ。/tmp/CC報告ファイル/secrets_dollar/prod_scan.txt）: .env は78行・69キー。`$` を含むのは SMTP_PASSWORD だけ。deploy.yml が書く36キーの値に `'`・`"`・空白を含むものは0。つまり **今、`$` で欠けている secrets は無い**。危険は、将来 secret を作り直したときに `$` や空白が入る場合。
4. 読み手（kenn1/recon2/readers.tsv）:
   - (a) docker compose の変数展開: docker-compose.yml:67-141・186・220-265・311・362・367 の `${KEY:-}`。`env_file:` は使わない。
   - (b) bash の source: scripts/blue-green-cutover.sh:35-38、scripts/run_all_migrations.sh:31-34、scripts/backup_to_s3.sh:49-52、scripts/backup_tenant_before_drop.sh:34-37。
   - (c) 行を grep|cut で切り出す（36キーのうち）: **deploy.yml:726 の ADMIN_NOTIFICATION_DISCORD_WEBHOOK の1か所だけ**（ロールバック通知の宛先。ROLLBACK_DISCORD_WEBHOOK が空のときの予備）。
   - (f) `--env-file`: 使わない（blue-green-cutover.sh:81 のコメント、#4486）。backend は source 済みの環境から `--env NAME` で受け取る（:84）。
   - backend/app には引用符を外す処理も load_dotenv も無い。値は compose か source が外した後のものが届く。
5. 読み手ごとの解釈:
   - docker compose（公式 https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/ 、2026-10-18 に WebFetch で確認。Context7 は "Monthly quota exceeded" で使えず）: "Unquoted and double-quoted (`"`) values have interpolation applied." "Single-quoted (`'`) values are used literally."
   - bash の source: 単一引用符の中は文字どおり。引用符なしでは `$` を展開する。空白で値が切れる。
   - したがって **単一引用符にすると、(a)(b) は今と同じ値（今の値には `'` も `$` も空白も無いため。ただし SMTP_PASSWORD は既に引用符付き）。将来 `$`・空白・`#` が入っても欠けない。** 壊れるのは値に `'` か改行が入ったときだけ。
6. 過去の害: S3 バックアップは 10/16・10/17 03:30 に「.env: line 931: s: unbound variable」で止まった。原因は、SMTP_PASSWORD の引用符なしの `$` を source が展開したこと（docs/handoff/bg-cutover-env-by-name/recon.md 事実8、prod_scan.txt で当時の931行目付近が SMTP_* の並び）。同じ形の事故は、ほかの34キーでも、secret に `$` が入った時点で起きる。
7. deploy.yml 以外に本番 .env を書く経路は無い（scripts/test_rollback_simulation.sh は模擬 .env、kenn1/recon/env_writers_other.txt）。
8. 前例: 本番での照合手順は docs/handoff/bg-cutover-env-by-name/design.md の K1・K3（値を出さず長さを照合する）。結果は /tmp/CC報告ファイル/bg_env/k1_after.txt（69/69 一致）。

## 未確認
- GOOGLE_CALENDAR_* は docker-compose*.yml に無い。backend には source の経路で渡る（事実4(f)）。compose のサービスがこの3キーを使っていないことは、git grep で0件を確かめた範囲まで。
