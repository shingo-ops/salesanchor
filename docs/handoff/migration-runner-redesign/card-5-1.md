---
mode: handoff
---
# 実装カード：値を書く移行 8本の値の文を NOTICE だけにする（段5 5-1・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「出すもの」） |
| 4 | 1便1目的（8本の値の文を外す＋その試験1本だけ） | ○ |
| 5 | ブランチの起点を明示（`origin/main`。このカードが main に入った後） | ○ |
| 6 | 書式は実例で示す（下の「変更後」は全文） | ○ |
| 7 | 合格基準を出力まで縛る | ○（「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは停止して報告 | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提（決まっていること）
- 設計: `docs/handoff/migration-runner-redesign/design.md` §5-5・§5-9（K5-1・K5-1b）・§5-10 の 2。分けた表: `docs/handoff/migration-runner-redesign/p11-classification.md` §3（無効にする8本）。先に全部読む。
- PO の決定: 2026-11-15「1」（8本を止める。消したデータが戻らなくなる）。
- 前の同じ形の作業: `docs/handoff/neutralize-value-migrations-3c/design.md`、印と NOTICE の形は `migrations/064_add_users_is_super_admin.sql:44-50`、試験の形は `backend/tests/test_value_migrations_neutralized_3c.py`。
- 行番号はカードを書いた時点（`origin/main` `2ccb6a94e`）の物。ずれていたら文の一致で探す。**文が見つからない・中身が下の「変更前」と違うときは停止**。
- 本番のサーバーと DB には一切つながない。SQL は流さない（試験は DB 不要の静的な試験だけ）。

## 触るファイル（9本）と触らない範囲
- 触る: 下の8本の `migrations/*.sql` と、新しい試験 `backend/tests/test_value_migrations_neutralized_5_1.py`（新規）。
- 触らない:
  - `scripts/run_all_migrations.sh`（登録の行 :299・:351・:412・:654・:752・:787・:790・:1050 はそのまま。ファイルを消さない・登録を外さない）。
  - `.github/workflows/migration-test.yml`（:179・:181・:797・:805 は #43 のために表を用意するだけ。表を作る文は残るので困らない。古いコメントは残りの作業として報告に書くだけ）。
  - `scripts/migration-guard/value-write-allowlist.tsv`（8本は一覧に無い。行を足さない・消さない）。
  - ほかの44本の移行・アプリのコード・ほかの試験。
- 各ファイルで外すのは値を書く文（と #17 の件数の確かめ）だけ。表・列を作る文は残す。ファイルの頭の説明のコメントは残す（書き換えない。例外は #25 の :6-10 だけで、名前を消すため下の節のとおり置き換える）。

## 印の書き方（8本共通）
- 印の1行目: `-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): <外した物>`（この文字列 `NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15)` は試験が探す。1文字も変えない）。
- 続けて理由・決定・`-- 元の内容は git history で参照可能。` を書く。
- 最後に NOTICE を1つ。`'ADR-1007 neutralized: ... (<ファイルの番号>)'` の形。

## 1本ずつの変更

### 1. `migrations/027_backfill_customer_contact_channels.sql`（#1）
- 変更前: :1-13 が説明のコメント、:14-81 が DO ブロック1つ（INSERT :36-50・:63-72）。
- 変更後: :1-13 はそのまま。:14-81 を消し、次に置き換える。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 連絡手段の写し（customers.primary_contact_channel と customer_discord から customer_contact_channels への INSERT 2つ）を外した。
-- 2026-04-23 の一度きりの役目は終わっている。毎回の本番反映で、消した連絡手段の行が戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #1
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: contact channel backfill removed (027)'; END $$;
```

### 2. `migrations/054_add_users_theme.sql`（#3）
- 変更前: :4-5 が `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS theme ...`。:7 と :9 がコメント、:10-12 が審査用の利用者1人の theme を戻す UPDATE。
- 変更後: :1-6 はそのまま。:7-12 を消し、次に置き換える。**消した後のファイルに、その利用者のメールアドレスが残らないこと**（:9 のコメントも消す）。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 審査用の利用者1人の theme を 'light' に戻す UPDATE を外した。
-- 列の既定値 'light' で足りる。毎回の本番反映で、画面で変えた色を戻していた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #3
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: review user theme reset removed (054)'; END $$;
```

### 3. `migrations/098_migrate_customer_discord_to_company_discord.sql`（#5）
- 変更前: :1-18 が説明のコメント、:20-132 が DO ブロック1つ（名前が合わないと止める RAISE EXCEPTION :87-90、INSERT :94-121）。
- 変更後: :1-19 はそのまま。:20-132 を消し、次に置き換える。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): customer_discord から company_discord への写し（INSERT と、名前が合わない行で止める RAISE EXCEPTION）を外した。
-- 一度きりの移し替えは終わっている。毎回の本番反映で、消した会社の Discord の行が戻り、名前が合わない行があると反映が止まる形だった。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #5
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: customer_discord to company_discord copy removed (098)'; END $$;
```

### 4. `migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql`（#12）
- 変更前: :1-16 が説明のコメント、:18-106 が DO ブロック1つ（INSERT … ON CONFLICT DO NOTHING :36-100）。
- 変更後: :1-17 はそのまま。:18-106 を消し、次に置き換える。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): conversation_logs から meta_messages への写し（INSERT … ON CONFLICT DO NOTHING）を外した。
-- 一度きりの移し替えは終わっている。毎回の本番反映で、消したメッセージの行が昔の会話の表から戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #12
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: conversation_logs to meta_messages copy removed (20260622_020000)'; END $$;
```

### 5. `migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql`（#17）
- 変更前: :6 `DO $body$`、:9 `_count  INTEGER;`、:14-19 会社の有無のガード、:24-37 `CREATE TABLE IF NOT EXISTS %I.tcg_unit_evidence_rules`、:39-123 4件の INSERT … ON CONFLICT (id) DO NOTHING、:125-132 件数の確かめ（4件でなければ RAISE EXCEPTION :130-132）、:134 件数の NOTICE、:135 `END $body$;`。
- 変更後: :1-8 と :10-38 はそのまま（:9 の `_count` の宣言は使わなくなるので消す）。:39-135 を消し、次に置き換える（DO ブロックの中なので字下げ4つ）。
```sql
    -- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 4件の seed（INSERT … ON CONFLICT DO NOTHING 4つ）と、4件でなければ止める件数の確かめを外した。
    -- 毎回の本番反映で、消した行が戻り、行を足すと反映が止まっていた。表を作る文は残す。
    -- 件数の確かめも外すのは、値の文だけ外すと表が空の環境で 0件になり反映が止まるため（p11-classification.md §3）。
    -- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #17
    -- 元の内容は git history で参照可能。
    RAISE NOTICE 'ADR-1007 neutralized: tcg_unit_evidence_rules seed and count check removed (20260903_120000)';
END $body$;
```

### 6. `migrations/20260905_120000_register_15_suppliers_t004.sql`（#24）
- 変更前: :1-9 が説明のコメント、:11-80 が DO ブロック1つ（INSERT :36-55・:63-78。仕入れ先の名前を含む）。
- 変更後: :1-10 はそのまま。:11-80 を消し、次に置き換える。**消した後のファイルに、仕入れ先の名前が残らないこと**。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): tenant_004 の仕入れ先15件と LINE の連絡手段の行の登録（INSERT 2つ）を外した。
-- 一度きりの登録は終わっている。毎回の本番反映で、消した仕入れ先の行が tenant_004.tcg_suppliers に戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #24
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: tenant_004 supplier registration removed (20260905_120000)'; END $$;
```

### 7. `migrations/20260905_150000_record_manual_supplier_fixes_t004.sql`（#25）
- 変更前: :1-20 が説明のコメント、:22-120 が DO ブロック1つ（UPDATE は既に外してある :47-50。INSERT :56-60・:62-73・:79-83・:85-96、読むだけの確かめ :107-117）。
- 変更後: :1-5 と :11-21 はそのまま。頭のコメントの :6-10（仕入れ先と人の名前が4か所ある。#24 と扱いをそろえて名前を残さない）を消し、次の5行に置き換える。
```sql
--   (1) SP0007 name の復旧（#3306/#3309 確認画面誤操作で上書きされた name）
--   (2) SP0184 name の復旧（同上）
--   (3) SP0203 新規登録 + LINE チャンネル行
--       （HTTP 422 で画面登録できなかったため直接 INSERT）
--   (4) SP0204 新規登録 + LINE チャンネル行（同上）
```
- 続けて :22-120 を消し、次に置き換える。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 手で直した仕入れ先2件と LINE の連絡手段の行の登録（INSERT 4つ）と、その確かめの NOTICE を外した。
-- 一度きりの手直しの記録。毎回の本番反映で、消した仕入れ先の行が戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #25
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: manual supplier fixes record removed (20260905_150000)'; END $$;
```

### 8. `migrations/20260929_120000_fix_source_messages_received_at.sql`（#43）
- 変更前: :1-4 がコメント、:6-9 が `UPDATE public.source_messages SET received_at = line_posted_at ...`、:11 が既にある NEUTRALIZED（ADR-158）のコメント。
- 変更後: :1-5 はそのまま。:6-9 を消し、次に置き換える。:10（空行）と :11 はそのまま残す。
```sql
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): received_at を line_posted_at にそろえる UPDATE を外した。
-- 2026-09-29 の一度きりの直しは終わっている。今はアプリの取り込みが received_at を入れる（backend/app/services/tcg_line_import_svc.py の source_messages への INSERT）。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #43
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: received_at realign removed (20260929_120000)'; END $$;
```

## 新しい試験 `backend/tests/test_value_migrations_neutralized_5_1.py`
`backend/tests/test_value_migrations_neutralized_3c.py` の SQL の部分と同じ形で書く（`_WRITE`・`_strip_sql_comments`・parametrize。Python の部分は要らない）。
- `MARK = "NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15)"`
- `_WRITE` に3c の4つ（INSERT・UPDATE・DELETE・ON CONFLICT）と、`"RAISE EXCEPTION": re.compile(r"\bRAISE\s+EXCEPTION\b", re.IGNORECASE)` を足す。
- `SQL_SPECS`（ファイル → (禁止する種類, 残っているべき文字列)）:

| ファイル | 禁止 | 残る |
|---|---|---|
| `027_backfill_customer_contact_channels.sql` | INSERT, ON CONFLICT | （なし） |
| `054_add_users_theme.sql` | UPDATE | `ADD COLUMN IF NOT EXISTS theme` |
| `098_migrate_customer_discord_to_company_discord.sql` | INSERT, ON CONFLICT, RAISE EXCEPTION | （なし） |
| `20260622_020000_migrate_conv_only_into_meta_messages.sql` | INSERT, ON CONFLICT | （なし） |
| `20260903_120000_tcg_unit_evidence_rules_t004.sql` | INSERT, ON CONFLICT, RAISE EXCEPTION | `CREATE TABLE IF NOT EXISTS %I.tcg_unit_evidence_rules` |
| `20260905_120000_register_15_suppliers_t004.sql` | INSERT, ON CONFLICT | （なし） |
| `20260905_150000_record_manual_supplier_fixes_t004.sql` | INSERT, ON CONFLICT, UPDATE | （なし） |
| `20260929_120000_fix_source_messages_received_at.sql` | UPDATE | （なし） |

- 試験1（parametrize）: 印がファイルにある・コメントを除いた本文に禁止の文が無い・残る文字列が本文にある。
- 試験2: 8本すべてが `scripts/run_all_migrations.sh` に `run_sql migrations/<ファイル>` の行で登録されたまま（登録を外していないことの確かめ）。
- 試験3: `054_add_users_theme.sql` の全文に `@` が無い（メールアドレスが残っていない）。`assert "@" not in text` の形で書き、アドレスそのものを試験に書いて比べない。
- 試験4: `20260905_120000_register_15_suppliers_t004.sql` と `20260905_150000_record_manual_supplier_fixes_t004.sql` の全文に、元のファイルにあった仕入れ先・人の名前が無い。名前そのものを試験に書かず、`re.search(r"name\s*(→|=)\s*'", text) is None` と `re.search(r"SP0\d{3}\s+'", text) is None` と `re.search(r"'SP0\d{3}',\s*'", text) is None` の3つの形で確かめる（元の文の「name → '…'」「SPxxxx '…'」「('SPxxxx', '…'」の形が無いこと。3つ目は #24 の INSERT の値の形。Opus が origin/main で当てて、元の #24 で18行・#25 で3行当たり、残す頭のコメント :1-10 では0行を確かめた）。
- 名前の扱い（全体）: 新しい試験ファイル・commit の文・報告の要約・`git diff` 以外の自分の文章に、利用者のメールアドレスと仕入れ先・人の名前を書かない（`git diff` の全文の `-` の行に出るのは構わない。報告はこのクラウドの実行の中だけに置く。Opus は `git diff` の全文を PR 本文・コメント・リポジトリのファイルに写さない）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-1 の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと `bash scripts/new-worktree.sh release/migration-disable8`（`--claude` なし）。以後の Bash は `cd $HOME/worktrees/salesanchor/release-migration-disable8 && ` で始める。`git log -1 --format=%H` と `git log -1 --format=%H origin/main` を記録し、同じでなければ **停止**。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. 変える前の数（K5-1 の前）: 数える台本を Write で `/tmp/m51/p11count.py` に書き、`python3 -I /tmp/m51/p11count.py > /tmp/m51/before.txt` で流す。台本は前の数え方（`docs/handoff/migration-runner-redesign/recon-5-0a/p11.md:13-14`）と同じにする:
   - 部品は `docs/handoff/migration-runner-redesign/recon-5-0a/p06.md:67-110` の `common.py`（`registered`・`strip_sql_comments`・`read`・`py_sql_names`）をそのまま写す。`ROOT` だけ作業フォルダに変える。
   - 対象: `registered()` の `run_sql` のファイル（名前が同じ物は1つ）と、`run_py` の台本ごとの `py_sql_names()` のうち `run_sql` に無い `migrations/` のファイル。
   - 数える物: `strip_sql_comments()` の後の本文に、`re.match(r'^\s*(INSERT|UPDATE|DELETE|TRUNCATE|MERGE|COPY)\b', 行, re.I)` に当たる行が1つ以上あるファイル。
   - 出す物: 対象の数、数えた本数、`run_sql` の物と `run_py` だけの物の内訳、数えたファイルの名前の一覧（名前順）。
   - 期待: 数えた本数 52（`run_sql` 51 ＋ `run_py` だけの物 1 = `044_create_meta_page_routing_trigger.sql`）。**52 でなければ停止**。
5. 8本を上の「1本ずつの変更」のとおり Edit する。1本ごとに「変更前」の行と中身が合っているか先に Read で確かめる。
6. 新しい試験を Write する。
7. 確かめ（DB 不要の物だけ）:
   - 先に Python 3.12 の専用の環境を作って依存を入れる（クラウドの見張り py312-guard は 3.12 以外の環境作りと、環境の外の `pip install` を止める。`scripts/agent-hooks/cloud/python_version_guard.py`。前例 `docs/handoff/extraction-job-recovery/card-test-clock-fix.md:34-35`）。(a) `command -v uv python3.12` を記録する。(b) uv があれば `uv venv --python 3.12 /tmp/v312` のあと `cd backend && uv pip install --python /tmp/v312/bin/python -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`。uv が無く python3.12 があれば `python3.12 -m venv /tmp/v312` のあと `cd backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`。出力の最後の20行と `exit=` を記録する。(c) どちらも無い・依存が入らないときは、その出力を記録して **停止**（環境を作り直す別の書き方は試さない）。
   - `/tmp/v312/bin/python -m pytest backend/tests/test_value_migrations_neutralized_5_1.py backend/tests/test_value_migrations_neutralized_3c.py -p no:cacheprovider -o addopts="" -q`（`backend/pyproject.toml:65` の既定の `-n auto` とカバー率60%の線を外すため `-o addopts=""` を付ける。全部通る。落ちたら直さずに **停止**）。
   - `python3 scripts/check-migration-value-writes.py repo`（通る）。
   - 4 と同じ台本を流し `/tmp/m51/after.txt` へ。本数を記録する（期待 44。`diff /tmp/m51/before.txt /tmp/m51/after.txt` で、消えた名前がちょうど8本で、増えた名前が0）。**44 でなければ停止**。
   - `git diff --stat` と `git diff` の全文を記録。8本の `-` の行が、上の「変更前」で消すと書いた範囲だけであること。
8. `git add` は上の9本だけ。`git diff --cached --name-only` を記録（9行）。
9. commit（文は Write で `/tmp/m51/commit-msg.txt` に書いて `git commit -F /tmp/m51/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `fix(migrations): neutralize value writes in 8 migrations (ADR-1007 5-1)`。
10. `git push -u origin release/migration-disable8`（force 禁止）。push の出力の全文を記録。**PR は作らない**（Opus が作る）。

## 想定される分かれ道
- 「変更前」の行番号がずれている → 文の一致で探す。中身が違う（行が足されている・消されている）→ **停止**。
- 4 の数が 52 でない → **停止**（誰かが移行を足した・直した。数え直しは Opus がする）。
- 3c の試験が落ちる → 触っていないファイルの試験なので、main 側の変化。**停止**して出力の全文を出す。
- `check-migration-value-writes.py repo` が「一覧に無い値の書き込み」で落ちる → 8本以外のファイルの話。**停止**。8本が原因（文の消し残し）なら直してよい。
- push が見張り（フック）に止められた → 言い換えない。止めた文を全文で報告して **停止**。

## 合否の線
- 合格: 7 の確かめが全部通り、数が 52 → 44、触ったファイルが9本、push 済み。
- 不合格: 上のどれか1つでも違う。

## 出すもの（報告）
- 1 の受領確認、2 の2つの commit、3 の出力、4 の台本の全文、4・7 の数と名前の一覧（before.txt・after.txt の全文と diff）、7 の pytest と検査の出力の全文、`git diff` の全文、8 の9行、push の出力の全文。
- 残りの作業として書くだけの物: `.github/workflows/migration-test.yml` :179・:181・:797・:805 のコメントは、#43 が UPDATE しなくなったので古い（直さない）。
- 最後の行: 合格なら `DONE`、止まったら `BLOCKED: <理由>`。

## この後（Opus がする。カードの範囲外）
- PR 起票（危険な道 `migrations/` を含む。ADR-1003 の除外に当たらない＝下の照合）、合流前の審査役、CI（K5-1b: `.github/workflows/migration-test.yml` の全件のドライランと backend の試験）、PO への3行まとめ（対象・変更内容・バックアップ確認。ADR-1003 の委譲の条件3 `docs/adr/ADR-1003-go-delegation-to-opus.md:25-29`・ADR-136）、委任の GO 記録、合流。
- 本番反映の後の見方（4つを分けて見る）: ①反映が成功した ②移行の段のログに8本の `ADR-1007 neutralized:` の NOTICE が出た（時刻つき） ③控えの段が流れた ④ほかに変わった物が無い（移行の段のログで、8本以外の NOTICE と失敗の行が前の回と同じ形）。

## ADR-1003 の除外の照合（Opus・2026-11-15）
| 除外 | この変更 |
|---|---|
| 表・列を消す移行 | 当たらない（行を外すだけ。DROP を足さない） |
| 大量の削除（TRUNCATE・条件の無い DELETE） | 当たらない（足さない） |
| secrets | 当たらない |
| Ruleset・Branch Protection | 当たらない |
| `workflow-lint.yml` | 当たらない |
| 外部の画面の操作 | 当たらない |
| main/develop への force push | 当たらない |
- 結論: 委任の GO の範囲。`migrations/` を含むので ADR-136 の危険な PR として GO 記録を PR 本文に残す。

## 事実の出どころ（Opus が 2026-11-15 に読んだ物）
- 8本の全文: `origin/main` `2ccb6a94e`。
- 4 の数え方の期待値: Opus が同じ数え方の台本を `2ccb6a94e` で流した結果、対象 410（run_sql 378・run_py だけ 32）、数えた本数 52（run_sql 51・run_py だけ 1）。8本と `044_create_meta_page_routing_trigger.sql` が一覧にある。
- #43 を止めても困らない理由: `backend/app/services/tcg_line_import_svc.py:319` と `:329` で received_at と line_posted_at は同じ値（:300 のコメントも「line_posted_at と同値」）。:414 で line_posted_at を例外の受け皿なしで読むので、同じ文字列の received_at が :445-450 で読めない道は通らない。アプリで source_messages に書くのは :455 の INSERT と :478 の UPDATE（superseded_by と is_active だけ）。ほかに書く物は `backend/tcg_migration/scripts/ingest_to_prod.py`（:216・:228。どこからも呼ばれていない手で流す台本。`git grep` で docs 以外の当たり0件）。
- 【未確認】本番の public.source_messages で received_at と line_posted_at が違う行の数。reader 鍵では権限が無く読めなかった（2026-11-15 11:21:04Z、InsufficientPrivilege）。上のコードの読みで、止めても違う行は増えない。
