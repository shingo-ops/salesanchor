# card: 便2 ログイン許可の依頼の表に「会社の管理者に頼んだ時刻」の列を足す（migration）

状態: カード発行（Opus、2026-11-06）。PO の実装承認は 2026-11-06「1」（このまま作り始める）。設計: docs/handoff/tenant-owner-login-approval/design.md 便2（このカードだけで作業できるように中身を下に全部書く）。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: origin/main `6f33d365ae772d4628e7c03da277c820c1af629b`。下の行番号はすべてこの時点のもの。行がずれていたら、行番号ではなく「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）
- guards/00-common.md: 全コマンドを作業場所の cd から始める・出力に上限（tail）・sleep しない・プレースホルダを残さない。○
- guards/03-file.md・guards/05-pr.md: 触るファイルを §1 で全部挙げた。消すファイルは無い。PR は Opus が作る（Sonnet は push まで）。○
- guards/10-executor.md: 散文で組み立てを頼まない（§2 に新しいファイルの全文と、足す行の全文を書いた）。○

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin2 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin2-login-request-column` を origin から取り、`docs/handoff/tenant-owner-login-approval/card-2.md` が在ること。
- P2 `ls migrations/ | sort | tail -1` が `20261106_120000_create_discord_server_snapshot_tables.sql`（新しいファイル名 20261106_140000 がいちばん後ろになる）。
- P3 `tail -2 scripts/run_all_migrations.sh` が次の 2 行:
  ```
  # discord-server-management 便2: 自社用サーバーの今の姿の記録と反映の記録の表を作る（作るだけ・冪等）
  run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql
  ```
- P4 `grep -rn "admin_requested_at" migrations backend scripts .github` が 0 件。
- P5 `grep -n "name: 変更 SQL を 1回目実行（実行可否・構文チェック）" .github/workflows/migration-test.yml` が 1 件。

## 1. 触るファイル

新しく作る:
1. `migrations/20261106_140000_add_login_request_admin_requested_at.sql`（2-1）

書き換える:
2. `scripts/run_all_migrations.sh`（2-2。末尾に 2 行足すだけ）
3. `.github/workflows/migration-test.yml`（2-3。手を 1 つ足すだけ）

触らない: 上に挙げた以外のすべて。特に `backend/`、`frontend/`、ほかの `migrations/*.sql`、`.github/workflows/deploy.yml`、`.github/workflows/workflow-lint.yml`、`docs/`（このカードを除く）。上のファイルの中でも、書いていない行は 1 文字も変えない。

## 2. 変更の中身

### 2-1. 新しいファイル `migrations/20261106_140000_add_login_request_admin_requested_at.sql`（全文。このとおりに書く）

```
-- ADR-1063 便2: ログイン許可の依頼に「会社の管理者（持ち主）に頼んだ時刻」の列を足す（追加のみ・冪等）
--
-- 設計: docs/handoff/tenant-owner-login-approval/design.md 便2
-- 目的: 社員が新しい機械で「会社の管理者に頼む」を押した時刻を残す。持ち主の一覧はこの列が入った依頼だけを出す（便3）。
-- 足すだけ・NULL 可・既定値なし。既にある行は書き換わらない。値はアプリ（便3）が入れる。
-- RLS は付けない（表 public.auth_login_requests は ADR-1055 段A でログイン前に hash で1行を引くため RLS なし。列を足しても変えない）。
-- ai_ro・ai_cloud の見せ方: timestamptz は素通しの型のため分類の行は要らない。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（索引も一緒に消える。便3 が出る前なら使う人はいない）:
--   ALTER TABLE public.auth_login_requests DROP COLUMN IF EXISTS admin_requested_at;

ALTER TABLE public.auth_login_requests
    ADD COLUMN IF NOT EXISTS admin_requested_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN public.auth_login_requests.admin_requested_at IS '社員が「会社の管理者に頼む」を押した時刻。NULL は頼んでいない。ADR-1063';

CREATE INDEX IF NOT EXISTS ix_auth_login_requests_admin_requested
    ON public.auth_login_requests (admin_requested_at)
    WHERE status = 'pending' AND admin_requested_at IS NOT NULL;
```

### 2-2. `scripts/run_all_migrations.sh`

ファイルの最後の行 `run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql` の次に、次の 2 行を足す（ファイルの最後は改行 1 つで終える）:
```
# ADR-1063 便2: ログイン許可の依頼に「会社の管理者に頼んだ時刻」の列と部分索引を足す（列1つ・追加のみ・冪等）
run_sql migrations/20261106_140000_add_login_request_admin_requested_at.sql
```

### 2-3. `.github/workflows/migration-test.yml`

新しい SQL は表 public.auth_login_requests（20261101_130000）が先にある前提のため、既存の手「変更 SQL の前提の移行を先に実行（機械の許可の表）」と同じ形の手を 1 つ足す。

場所: `      - name: 変更 SQL を 1回目実行（実行可否・構文チェック）`（P5 の行）の直前。足す手の後ろに空行 1 つを置き、P5 の行に続ける。字下げは既存の手と同じ（`      - name:` は空白 6 つ、`if:`・`run:` は空白 8 つ、run の中身は空白 10 つ）。

足す全文:
```
      - name: 変更 SQL の前提の移行を先に実行（ログイン許可の依頼の表）
        if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261106_140000_add_login_request_admin_requested_at.sql')
        run: |
          # 20261106_140000 は auth_login_requests（20261101_130000）に列を足すので、その前提を本番と同じ順で先に入れる
          for sqlfile in migrations/001_create_auth_events.sql migrations/20261013_160000_add_self_hosted_auth_tables.sql migrations/20261101_130000_add_new_device_approval.sql; do
            echo "▶ $sqlfile を前提として実行中..."
            psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
            echo "✅ $sqlfile 成功"
          done

```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/tenant-owner-bin2-login-request-column && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P5 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/tenant-owner-login-approval/card-2.md | tail -1
    cd ~/sa && ls migrations/ | sort | tail -1
    cd ~/sa && tail -2 scripts/run_all_migrations.sh
    cd ~/sa && grep -rn "admin_requested_at" migrations backend scripts .github | tail -5; echo "P4 end"
    cd ~/sa && grep -n "name: 変更 SQL を 1回目実行（実行可否・構文チェック）" .github/workflows/migration-test.yml | tail -3

手順3 §2 の変更をする（2-1 → 2-2 → 2-3 の順）

手順4 差分を確かめる
    cd ~/sa && git status --short | tail -10
    cd ~/sa && git diff | tail -60
    cd ~/sa && cat migrations/20261106_140000_add_login_request_admin_requested_at.sql | tail -30

手順5 形の確かめ（期待: 1 つめ YAML OK、2 つめ 1 件、3 つめ 0 で終わる）
    cd ~/sa && python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/migration-test.yml')); print('YAML OK')" 2>&1 | tail -3
    cd ~/sa && grep -c "20261106_140000_add_login_request_admin_requested_at.sql" scripts/run_all_migrations.sh | tail -1
    cd ~/sa && bash scripts/check-migration-registration-exists.sh 2>&1 | tail -5; echo "exit=$?"
    cd ~/sa && node scripts/check-migration-column-churn.js 2>&1 | tail -5
    cd ~/sa && bash scripts/check-migration-duplicate-registration.sh 2>&1 | tail -5

手順6 実 DB で 2 回流す（PostgreSQL が手元にあるときだけ。無ければ「実 DB は CI の migration-test で確かめる」と書いて手順7 へ）
    cd ~/sa && which psql | tail -1

手順7 記録して送る
    cd ~/sa && git add migrations/20261106_140000_add_login_request_admin_requested_at.sql scripts/run_all_migrations.sh .github/workflows/migration-test.yml && git commit -q -m "feat(db): add auth_login_requests.admin_requested_at (ADR-1063 bin2)" && git log --oneline -1 | tail -1
    cd ~/sa && git push origin release/tenant-owner-bin2-login-request-column 2>&1 | tail -3

## 4. 想定される分かれ道

BLOCKED: に入ったら、その場で作業を停止し、それまでの出力と §5 の形の報告を返して終わる（直さずに先へ進まない・別のやり方を試さない）。

- P1〜P5 のどれかが外れた → 実装せず `BLOCKED: P番号 と見えたもの`。
- 手順5 の YAML が OK でない → 出力を報告して `BLOCKED: yaml`。
- 手順5 の 3 つの見張りのどれかが 0 以外で終わる・失敗の文が出る → 出力を報告して `BLOCKED: 見張りの名前`。
- 手順5 の見張りが node・bash が無くて始まらない → 出力を報告し「CI で確かめる」と書いて先へ進む。
- 変更前の行が見つからない・2 か所ある → `BLOCKED: ファイル名と行 変更前の文が一致しない`。
- push が拒まれた → 出力の最後の 3 行を報告して `BLOCKED: push`（force はしない）。

## 5. 報告の形

- 1 行目: 受領確認（`RECEIVED tenant-owner-bin2 HEAD=…`）。
- 手順2・4・5・6・7 の出力（tail の範囲）をそのまま貼る。
- §4 の分かれ道に入ったら、どれに入ったかと見えたもの。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

END OF CARD
