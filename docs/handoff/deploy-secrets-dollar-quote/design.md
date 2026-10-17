# design: deploy.yml が .env に書く secrets をすべて単一引用符にする（件1）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:5-9（#4481 件1）。recon: [recon.md](./recon.md)
> 状態: 本番反映済み（#4498、merge 6d543ff62、2026-10-17T17:25Z）。K1〜K4 ○（下の「結果」節）。設計審査は Opus 自己審査 APPROVE、PR は Reviewer エージェント APPROVE。PO 2026-10-18 チャットで件1着手に「y」。マージ・デプロイまでの完走は 2026-10-17 に委任済み。

## 目的（利用者に見える変化）
今は、本番の秘密の値（パスワード・トークン）を作り直したときに `$` や空白が入ると、その値が黙って欠けます。欠けると、メール送信や S3 バックアップが止まります（10/16・10/17 に実際に起きた）。この変更で、どの値に `$`・空白・`#` が入っても欠けなくなります。値に `'` か改行が入ったときは、本番に入る前にデプロイが止まって知らせます。今の値はどれも変わりません（recon 事実3・5）。

## KGI（○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | deploy.yml の heredoc で、COMPOSE_FILE 以外の35行がすべて `KEY='${{ secrets.X }}'`。引用符なしの行は0 | `grep -cE "^ +[A-Z0-9_]+='\\$\\{\\{ secrets\\.[A-Z0-9_]+ \\}\\}'$"` が35／`grep -cE "^ +[A-Z0-9_]+=\\$\\{\\{ secrets"` が0（heredoc 範囲で） |
| K2 | 模擬試験（ローカル・bash）で次をすべて満たす。①`$`・空白・`#`・空・`"` を含む擬似値を source すると、元の値と1文字も違わない ②`'` を含む値、改行を含む値ではそれぞれ終了コード1、`.env` が変更前と同一（cmp）、出力に擬似値の文字列が0回 ③正常時は `.env.bak` と `.env.secrets.new` が残らない | Sonnet がステップの該当部分を抜き出して実行。生出力を /tmp/CC報告ファイル/kenn1/sim/ |
| K3 | 本番のデプロイ後: .env の36キーのうち35行が単一引用符・COMPOSE_FILE はそのまま／compose の各サービスと backend で、.env を source した長さと一致しないキーが0／compose config の警告 "variable is not set" が0／`set -euo pipefail` で source が通る | 本番で読み取り専用の点検（値は出さず、キーと長さだけ）。手順は bg-cutover-env-by-name の K1・K3 と同じ。生出力 /tmp/CC報告ファイル/kenn1/prod/ |
| K4 | main マージ後、push で動く workflow（Deploy to VPS を含む）がすべて success | `gh run list --commit <merge sha>` |

## 変更（.github/workflows/deploy.yml のみ。行番号は 88391573c）
1. :314 の `rm -f .env.bak` を消す（検査の後へ移す。sed が作った `.env.bak` は、消す前の `.env` の写し）。
2. :323 の `cat >> .env <<'ENV_EOF'` を `cat > .env.secrets.new <<'ENV_EOF'` に変える。
3. :324-358 の34行を `KEY='${{ secrets.X }}'` にする（:351 SMTP_PASSWORD は既にこの形）。:359 の COMPOSE_FILE は変えない。
4. :360 の `ENV_EOF` の直後に、次を足す（値は出さず、行番号だけを出す）。
   ```bash
   # 件1（docs/handoff/deploy-secrets-dollar-quote/design.md）: 値に ' か改行があると単一引用符が壊れる。
   # 壊れた行があれば .env を書き換える前の状態に戻して止める。出すのは heredoc 内の行番号だけ（値は出さない）。
   _bad_lines=$(grep -nvE "^[A-Z0-9_]+='[^']*'$|^COMPOSE_FILE=" .env.secrets.new | cut -d: -f1 | tr '\n' ' ')
   if [ -n "${_bad_lines}" ]; then
     echo "❌ secrets の値に単一引用符か改行がある（heredoc の行: ${_bad_lines}）。.env は変更前に戻した"
     mv .env.bak .env
     rm -f .env.secrets.new
     exit 1
   fi
   cat .env.secrets.new >> .env
   rm -f .env.secrets.new .env.bak
   ```
5. :538-539 の ADMIN_DATABASE_URL を次にする。
   ```bash
   case "${ADMIN_DATABASE_URL}" in
     *"'"*|*$'\n'*) echo "❌ ADMIN_DATABASE_URL に単一引用符か改行がある（値は出さない）"; exit 1 ;;
   esac
   sed -i '/^ADMIN_DATABASE_URL=/d' .env
   echo "ADMIN_DATABASE_URL='${ADMIN_DATABASE_URL}'" >> .env
   ```
6. :726 のロールバック通知の予備の読み方で、引用符を外す: `… | cut -d= -f2- | tr -d "'")`。値に `'` が入らないことは手順4で保証する。
7. コメント :265-274 の「quoted heredoc …」の下に1行足す: 「値は単一引用符で囲む（compose も source も文字どおり読む。件1 design）」。

## 触らない範囲
- sed の削除リスト :276-313（`^KEY=` は `KEY='…'` の行にも当たるので、そのまま使える）、DATABASE_URL の3か所（quote 済み）、POSTGRES_* など PO が VPS で手で書いたキー、scripts/blue-green-cutover.sh・run_all_migrations.sh・backup_*.sh、docker-compose*.yml、backend/。
- `.github/workflows/workflow-lint.yml`（PO 本人のみ）。

## 代替案
- A（採用）: 全部を単一引用符にし、書く前に `'` と改行を検査する。compose と source が同じ値を読み、`$`・空白・`#` が安全になる。
- B: 何もしない（今の値は無事。recon 事実3）。secret を作り直したときに、黙って欠ける事故が再発する（10/16・10/17 の S3 バックアップ停止と同じ形）。不採用。
- C: 二重引用符にする。compose も source も `$` を展開するので、`$` を守れない。不採用。
- D: 値の中の `'` を `'\''` に置き換えて書く。`${{ secrets.X }}` は shell の変数ではなく、GitHub が文字として埋め込むため、置き換えるには値を一度 shell 変数に移す必要がある（env: 経由）。35個すべてを env: に移すのは変更が大きい。今の値に `'` は0なので、検査で止めるほうが小さく確実。不採用。

## リスクと対処
- 引用符を引用符ごと読む読み手が残っている → 36キーで該当するのは :726 の1か所だけ（recon 事実4(c)）。手順6で外す。K3 で compose と backend の長さを全部照合する。
- 検査で止まったときに secrets の無い .env が残る → sed の `.env.bak` に戻してから止める（手順4）。K2② で確かめる。
- 将来、引用符なしの行を heredoc に足す → 検査がその行を引っかけ、デプロイが変更前の .env のまま止まる（気づける）。
- 本番での失敗: Deploy の Step 2 で止まると、コンテナは古いまま動き続ける（Step 3 の前）。

## 戻し方
この PR を revert して再デプロイする。sed が `^KEY=` の行を消してから書き直すので、.env は引用符なしの形に戻る。

## 危険パス・GO
- `.github/workflows/deploy.yml`（危険パス）。DB・migrations/ は触らない。バックアップ確認: DB は変えないので対象外。.env の変更前の写しは手順4の `.env.bak` が自動で作り、失敗時に戻す。
- GO は「POの委任に基づくClaude Opus発行」（委任根拠: PO 2026-10-17 チャット「PRマージ、デプロイまで完走させてくれ」、件1着手 2026-10-18「y」）。

## 外部・過去事例の参照と我々への応用
- 公式仕様: Docker Compose の .env の解釈（recon 事実5、2026-10-18 確認）。単一引用符は文字どおり、引用符なし・二重引用符は展開。これを根拠に単一引用符を選ぶ。
- 過去事例: #4461（SMTP_PASSWORD を単一引用符に → compose と source は直った）、#4486（--env-file が引用符を残す → 名前で渡すように直し、backend 69/69 一致）。本便は #4461 と同じ形を残りの34キーへ広げる。--env-file の問題は #4486 で解消済みなので、副作用は起きない（recon 事実4(f)）。外部の導入事例は使わない（この構成に固有の書き方の問題で、公式仕様と本番の実測が直接の根拠になるため）。

## 維持の仕組み
守り手: deploy.yml に触る PR の審査役（Opus）。仕組み: 手順4の検査が、引用符の無い行や壊れた値をデプロイ時に止める。コメント（手順7）がこの設計を指す。

## 審査（Opus 自己審査・同一 AI。独立の第二者レビューではない）
- 判定: APPROVE。
- 根拠: 読み手を4種すべて洗い出した（recon 事実4）。引用符で値が変わる読み手は :726 の1か所で、手順6で対処する。今の値は `'`・改行・空白を含まない（recon 事実3）ので、変更の前後で値は変わらない。受入条件はすべてコマンドで○×が出る。
- 未解決: 無し（K3 は本番でしか測れない。前例と同じ手順で測る）。

## 結果（2026-10-18 実測）
| # | 結果 | 根拠 |
|---|---|---|
| K1 | ○ 35/0 | Sonnet が heredoc 範囲で grep（HEAD 49494e7a5） |
| K2 | ○ 全ケース | /tmp/CC報告ファイル/kenn1/sim/result.md（ケースA 36/36 一致、B・C は rc1・.env 不変・値の出力0、ADMIN 3ケース、:740 の読み方） |
| K3 | ○ | /tmp/CC報告ファイル/kenn1/prod/k3_result.txt・k3_smtp_result.txt。35/35 が単一引用符、COMPOSE_FILE 1/1、ADMIN_DATABASE_URL 単一引用符、source rc=0、警告0、backend コンテナ 36/36 一致。compose config の表示で SMTP_PASSWORD だけ長さが +1（backend・celery-worker）。表示上 `$` が `$$` に書き換わるためで（表示 32＝実値 31＋`$` 1個）、動いている backend・celery-worker の値は 31 で一致した |
| K4 | ○ | merge 6d543ff62 の push で動いた7本がすべて success（Deploy to VPS run 39053664101、17:27:46Z） |

- 審査の低い指摘（今回は直さない）: ①このステップに `set -o pipefail` を足すと、検査の grep が普段の終了コード1で止まり、.env を戻せない。足すときは `|| true` を付ける ②sed と検査の間で、検査以外の理由（ディスク満杯など）で失敗すると .env は戻らない（変更前から同じ）。
