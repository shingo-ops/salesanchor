# recon: SMTP_PASSWORD を .env へ単一引用符で書き出す

## 事実（Opus確認済み）
- 本番 /home/ubuntu/salesanchor/.env の SMTP_PASSWORD は引用符なし31文字で途中に `$` を含む。
- docker compose は引用符なし値の `$xxx` を変数展開するため、コンテナには29文字で渡り、deploy 時に "variable is not set" 警告が出る。
- 値に単一引用符・二重引用符は含まれない（本番で文字種確認済み）。

## 該当箇所（git grep -n "SMTP_PASSWORD" で確認）
- /Users/tanizawashingo/worktrees/salesanchor/release-smtp-password-literal/.github/workflows/deploy.yml:303 `-e '/^SMTP_PASSWORD=/d' \`（書き出し前の既存行削除 sed）
- /Users/tanizawashingo/worktrees/salesanchor/release-smtp-password-literal/.github/workflows/deploy.yml:348 `SMTP_PASSWORD=${{ secrets.SMTP_PASSWORD }}`（`cat >> .env <<'ENV_EOF'` 内の書き出し行。変更対象）
- /Users/tanizawashingo/worktrees/salesanchor/release-smtp-password-literal/docker-compose.yml:130 `- SMTP_PASSWORD=${SMTP_PASSWORD:-}`
- /Users/tanizawashingo/worktrees/salesanchor/release-smtp-password-literal/docker-compose.yml:259 `- SMTP_PASSWORD=${SMTP_PASSWORD:-}`
- /Users/tanizawashingo/worktrees/salesanchor/release-smtp-password-literal/backend/app/services/mail_config.py:30 `_env("SMTP_PASSWORD")` で読む（コンテナ環境変数）

## 公式仕様
- docker compose: "Single-quoted (') values are used literally."
  https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/

## ローカル再現（生出力 /tmp/CC報告ファイル/smtp_fix/verify.txt）
- `X='ab$scd'` は `ab$$scd`（リテラル保持）、`Y=ab$scd` は `ab`（展開され切り詰め）＋ "scd variable is not set" 警告。
