---
mode: handoff
---
# 実装カード 便1: 配信先のシートとお客さん（閲覧者の名簿）をつなぐ

親: [design.md](./design.md) §3-3・§3-5「配信するシート」・§3-7・§7（便1の行）・§6 Q1・Q1b・Q2・Q5

- 状態: カード作成済み（2026-11-04 Opus）・PO 実装承認済み（2026-11-04 21:20 JST ごろ・チャットで「１」。選択肢「作り始める：クラウドの担当に作業指示を渡して作らせます」）。マージと本番への反映の GO は兼ねない。
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: A（`migrations/` と `scripts/` と `frontend/api-contract/` を触るため。ADR-1015）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（シートとお客さんをつなぐだけ。請求先は便2） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に削除が想定外に無いこと） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順9） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に実在を確かめる）、04-worktree.md（起点は origin/main・push は `-u origin HEAD`）、05-pr.md（`gh pr create` を直に使わない → PR は Opus が `gh-pr-create-safe.sh` で作る・触るファイル欄は1行カンマ区切り）、07-migration.md（`run_all_migrations.sh` に登録・採番は直近を見てから）。クラウドでも `new-worktree.sh` で作業場所を作る（`git switch -c` だけだと commit の検査で止まった前例がある）。

基準: 設計の基準 origin/main d948cf9c7。2026-11-04 に origin/main 63a69bfb6 と比べ、下の §2 の対象ファイルに差分 0 を確認済み。行番号は d948cf9c7 時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便1で利用者に見える変化）

- 閲覧者管理ページで、本契約のお客さんを開くと、その人のシート（名前・最後の配信時刻・結果）が見え、そこで登録・変更できる。
- 配信先の画面（/super-admin/tcg-distribution）と閲覧者管理ページは同じ1つの表を読み書きする。
- 本契約（active）の人のシートにだけ書き込む。停止したら自動で止まり、停止を外すと自動で戻る。お試しの人には登録してあっても書かない。特定の人用でないシートは今までどおり。
- 1人1シートまで。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `migrations/20261104_xxxxxx_add_tcg_distribution_targets_viewer_account_id.sql`（新規。時刻部分は作成時の時刻） | 列・外部キー・部分一意索引・COMMENT。冪等 |
| `scripts/run_all_migrations.sh` | 末尾の `run_sql migrations/...` の並びの最後に1行足す |
| `backend/app/services/tcg_distribution_svc.py` | list_targets・get_target の判定、配信の判定、create・update・soft_delete、専用の例外 |
| `backend/app/routers/tcg_distribution.py` | 入力の型、例外を 409・422 に直す、null でつなぎを外す |
| `backend/app/line_import_admin.py` | 配信前の点検が deliverable と理由を読む |
| `backend/app/services/tcg_analysis_dashboard_svc.py` | 配信の数を list_targets の呼び出しに替える |
| `backend/app/routers/tcg_analysis_dashboard.py` | DistributionTargetItem に3つの値を足す |
| `frontend/api-contract/openapi.json` と生成される型 | 下の §5 手順7 の命令で作り直す（手で書かない） |
| `frontend/src/pages/super-admin/TcgDistributionPage.tsx` | 配信していない理由を Badge で出す・お客さんを選べるようにする |
| `frontend/src/pages/super-admin/ViewerAccountsPage.tsx` | 詳細スライドに「配信するシート」の区切り |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | 新しいキー（両方に同じキー） |
| 試験（`backend/tests/` の配信先の試験・`backend/tests/test_viewer_purge.py`・画面の試験） | §3 の受入条件を確かめる試験 |

触らないもの: 請求先の表（便2）・鍵の用途・文面テンプレート・閲覧ページ（`frontend/src/pages/viewer/`）・`.github/`・`deploy.yml`・ADR と仕様書の文書・プライバシーポリシー・`ops_case` と `ai_cloud_views` の migration（便1は新しい表を作らず、足す列は BIGINT のため分類の行は要らない。design §3-2 の3）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. migration

- `public.tcg_distribution_targets` に `viewer_account_id BIGINT NULL REFERENCES public.viewer_accounts(id) ON DELETE CASCADE` を足す。`ADD COLUMN IF NOT EXISTS` で冪等に。外部キーの名前は既存の命名に合わせる。
- 部分一意索引 `uq_tcg_distribution_targets_viewer_account_id` ON `tcg_distribution_targets(viewer_account_id)` WHERE `viewer_account_id IS NOT NULL`。`CREATE UNIQUE INDEX IF NOT EXISTS`。
- 列に COMMENT（「この配信先を使うお客さん（閲覧者の名簿の番号）。NULL は特定の人用でないシート。名簿の行が消えると配信先も消える」）。
- 書き方は `migrations/20261016_150000_add_viewer_accounts.sql` にそろえる。

### 3-2. 配信するかの判定（1か所だけ）

- list_targets・get_target（`tcg_distribution_svc.py` :701〜:724 付近）の SELECT で `public.viewer_accounts` を LEFT JOIN し、各行に `deliverable`（真偽）と `reason`（`manual_off`／`suspended`／`not_contracted`／NULL）を SQL で出す。
- 理由は1つだけ。式はこの1つ:
  `CASE WHEN NOT t.is_active THEN 'manual_off' WHEN va.status = 'suspended' THEN 'suspended' WHEN t.viewer_account_id IS NOT NULL AND va.status <> 'active' THEN 'not_contracted' END`
  `deliverable` は reason が NULL のとき真。
- 配信の判定（:990〜:994 付近。今は is_active を見る）は `deliverable` を見る。
- 判定を書き写さない: `line_import_admin.py` :134・:139 付近の active と targets は list_targets の値を読む。`tcg_analysis_dashboard_svc.py` :665〜:687 付近の自前の SELECT は list_targets の呼び出しに替える。
- is_active は書き換えない（停止で false にしない）。

### 3-3. 書き込み

- create_target・update_target（:727〜:775 付近）に viewer_account_id を足す（INSERT の列と update の allowed）。
- 書いた後は RETURNING の値でなく get_target で読み直して返す。
- IntegrityError を SQLSTATE で分ける: 23505 かつ索引名が `uq_tcg_distribution_targets_viewer_account_id` → 専用の例外 → router で 409。23503 → 専用の例外 → router で 422。それ以外はそのまま上げる。router の返し方は同じファイル :163 付近の 409 と同じ形。
- 入力の型 DistributionTargetCreate・DistributionTargetUpdate（router :44・:52 付近）に `viewer_account_id: int | None`。PUT は今 `model_dump(exclude_none=True)`（:129 付近）なので、viewer_account_id だけは `model_fields_set` に入っていれば null でも渡し、NULL に戻せるようにする。
- soft_delete_target（:778〜:789 付近）は、同じ UPDATE の1文で is_active を false にし、viewer_account_id を NULL にする。
- 応答の型 DistributionTargetItem（`tcg_analysis_dashboard.py` :184 付近）に viewer_account_id・deliverable・reason。配信先 API の応答にも同じ3つが出ること。
- シートを自動で作らない決まり（`tcg_distribution_svc.py` :15 の #2）は変えない。

### 3-4. 画面

- 金型だけを使う（ADR-144）。色・余白はデザイントークンだけ（ADR-067）。文字はすべて `t()`（ADR-027）。新しい部品は作らない。金型にない部品が要ると分かったら、そこで止まって報告する。
- 閲覧者管理ページの詳細スライド（Drawer）に「配信するシート」の区切り: Stack で、シートの名前・最後の配信時刻・結果を文字で、配信していない理由を Badge で出す。登録・変更は Modal＋TextField（ブックの番号・タブ名）＋Button。シートが無いときは EmptyState。書き込みは今の配信先 API（POST・PUT `/tcg/distribution/targets`）を呼ぶ。新しい書き込み API は作らない。
- 409 は「この人にはもうシートがあります」、422 は「お客さんが見つかりません」に当たる文言を `t()` で出す（キー名は既存の並びに合わせる）。
- 配信先の画面: 各行に配信していない理由（手で止めた／停止中／本契約でない）を Badge で出す。行にお客さんを選ぶ欄を付けるかは、既存の金型（Select）で作れる範囲にする。

### 3-5. 試験に足すもの

- `backend/tests/test_viewer_purge.py` :143〜:149 付近の「消えた表」の並びに `tcg_distribution_targets` を足す（便1では請求先の表は足さない）。
- 着手前に確かめること（設計審査で未確認）: この試験の pg fixture（`tests.test_tcg_work_matching_integration` の pg）で migration が流れ、`tcg_distribution_targets` があること。無かったら止まって報告する。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- PR を作る前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／金型にない部品が要るとき／design.md と食い違うのに design.md どおりに作れないとき／§3-5 の fixture に表が無いとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバーに接続しない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、手順1 の `cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降の命令は毎回その作業場所へ cd してから流す（下の `cd 作業場所` はそのパスに読み替える）。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/viewer-sheet-link-bin1
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。違えば NEEDS_DECISION: で止まる。

手順2 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat d948cf9c7 origin/main -- backend/app/services/tcg_distribution_svc.py backend/app/routers/tcg_distribution.py backend/app/line_import_admin.py backend/app/services/tcg_analysis_dashboard_svc.py backend/app/routers/tcg_analysis_dashboard.py frontend/src/pages/super-admin/TcgDistributionPage.tsx frontend/src/pages/super-admin/ViewerAccountsPage.tsx backend/tests/test_viewer_purge.py
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順3 §3-1 の migration を作り、`scripts/run_all_migrations.sh` の並びの最後の `run_sql` の次の行に登録する。ファイル名の時刻は、`migrations/` の直近のファイル名を見てから、それより後の時刻で付ける。

手順4 §3-2・§3-3 の backend を直し、§3-5 と下の §6 の受入条件の試験を書く。

手順5 §3-4 の画面と ja.json・en.json を直す。

手順6 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json
    cd 作業場所/frontend && npm ci
    cd 作業場所/frontend && npm run generate:api-types

手順7 試験を流す
    cd 作業場所/backend && python -m pytest tests/test_viewer_purge.py -q
    期待する出力: 全部 passed。PostgreSQL が無くて skipped になったら、その数と理由を報告に書いて続行する（CI で確かめる）。足した配信先の試験も同じく流し、結果を全文報告に書く。
    cd 作業場所/frontend && npx vitest run src/pages/super-admin
    期待する出力: 全部 passed。

手順8 commit
    cd 作業場所 && git add -A
    commit 文は Write でファイルに書き（1行目 `feat: link distribution sheets to viewer customers (bin1)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: commit の番号と、§2 の表のファイルだけ。

手順9 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表のファイルだけ。削除の数（2列目）が 0 でないファイルは、名前と消えた行の中身を報告に書く（既存の行の書き換えはあってよい）。表に無いファイルがあれば、その名前を報告に書いて止まる。

手順10 push（PR は作らない。PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使って作る）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/viewer-sheet-link-bin1
    期待する出力: 手順8 の commit と同じ番号。

## 6. 受入条件（design.md §7 の便1の行）

| 基準 | 検証方法 |
|---|---|
| 閲覧者管理ページで本契約の人を開くと、その人のシートの名前・最後の配信時刻・結果が出る | 画面テスト＋PO 目視 |
| 閲覧者管理ページでシートを登録すると、配信先の画面にも同じ1件が出る（表は1つ） | API テスト（同じ行を読む）＋PO 目視 |
| 特定の人用でないシート2件は、今までどおり配信される | 本番の配信結果の読み取り（Opus が出荷後に） |
| 本契約の人を停止すると、次の配信でその人のシートだけ書き込まれず、他は ok。停止を外すと書き込みが戻る | PG テスト（停止・解除の前後で配信の結果を比べる）＋PO 目視 |
| 手で止めた（is_active=false）シートは、停止を外しても止まったまま | PG テスト |
| お試し（trial・期限切れを含む）・pending・verified の人のシートは書き込まれない。本契約にすると次の配信で書き込まれる | PG テスト |
| 同じ人に2つ目のシートを登録すると 409 で、DB にも入らない。特定の人用でないシートは何件でも登録できる | PG テスト＋API テスト |
| 名簿の行が自動削除されると、その人の配信先の行も消える | PG テスト（maintenance の削除を流す。test_viewer_purge） |
| 配信先を削除すると viewer_account_id が NULL になり、同じ人に新しいシートを登録できる。手で止めただけのシートが残っている人には2枚目を登録できない（409） | API テスト＋PG テスト |
| 配信しないシートは、配信先の画面・閲覧者管理ページ・解析ダッシュボードの配信の数・配信前の点検の4か所で同じ理由になる | API テスト（同じ行を4つの入口から読んで値を比べる） |
| null を送るとつなぎが外れる。名簿に無い番号は 422 | API テスト |
| 画面に直書きの文字・色が無い | 既存の CI（i18n・デザイントークン・UI governance） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: scripts/run_all_migrations.sh, backend/app/services/tcg_distribution_svc.py`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `区分: A`、`PO承認:` に PO の実装承認の言葉と日時、`Opus 審査記録: docs/handoff/viewer-customer-sheet/review-opus.md`、`対象ADR: ADR-1019`、`設計仕様書（あるべき姿）: docs/specs/inventory-management/inventory-viewer/README.md`。
- migration を含むので、マージは GO（ADR-136 の形）まで待つ。

## 7. 報告

- 報告の冒頭に「本報告はカード 便1（配信先のシートとお客さんをつなぐ）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「カード 便1 を受領」と1行書く。
- 完了報告の本文に、手順1・2・7・8・9・10 の生出力を全文含める。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
