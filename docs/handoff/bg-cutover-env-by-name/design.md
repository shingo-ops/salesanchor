# design: blue-green の backend に .env を「名前で」渡す

recon: docs/handoff/bg-cutover-env-by-name/recon.md

## 目的（KGI）
本番 backend が受け取る環境変数を、compose の各サービスと同じ値にそろえる。.env は今までどおり1か所（deploy.yml が書く）で、読み方だけを直す。
- 判定: デプロイ後、backend の全キーで .env の値の長さとコンテナ内の値の長さが一致する（69/69）。SMTP_PASSWORD は31。

## 対象と対象外
- 対象: /Users/tanizawashingo/salesanchor/scripts/blue-green-cutover.sh の1か所（:68 の `--env-file "${REPO_DIR}/.env"`）。
- 対象外: deploy.yml（#4461 の単一引用符はそのまま）、.env の中身、compose ファイル、ほかの source している4本。
- REVIEW_MAIL_DISCORD_MENTION の二重引用符も、この変更で backend 側は外れる（compose 側と同じ値になる）。.env の行そのものは変えない。

## 変更前後
変更前（:68）:
```
  --env-file "${REPO_DIR}/.env" \
```
変更後: Step 2 の `docker run` の直前に、次を追加する。
```
# .env のキーを名前だけで渡す（値は :34-39 で source 済みの環境から docker が読む）。
# --env-file は引用符を外さないため使わない（docs/handoff/bg-cutover-env-by-name/design.md）。
ENV_ARGS=()
while IFS= read -r _k; do ENV_ARGS+=(--env "$_k"); done < <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "${REPO_DIR}/.env" | tr -d '=')
```
:68 は次に変える。
```
  "${ENV_ARGS[@]}" \
```
その後ろの `--env GOOGLE_APPLICATION_CREDENTIALS=...` と `--env TCG_SCHEMA=...` はそのまま残す（後ろに書いたものが優先されることを実測済み・recon 事実9）。

- 値はコマンドラインに出ない（ps に値が残らない）。一時ファイルも作らない。
- .env が無いとき: 今の --env-file はファイルが無いと docker run が失敗して止まる。変更後もこの挙動を保つため、ENV_ARGS を作る前に `[ -f "${REPO_DIR}/.env" ] || { echo ".env not found" >&2; exit 1; }` を置く（空の環境で backend を起動させない）。

## 代替案
- A（採用）: 名前で渡す。.env を読むのは bash の source だけになり、compose と同じ解釈になる（引用符を外し、`$` は単一引用符の中では文字どおり）。
- B: 引用符を sed で外した一時ファイルを作り、--env-file に渡す。秘密の値がディスクに一時的に残る。削除が必要で、二重引用符のエスケープを自前で解釈する必要もある。不採用。
- C: #4461 を戻す。backend は直るが、compose 側と S3 バックアップが再び欠ける。不採用。

## リスクと対処
- source と compose の解釈が違う値（二重引用符の中の `\` や `$`）: 今の .env には0件（recon 事実2）。将来入ったときに気づけるよう、K1 の点検手順を受入条件に入れる。
- 名前の数が増えると引数が長くなる: 69個 × 約30字 ≈ 2KB。ARG_MAX（数MB）の範囲内。
- 失敗時: green の health に失敗すると、既存の ERR trap が green を消し、旧 backend が残る（:43-49）。無停止の切替は変わらない。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 backend の全キーの長さが .env と一致（69/69）、SMTP_PASSWORD=31、先頭が `'` でない | デプロイ後、本番で /tmp/CC報告ファイル/secrets_dollar/ と同じ点検（値は出さない） |
| K2 デプロイが success、blue-green の health 確認を通過 | gh run view のログ |
| K3 compose 側は変わらない（41組一致・警告0） | 同じ点検 |
| K4 bash -n と shellcheck が通る | ローカルで実行 |
| K5 S3 バックアップ 10/18 03:30 が完了（#4461 の効果。この変更とは独立） | 予約「#4461 S3バックアップとSMTP長さ」10/18 10:30 |

## 戻し方
この PR を revert して再デプロイする（blue-green は --env-file に戻る）。

## 維持の仕組み
守り手: deploy に触る PR の審査役（Opus）。仕組み: スクリプト内のコメントでこの設計を指す。K1 の点検手順は recon に残す。

## 外部・過去事例の参照と我々への応用
- 過去事例 #4461（docs/handoff/smtp-password-literal/design.md）: 読み手の一部（compose）だけを見て書き方を変え、別の読み手（docker run --env-file）を確かめなかった。今回は読み手を全部洗い出し（compose 12サービス・backend・source 4本）、実物で長さを照合した。
- Docker の仕様: `--env-file` の値は引用符も含めて文字どおりに渡り、`--env NAME`（= なし）はクライアント側の環境から値を取る。どちらも本番の docker で実測して確かめた（recon 事実5・9）。外部の導入事例は使わない（理由: この構成に固有の不具合で、実測が直接の根拠になるため）。

## 設計審査（Opus 自己審査・独立した第二者レビューではない）
- 判定: APPROVE
- 根拠: 原因（--env-file が引用符を残す）を、本番の backend 内の長さ（33・先頭が `'`）と使い捨てコンテナの実測で確かめた。変更は1ファイル・数行で、受入条件はすべてコマンドで○×を判定できる。
- 未解決: 10/17 19:30〜23:40 に backend のメール送信が実際に失敗したかは未観測（recon「未観測」）。
