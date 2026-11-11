# 実装カード 便1: 会社と連絡先の状態の表 public.customer_statuses を作る（作るだけ）

- 設計: [design.md](design.md) §3・§7 の1・§8 K12（クラウド審査 8回目 APPROVE・§14）。調査: [recon.md](recon.md)。
- PO の実装承認: 2026-11-12 のセッション冒頭の依頼「PRマージ、デプロイまで完走させてくれ」。本番への反映は「GO #PR番号」が要る（migrations を含むため・ADR-135/136。GO は ADR-1003 の委任で Opus が出す）。
- ブランチ: `origin/main` から `release/status-ssot-bin1` を作って積む。PR は作らない（Opus が作る）。
- 試験は Mac で流さない。CI で確かめる。行番号は origin/main aec493c7f。
- この便ではアプリのコードは変えない。表は作るだけで、どこからも読まれない（§3）。行を入れる文は書かない（4行は後で PO が流す・ADR-1007）。
- 手本: 前の便のカード `docs/handoff/channel-master-shared/card-pr-a.md`（PR #5206）と同じ形。

## やること（この順）

1. 作業場所: `bash scripts/new-worktree.sh release/status-ssot-bin1 --claude` で作る（`git switch -c` は使わない）。最後の claude --print のエラーは無視してよく、worktree ができたかを確かめる。その中で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告に貼る。クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む。[3/3] と [4/4] が OK でなければ BLOCKED:。Bash は毎回 `cd <worktree> && …` の単独の呼び出しで行う。台帳の札はクラウドでは作らない・commit しない（Opus が手元で作る）。Stop の「commit せよ」の促しは、札や作業場所の登録だけが理由なら従わない。
2. 新しい migration `migrations/20261112_120000_create_public_customer_statuses.sql` を作る。中身は下の「migration の中身」を1文字も変えずに使う。
3. `scripts/run_all_migrations.sh` の最後の `run_sql`（今は :1257 `run_sql migrations/20261111_120000_add_codex_secretary_choices.sql`）の後ろに、注釈1行 `# 会社と連絡先の状態 便1: 状態の表 public.customer_statuses を作る（作るだけ・冪等）` と `run_sql migrations/20261112_120000_create_public_customer_statuses.sql` を足す。注釈の書き方（`#` か別の形か）は直前の注釈の行にそろえる。
4. 読み取り専用の窓の列の分類: `migrations/20261024_100300_create_ai_cloud_views.sql` の `('public','countries',ARRAY['name'],...)` の行（今は :78）の次に、次の3行を足す（`countries` の次・`data_access_events` の前＝名前の順）。
   ```
     ('public','customer_statuses',ARRAY['code'],'allow','共用マスタ（運営が入れる一覧）。会社・連絡先の状態の記号（tenant 側の status 列が外部キーで指す）'),
     ('public','customer_statuses',ARRAY['name_en'],'allow','【名前を含む】共用マスタ（運営が入れる一覧）。状態の英語名'),
     ('public','customer_statuses',ARRAY['name_ja'],'allow','【名前を含む】共用マスタ（運営が入れる一覧）。状態の日本語名'),
   ```
   ほかの列（sort_order・is_active・selectable_on_create・created_at・updated_at）は数・真偽・日時の型で、名前の見張り（`backend/tests/ops/test_ai_cloud_views.py:44-47` の `_NAME_RE`）にも当たらないので行を足さない。
   分類の行を足すと、次の3か所も一緒に直す（手本 card-pr-a のやること4 と同じ直し方）:
   - 同じファイル 3 行目の `1083 行` を `1086 行` にする。
   - `backend/tests/ops/test_ai_cloud_views.py:484` の `== n0 == 1083` を `== n0 == 1086` にする（1 か所）。
   - `scripts/migration-guard/reference-allowlist.tsv:7`（`migrations/20261024_100300_create_ai_cloud_views.sql` の行）だけを直す。2 列目の sha256 を、分類の行を足した後の `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値にする。4 列目の末尾に ` / status-ssot-contact-company card-bin1（分類3行追加）` を足す。ほかの列は変えない。区切りはタブのまま。
   確かめ: `grep -c "('public','customer_statuses'" migrations/20261024_100300_create_ai_cloud_views.sql` が 3。sha256sum と allowlist の 2 列目（`cut -f2`）が同じ。
5. `.github/workflows/migration-guard.yml:228` の `PUBLIC_TABLES="..."` の閉じる `"` の直前（今の末尾は `staff_join_invites`）に、半角空白区切りで ` customer_statuses` を足す。ほかの行・ほかの語は変えない（手本 card-pr-a の改訂1。便2 の外部キーの参照先がこの一覧に無いと CI のチェック4が止まる）。
6. 提出前: `bash scripts/dev/check-before-submit.sh` を流し、生の結果をファイルに残してパスを報告する。
7. commit（1つでよい。題は `feat(db): 会社と連絡先の状態の表 public.customer_statuses を作る（便1・作るだけ）`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ `git push -u origin release/status-ssot-bin1`。

## migration の中身

```sql
-- 会社と連絡先の状態 便1: 状態の表 public.customer_statuses を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/status-ssot-contact-company/design.md §3
-- 会社（companies）と連絡先（contacts）の status に入る4つの記号・日英の名前・並び順の正本。会社ごとの独自の状態は持たない（tenant_id 列なし）。
-- RLS: 読むのは誰でも全行（USING (true)）。便2 の外部キーの VALIDATE が FORCE の下で行を絞られないため（design.md §3）。書くのは運営だけ。
-- 行を入れる文は書かない（4行は別のデータ変更で PO が流す・ADR-1007）。この便では作るだけで、どこからも読まれない。
--
-- ロールバック: 表は残してプログラムが使わない（表を消すのは別便・PO GO）。

BEGIN;

CREATE TABLE IF NOT EXISTS public.customer_statuses (
    code                 VARCHAR(20) PRIMARY KEY,
    name_ja              VARCHAR(50) NOT NULL,
    name_en              VARCHAR(50) NOT NULL,
    sort_order           SMALLINT    NOT NULL UNIQUE,
    is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
    selectable_on_create BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.customer_statuses IS '会社と連絡先の状態の正本。記号・日英の名前・並び順。運営だけが書く';
COMMENT ON COLUMN public.customer_statuses.code IS '会社・連絡先の status 列に入る記号（変えない）';
COMMENT ON COLUMN public.customer_statuses.name_ja IS '画面に出す日本語の名前';
COMMENT ON COLUMN public.customer_statuses.name_en IS '画面に出す英語の名前';
COMMENT ON COLUMN public.customer_statuses.sort_order IS '選択肢と集計の並び順（小さい順）';
COMMENT ON COLUMN public.customer_statuses.is_active IS 'FALSE＝新しく選べない（過去の行は残る）。消す代わりに使う';
COMMENT ON COLUMN public.customer_statuses.selectable_on_create IS 'FALSE＝作る画面の選択肢に出さない（直す画面には出す）';
COMMENT ON COLUMN public.customer_statuses.created_at IS '作った時刻';
COMMENT ON COLUMN public.customer_statuses.updated_at IS '直した時刻';

ALTER TABLE public.customer_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_statuses FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_statuses_select ON public.customer_statuses;
CREATE POLICY customer_statuses_select ON public.customer_statuses FOR SELECT
  USING (true);

DROP POLICY IF EXISTS customer_statuses_insert ON public.customer_statuses;
CREATE POLICY customer_statuses_insert ON public.customer_statuses FOR INSERT
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS customer_statuses_update ON public.customer_statuses;
CREATE POLICY customer_statuses_update ON public.customer_statuses FOR UPDATE
  USING (current_setting('app.is_operator', true) = 'true')
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS customer_statuses_delete ON public.customer_statuses;
CREATE POLICY customer_statuses_delete ON public.customer_statuses FOR DELETE
  USING (current_setting('app.is_operator', true) = 'true');

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT ON public.customer_statuses TO salesanchor_app;
    END IF;
END $$;

COMMIT;
```

- アプリの役（salesanchor_app）には読む権限だけを付ける。書くのは運営の手作業（PO の `!`）だけなので、書く権限は付けない（ADR-1007）。

## 触らない

- `backend/`（`backend/tests/ops/test_ai_cloud_views.py:484` の数の1か所を除く）・`frontend/`・`.github/`（やること5の1か所を除く）・`deploy.yml`・`docs/`（全部。ADR と4行の SQL ファイルは Opus が同じ枝に足す）。
- 既存の migration（`migrations/20261024_100300_create_ai_cloud_views.sql` のやること4の3行と3行目の数を除く）・`backend/app/services/tenant.py`（便2 で直す）。
- `scripts/migration-guard/protected-tables.txt`（便3 で足す・design.md §3 の最後から2つ目の項）。
- 行を入れる文（INSERT・UPDATE）を migration に書かない。

## 想定される分かれ道

- 行番号がずれている（本線が進んだ）→ 文字で場所を探す。中身が設計と違えば止めて `NEEDS_DECISION:` で報告する。
- 3 行目が `1083 行` でない・:484 が 1083 でない → 今の数に 3 を足した数にし、元の数を報告に書く。
- `run_all_migrations.sh` の最後の `run_sql` が `20261111_120000` でない → 今の最後の `run_sql` の後ろに足し、そのファイル名を報告に書く。
- `check-before-submit.sh` の値の書き込みの検査（migration-value-writes）が、この migration を止める → 直さずに止めて、生の結果を付けて報告する。
- 見張りに止められた → 言い換えずに `BLOCKED:` で止める。
- 変更ファイルは 6 つ（新しい migration・run_all_migrations.sh・create_ai_cloud_views.sql・test_ai_cloud_views.py・reference-allowlist.tsv・migration-guard.yml）。違えば報告に理由を書く。

## 終わりの報告

- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 問い`。HEAD の sha・変更ファイル一覧（`git diff --name-only origin/main...HEAD`）・各検査の終了コードを付ける。
