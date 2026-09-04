# カードの型

この文書は何か（専門用語なしの1行）: 設計パートナーが実装役に出す指示書の雛形。2026-09-04 の1日で実際に通った形だけを集めた。

- 日付: 2026-09-05
- 担当: architect
- 根拠: 2026-09-04 に発行した CM-01 から CM-42 のうち、成功したものと失敗したものの両方から抽出

## 0. この文書の使い方

設計パートナーは、セッション開始時に本書を読む。カードを書くときは、該当する型をコピーして固有名詞だけを埋める。型に無い操作が必要なときは、本書の末尾に追記してから使う。

実装役は本書を読まなくてよい。カードは単体で完結する。

## 1. 全カード共通の約束

### 1-1. 冒頭宣言

すべてのカードは次の1文で始める。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

理由: 前のカードの禁止が残っていると、次のカードで許可した操作まで止まる。2026-09-04 に実測。

### 1-2. 許可と禁止は名指しで書く

許可するものを列挙し、それ以外を禁止する。禁止側には、実装役が善意で取りそうな回避策を先回りして書く。

例: gh pr merge の直接実行、--admin、--auto、--no-verify、squash、permit-danger.sh の自己発行、失敗時の自力回避。

### 1-3. 停止条件は肯定形で書く

「〜の場合のみ次へ進む」の形にする。否定形（〜でなければ止まる）は、実装役が読み替えの余地を持つ。

### 1-4. 停止条件には「あるべきでないもの」を使う

正の期待値（UPDATE が 3 本ある）は設計パートナーが数える必要があり、数え間違える。2026-09-04 に3回起きた。
負の条件（INSERT が 0 本、DELETE が 0 本）は数えずに書ける。危険なものが混ざっていないことだけを停止条件にし、無害な数え上げは報告のみとする。

### 1-5. 生出力の様式

JUDGE_START_Sn と JUDGE_END_Sn で囲む。報告には区間の全文を含めさせ、折りたたみ・要約・罫線テーブル・「中略」を禁止する。

### 1-6. 判定を書かせない

「完了しました」「マージされました」を生出力なしで書くことを禁止する。判定は設計パートナーが行う。

### 1-7. 引用符の扱い

SQL 内のシングルクォートは @@ と書き、実装役に「@@ はシングルクォート1文字に置き換えて実行すること」と指示する。eval の使用と、シェル変数へのコマンド格納を禁止する。

## 2. 型A: 読み取りカード（SELECT のみ）

実績: CM-29 CM-30 CM-31 CM-36 CM-41手順1 で6回成功。

### 2-1. 禁止事項に必ず入れるもの

あらゆるテーブルへの INSERT / UPDATE / DELETE / CREATE / ALTER / DROP / TRUNCATE
psql -f の使用、< > によるリダイレクト入力
不等号 < > <= >= <> をSQL内に書くこと（BETWEEN を使う）
SQLの語句・列名・並び順を書き換えること

理由: ローカルの psql-write-guard が不等号と -f を書き込みと誤検知する。2026-09-04 に実測。

### 2-2. 手順の骨格

手順1: ファイル初期化と読み取り専用検算（SHOW transaction_read_only が on であること）
手順2以降: 1クエリ1手順。区画マーカー BEGIN / END で囲み、ファイルに追記
最終手順: 完了マーカーと集計（wc -l、BEGIN 数、END 数、ERROR 数、tail -1）

### 2-3. 接続の定型

ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@app.salesanchor.jp 'docker exec -e PGOPTIONS="-c default_transaction_read_only=on" astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -c "SELECT ...;"'

### 2-4. 報告の様式

チャットには手順1の tail と最終手順の JUDGE 区間だけを書かせる。ファイル中身の貼り付けを禁止し、ファイルは添付してもらう。

## 3. 型B: バックアップカード（CREATE TABLE AS SELECT）

実績: CM-32 CM-32b CM-32c CM-41 CM-41b。最初の2回は permit の仕様を知らずに失敗し、3回目以降で確立。

### 3-1. permit の仕様（2026-09-04 実測）

scripts/permit-danger.sh "psql write" は PO が手で実行する。実装役の自己発行はガードが止める。
チケットは ~/.claude/permits/ に置かれ、1回のコマンドで消費される。30分で失効する。
したがって、書き込みコマンド1本につき permit 1回が必要である。

### 3-2. 型の骨格

1カードにつき CREATE TABLE を1文だけ許可する。複数テーブルのバックアップは、カードを分けて PO に permit を1回ずつ発行してもらう。

手順1: 対象の現在値を読み取りで記録（変更前の証拠）
手順2: バックアップ名の空き確認（同名が無いこと）
手順3: CREATE TABLE ... AS SELECT を1文
手順4: 件数照合（バックアップと元テーブルが一致し、元テーブルが変わっていないこと）

### 3-3. 命名

tenant_004.<テーブル名>_bak_<YYYYMMDD>。同日に2回目を作るときは末尾に b を付ける。既存のバックアップは上書きも削除もしない。

### 3-4. 禁止事項に必ず入れるもの

上記1文以外のあらゆる書き込み
scripts/permit-danger.sh の実行
既存バックアップの上書き・削除

## 4. 型C: migration とPR起票カード

実績: CM-34（25商品登録）CM-42（5件訂正）で成功。CM-42 は停止条件の数え間違いで1回止まった。

### 4-1. 本便で本番DBに接続しない

migration はファイルを作るだけである。実行はマージ後のデプロイで run_all_migrations.sh が行う。この経路は psql-write-guard の対象外であり、permit は不要である。

### 4-2. 手順の骨格

手順1: scripts/new-worktree.sh <branch> --claude で作業台を作る。以降は worktree 内で作業する
手順2: migration ファイルを cat > で作る。SQL は全文をカードに同梱し、一字も変えずに入れさせる
手順3: scripts/run_all_migrations.sh の末尾を tail で見せ、既存の最終 run_sql 行の直後に1行追記させる。追記後に grep -n で1行だけ返ることを確認
手順4: 検算。停止条件には INSERT / DELETE / DROP など「あってはならないもの」が 0 であることを使う。正の本数は報告のみ
手順5: git add で対象2ファイルだけを指定し、commit、git diff origin/main --name-only で差分が2ファイルのみであることを確認してから push
手順6: PR 本文を一時ファイルに書き --body-file で作成。PR 番号が出たら worktree 直下に .pr-number を作る。git add はしない
手順7: gh run list --commit <HEAD> で関所の結果を取得。赤でも自力で直さない

### 4-3. migration の書き方（tenant_004 向け）

冒頭に pg_namespace のスキーマ存在ガードを置く。CI には tenant_004 が無く、本番が初回実行になるため。
INSERT には ON CONFLICT DO NOTHING を付けて冪等にする。
参照マスタの id は code から SELECT INTO で引く。uuid を直書きしない。
検証は担当範囲（code BETWEEN 'PMxxxx' AND 'PMyyyy'）だけを数える。テーブル全体を数えると、他の商品が増えたときにデプロイが止まる。2026-09-04 に実測。
書き込むテーブルの列定義は、書く前に \d で実測する。NOT NULL で初期値の無い列（category_class、position）を省略するとデプロイが止まる。2026-09-04 に実測。

### 4-4. PR 本文の必須節

## 概要
### 標準ワークフロー確認（対象ADR / recon / 設計 / 触るファイル / 削除するファイル / バックアップ確認）
### GO記録（マージカードで追記する。起票時点では書かない）

## 5. 型D: マージカード

実績: CM-28 CM-35 CM-38 CM-40 CM-40b。CM-40 は BEHIND で止まり、CM-40b で update-branch を許可して通した。

### 5-1. 手順の骨格

手順1: worktree に入り、ブランチ名・.pr-number・HEAD を確認
手順2: PR 本文を GO記録付きで差し替える。GO記録の文面はカードで指定し、実装役に書かせない
手順3: gh pr checks で fail が 0 件であることを確認。pending は60秒待って最大15回
手順4: gh pr view で state=OPEN、isDraft=false、mergeStateStatus=CLEAN を確認
手順5: bash scripts/gh-pr-merge-safe.sh --merge
手順6: 3経路の検算（gh pr view で MERGED、git merge-base --is-ancestor で 0、git show origin/main:<file> で行数）

### 5-2. BEHIND のとき

別の PR が先にマージされると mergeStateStatus が BEHIND になる。gh pr update-branch <番号> を許可する。git merge / rebase / push は禁止のままにする。更新後に GO記録が残っていることを grep で確認する。

### 5-3. .pr-number の場所

worktree 直下に置く。無いと gh-pr-merge-safe.sh が中断する。git add / commit はしない。

### 5-4. GO記録の形

GO発行者 / 日時 / GO原文 / バックアップ確認 / 提示した3行サマリ。文書のみの PR では「バックアップ確認: 該当なし」と、その理由を書く。

## 6. 2026-09-04 に止まった箇所の一覧

| 回 | カード | 原因 | 対処 |
|---|---|---|---|
| 1 | CM-08 | eval の引用符 | eval 禁止、@@ 置換に変更 |
| 2 | CM-10 | ガードが不等号を誤検知 | BETWEEN を使う |
| 3 | CM-13 | permit なしで CREATE | PO が permit を発行 |
| 4 | CM-21 | product_exclude_keywords の position を省略 | \d で列を実測してから書く |
| 5 | CM-27 | .pr-number が worktree 外 | worktree 直下に置く |
| 6 | CM-32 | permit が1回限りと知らず3文を1カードに | 1文=1カードに分割 |
| 7 | CM-40 | BEHIND に対する例外なし | update-branch を許可 |
| 8 | CM-42 | UPDATE の本数を数え間違い | 負の条件を停止条件にする |

いずれも実装役は正しく停止した。壊れたものは無い。

## 7. この文書の限界

型があっても、初めての事態には対応できない。止まることは仕組みとして正しい動作である。止まったら、原因を本書の第6節に追記し、必要なら型を直す。
