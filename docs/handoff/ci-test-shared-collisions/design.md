# design: CI の試験どうしのぶつかりで main が赤になるのを 0 回にする

状態: 便1は設計案作成済み・設計審査済み（Opus 自己審査）・PO の実装承認 2026-11-27「1」（合流・本番反映まで委任）。便2〜5は調べ待ちで、実装はできない。
参照: docs/handoff/ci-test-shared-collisions/recon.md（以下 recon）。区分: 試験コードだけを変える。製品コード・本番・CI 設定には触らない。

## 1. 目的（KGI）
main の試験が赤になるのは、今は試験どうしのぶつかりだけが理由である（recon §1。直近60回中9回）。赤が出るたびに、本当の不具合かどうかを確かめる手間がかかっている。
**KGI: 全便の合流後、main の Backend Tests が「試験どうしのぶつかり」で落ちる回数を、続けて30回のあいだ 0 回にする（今は60回中9回）。** PO 承認 2026-11-26「1」。

## 2. 進め方（1便1種類・変更→反映→測定）
| 便 | 種類 | 状態 |
|---|---|---|
| 便1 | D 役割が消える | 本書 §3 で設計済み。PO 実装承認 2026-11-27「1」 |
| 便2 | A 調べたが無い | 相手は確定（recon §3）。直し方の前に「未確認」2点をクラウドで調べる |
| 便3 | B 請求書の表 | 仕組みが未確定（recon §4）。クラウドで調べる |
| 便4 | C カルテ | 仕組みが未確定。クラウドで調べる |
| 便5 | E テナント998 | 覚え書きの残り件。クラウドで調べる |

便2〜5は、調べた結果を recon に足して、本書に便ごとの節を足す。便ごとに審査してから実装する。

## 3. 便1: 共通の役割を試験の後片付けで消さない

### 3-1. 変更前後
recon §2 の6ファイルについて、後片付けの中の共通の役割を消す部分だけを外す。使い捨ての DB を消す行（`DROP DATABASE ... WITH (FORCE)`）と、接続を閉じる行は残す。

| ファイル | 変更前 | 変更後 |
|---|---|---|
| `backend/tests/ops/test_ai_cloud_views.py:84-96` | `_Cluster` が始めの有無を覚え、`cleanup()` で無かった役割を消す | `_Cluster.cleanup()` は何もしない。中身を消し、理由のコメント1行を残す |
| `backend/tests/ops/test_ai_job_assignments_db.py:70-82` | 同上 | 同上 |
| `backend/tests/ops/test_ops_case_db.py:87-105` | 同上（`_ROLES` 7つ） | 同上 |
| `backend/tests/ops/test_ops_case_report_kind_migration.py:104-108` | `for r in _ROLES: if not existed[r]: DROP ROLE` | この for 文を外す |
| `backend/tests/test_ops_case_router.py:187-192` | 同上 | 同上 |
| `backend/tests/ops/test_ai_ro_views.py:98-99` | `if not role_existed: DROP ROLE IF EXISTS ai_reader` | この2行を外す |

- 使わなくなった変数（`existed`・`role_existed`・`_ROLES`・`self.existed` など）は、ほかで使っていなければ外す。使っていれば残す。lint（ruff）の指摘が 0 件になる形にそろえる。
- 理由のコメントの文: `# 共通の役割はクラスタ全体で1つ。別の係が使っている途中で消すと落ちるため、試験では消さない（docs/handoff/ci-test-shared-collisions/design.md 便1）`
- 触らない範囲: 役割を作る行、属性を一時的に変える試験（`test_ai_cloud_views.py:460-468`・`test_ops_case_db.py:621-627`）、`test_tenant_isolation_daily_check.py`（自分で作った名前の役割だけを消すため）、migration、製品コード、CI 設定。

### 3-2. 代替案と選んだ理由
- A（採用）共通の役割を消さない: 消すことが原因なので、消さなければ起きない。役割を作る migration は冪等なので、残っていても次の試験は困らない（recon §2）。CI の DB は回ごとの使い捨てで、残りは次の回に持ち越されない。
- B 役割の出入りを札で順番にする: 6ファイルのモジュール全体で札を持つことになる。同じ係の中で札を待ち合う危険があり、試験の時間も延びる（上限15分まであと約2分）。不採用。
- C 試験ごとに別の名前の役割を作る: migration は名前が決まっているので、名前を変えると migration の形を確かめられない。不採用。

### 3-3. リスクと対処
- 手元の DB に役割が残る。パスワードの無い役割なので、ログインには使えない（`20261024_100100_create_ai_reader_cloud_role.sql:2`）。手元で消したいときは手で消す。
- 属性を一時的に変える2か所の重なり（recon §2「未観測の近い危険」）は、便1では直さない。1便1種類の決まりに従う。便1の受け入れ基準 K4 で見張り、出たら次の便に入れる。

### 3-4. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1: 差分は §3-1 の6ファイルと、本書類（recon・design・review-opus）・台帳だけ | `gh pr diff --name-only`（審査役） |
| K2: 6ファイルに、共通の役割を消す `DROP ROLE` が1つも残らない | `git grep -n "DROP ROLE" -- backend/tests` で、`test_tenant_isolation_daily_check.py` 以外が0件（Opus） |
| K3: PR の必須チェック pytest が pass。6ファイルの試験は数が減らず、skip も増えない | `gh pr checks` と、PR の run の記録で6ファイルの passed 数を main の直近の回と比べる（Opus） |
| K4: 合流後の main の Backend Tests 30回で、`role "..." does not exist` と `already exists with unexpected attributes` が0件 | 30回分の失敗の記録を `--log-failed` で保存して数える（Opus・合流から約1〜2週） |

## 4. 外部・過去事例の参照と我々への応用
- PostgreSQL 16 公式（Context7 /websites/postgresql）: ALTER TABLE は明記が無ければ ACCESS EXCLUSIVE を取る。ACCESS EXCLUSIVE はほかのすべての札とぶつかる（explicit-locking.html）。便2以降で、巻き戻す DDL を長く持つ危険の根拠に使う。
- 過去の自分たちの例: 2026-11-05 と 11-06 に、札の外で DROP していた試験を札の中に入れて、デッドロックを0件にした（覚え書き test_lock_collisions・PR 5179）。便3〜5は同じ型で直せるかを先に確かめる。
- 数値の外部事例は使わない。直す対象はこのリポジトリの試験だけで、効果は自分たちの main の回数で測るため。

## 5. 維持の仕組み
- 守り手: 便1の K2 の `git grep` を、便の受け入れのときに Opus が流す。
- 将来の新しい試験が共通の役割を消す形を持ち込むのを、機械で止める見張りは便1には入れない。便2〜5で同じ型の見張りがまとまって要るかを判断して、最後の便で1つにまとめる（覚え書き no_repeat_mistake_rule）。
- KGI の数え方: 全便の合流後、main の Backend Tests 30回分の失敗の記録を Opus が読み、ぶつかりの種類ごとに数える。

## 6. 便1の実装カード（クラウドの担当へ渡す）
- 作業場所: 本書類と同じブランチ `release/ci-test-shared-collisions` に足す（1つの PR に設計と実装をまとめる）。`bash scripts/new-worktree.sh release/ci-test-shared-collisions` で場所を作り、`git switch -C release/ci-test-shared-collisions origin/release/ci-test-shared-collisions` で合わせる。
- 変更: §3-1 の表のとおり。触らない範囲は §3-1 の最後の項。
- 確かめ（手元で試験は回さない。試験は GitHub の CI で回す）:
  1. `git -C <wt> diff --stat` が6ファイルだけであること。
  2. `git -C <wt> grep -n "DROP ROLE" -- backend/tests` が `test_tenant_isolation_daily_check.py` の2行だけであること。
  3. `cd <wt>/backend && ruff check tests/ops/test_ai_cloud_views.py tests/ops/test_ai_job_assignments_db.py tests/ops/test_ops_case_db.py tests/ops/test_ops_case_report_kind_migration.py tests/test_ops_case_router.py tests/ops/test_ai_ro_views.py` が0件であること。
- 想定の分かれ道:
  - 消す対象の変数がほかの試験で使われていた → 変数は残し、消す行だけを外す。
  - 表の行番号が今の main とずれていた → 中身（`DROP ROLE` の for 文）で場所を決める。中身も違っていたら止めて報告する。
- commit して push する。PR は作らない（Opus が作る）。

## 審査（Opus 自己審査・2026-11-27）
- 便1は、原因（recon §2 の起きる順番）と直し方（消す行を外す）が1対1に対応している。既存 ADR との食い違いは無い（recon §5）。
- 受け入れ基準は、どれも記録や差分で ○× を決められる。
- 判定: 便1は APPROVE。便2〜5は REVISE（調べが要る。recon §3・§4 の未確認）。
- 未解決: 便2〜5の仕組み。属性を一時的に変える2か所の重なり（未観測）。
