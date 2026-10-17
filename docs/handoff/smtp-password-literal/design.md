# design: SMTP_PASSWORD を .env へ単一引用符で書き出す

参照: recon.md（同ディレクトリ）, 対象ADR: なし（ADR-136 危険パス手順）

## 目的
deploy.yml が .env に書く SMTP_PASSWORD の `$` が docker compose に変数展開されて値が欠ける（31文字→29文字）のを止め、正しい値をコンテナへ渡す。

## 変更前後
- 対象: .github/workflows/deploy.yml:348 の1行のみ
- 前: `SMTP_PASSWORD=${{ secrets.SMTP_PASSWORD }}`
- 後: `SMTP_PASSWORD='${{ secrets.SMTP_PASSWORD }}'`
- 他の行は触らない。

## 影響範囲
- 変更は SMTP_PASSWORD の1行のみ。読む側は docker-compose.yml:130, :259 と backend/app/services/mail_config.py:30（変更なし）。
- 値に単一引用符を含む場合は壊れるが、本番値は含まない（確認済み）。
- migrations なし・相乗りなし。

## 受入条件
|基準|検証方法|
|---|---|
|K1 次回deployログに SMTP_PASSWORD 由来の "variable is not set" 警告が0件|deployログを grep し該当警告の件数を数える|
|K2 本番 `docker compose config` 上の SMTP_PASSWORD 長さ=31（値は出さず長さのみ）|本番で config 出力から長さのみ算出|
|K3 deploy success|GitHub Actions の deploy ジョブが success|

## 戻し方
当該1行を revert（`git revert` で1行が元に戻る）。

## 維持の仕組み
他の secrets に `$` が入っても同じ形（単一引用符）で守れる。ただし今回は SMTP_PASSWORD の1行のみ。他 secrets への横展開は別便とする。

守り手: deploy.yml を変える PR の審査役（Opus）。次回 deploy ログの "variable is not set" 警告0件で確認する。

## 外部・過去事例の参照と我々への応用
- docker compose 公式: "Single-quoted (') values are used literally."（出典 https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/ ）
- 応用: .env 書き出し時に単一引用符で囲めば `$` がリテラル扱いとなる。ローカル検証で X='ab$scd' が保持され、引用符なしの Y は切り詰められることを確認（/tmp/CC報告ファイル/smtp_fix/verify.txt）。
