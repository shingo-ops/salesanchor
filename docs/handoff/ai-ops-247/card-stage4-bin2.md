<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。このPRに含まれない新しいファイルにはバッククォートを付けない。 -->
# 実装カード 段階4 便2 — 報告を種類ごとに受け、届いたことを出来事の表に 1 行残す（C3-0・C3-1）

> この文書は何か: AI 保守運用 24 時間化 段階4 の 2 便目の段取り表です。相談係の報告を「調べた結果」「直ったかの確かめ」「効果の確かめ」の 3 種類で 1 通ずつ受けられるようにし（C3-1）、報告が届いたら、出来事の表に「届いた」という 1 行を報告の id だけで残します（C3-0）。表の変更があるので、危険便（GO #番号が要る）です。

- 設計: `docs/handoff/ai-ops-247/stage4-design.md` §2「実装カードで足すこと」C3-0・C3-1（:58-62）、§8（:155）、§12 D1・D4（:187・:190）
- 便の分け方: `docs/handoff/ai-ops-247/card-stage4-bin1.md` §0（:11-26）。便1 の K1 は ○（設計 §13）
- 対象ADR: ADR-1012
- 状態: 設計案作成済み。設計審査（クラウド）と PO 承認はまだ。実装は未着手
- 危険便: はい（`migrations/` と `scripts/run_all_migrations.sh` を変える。ADR-135・ADR-136）。下の 2a・2b とも GO #番号が要る
- 実装担当: クラウドの Sonnet（RemoteTrigger の一回実行）。push して止まる。PR は Opus が作る
- 決めること（PO）: §3 の出来事の kind と actor（案 A／案 B）

## 0. 前提の事実（origin/main b1f73d2da で読んだ）

報告の表と口:
- `ops_case.reports` は incident_id に名前の無い一意の決まりを持つ: `incident_id uuid NOT NULL UNIQUE REFERENCES ops_case.cases(incident_id)`（`migrations/20261031_210000_create_ops_case.sql:22-33`）。表の説明は「1 件につき 1 通」（同 :81）。
- 報告の口は `ON CONFLICT (incident_id) DO NOTHING RETURNING id::text` で入れ、行が返らなければ 409 `OPS_CASE_REPORT_EXISTS`（`backend/app/routers/ops_case.py:510-531`）。入れたら commit して `{"id","incident_id"}` を返す（同 :532-540）。
- 本文の形 `ReportBody` は extra="forbid"・status は investigating か reported（`backend/app/routers/ops_case.py:189-198`）。本文は 32KB まで（同 :47）。
- 口の前で、件の札を確かめたあと運用者の旗を立てたまま渡す（`backend/app/routers/ops_case.py:156-174`）。
- 相談係の指示書は「2 回目の報告は 409。409 が返ったら終わる」（`docs/ai-agents/ops-incident-agent.md:69,79`）。

出来事の表:
- `public.ops_incident_events` の kind は 6 つ、actor は 3 つに限られる（`migrations/20261016_100000_create_ops_incident_tables.sql:54-57`）。detail は 8192 バイトまで（同 :58）。
- 読み書きとも運用者の旗が要る（同 :98-103）。アプリのロールは SELECT と INSERT だけ（同 :122-124）。
- 出来事を書く SQL は保守の口に 1 つだけある: `_INSERT_EVENT_SQL`（`backend/app/routers/ops.py:195-198`）。出来事の表に書くコードは今この 1 ファイルだけ（`git grep ops_incident_events -- backend/app` で ops.py 以外 0 件）。
- 伏せた窓のビューでは、kind は「値の決まり ops_incident_events_kind_check で値が限られる」理由で見せ、actor と detail は伏せる（`migrations/20261024_100300_create_ai_cloud_views.sql:164-165`）。決まりの名前を変えなければ、この理由はそのまま正しい。
- 伏せた窓のビューを作る範囲は public と tenant_* だけで、ops_case は入らない（`migrations/20261024_100000_create_ai_cloud_meta.sql:85`）。報告の表に列を足しても、伏せる分類（1151 行）は変わらない。

本番への出し方（ここが便を 2 つに分ける理由）:
- 本番反映では、先に backend を入れ替え（`.github/workflows/deploy.yml:497-498` の blue-green）、そのあとで移行を流す（同 :840-857）。新しいコードが、古い表の上で数分動く。
- 移行は毎回すべてのファイルを流す。各ファイルは psql の 1 回の流しで、`ON_ERROR_STOP=1`・ロック待ち 1 秒・再試行つき（`scripts/run_all_migrations.sh:25,57,110-130`）。1 ファイルをまとめて 1 つの取引にはしない（`-1` が無い）ので、文ごとに確定する。
- PostgreSQL の決まり（Context7 /websites/postgresql、sql-insert「ON CONFLICT Clause」）: `ON CONFLICT (列)` は、その列とちょうど同じ一意の索引を探し、無ければ失敗する。つまり、
  - 古い一意（incident_id だけ）を先に消すと、古いコードの `ON CONFLICT (incident_id)` が失敗し、報告が全部 500 になる。
  - 新しいコード（kind の列を入れる）を先に出すと、列が無い間、報告が全部 500 になる。
- 同じく（sql-altertable「Notes」）: CHECK を `NOT VALID` で足すと表を読まずにすぐ確定し、あとの `VALIDATE CONSTRAINT` は書き込みを止めない弱いロックで済む。

CI:
- 移行の試験は、変えた SQL ファイルを 2 回流して冪等を確かめ（`.github/workflows/migration-test.yml:1437`）、全ファイルを `scripts/run_all_migrations.sh` の run_sql の順で流す（同 :1441-1443）。
- 報告の口の試験は、使い捨て DB に移行ファイルを 1 つずつ名指しで流す（`backend/tests/test_ops_case_router.py:145-159`）。新しいファイルは、ここにも足さないと試験の DB に入らない。

## 1. 便2 を 2a と 2b に分ける

| | 中身 | コード | 古い一意（incident_id だけ） | GO |
|---|---|---|---|---|
| 2a | 表だけ足す: 報告の表に kind の列・新しい一意（incident_id, kind）。出来事の表の kind と actor の決まりを広げる | 変えない | 残す | GO #番号（2a の PR） |
| 2b | 口を変える: 本文に kind・同じ取引で出来事を 1 行。古い一意を消す | 変える | 消す（コードの入れ替えの後） | GO #番号（2b の PR） |

- 2a を出したあと: 古いコードのまま。kind は既定の investigation が入り、`ON CONFLICT (incident_id)` は古い一意で今までどおり動く。報告の数・409 の出方は変わらない。
- 2b を出したあと: 入れ替えから移行までの数分、新しいコードと古い一意が並ぶ。investigation の報告は今までどおり動く。この間に investigation 以外の 2 通目を送ると、古い一意にぶつかって 500 になる。今その種類を送る係はいない（指示書は kind を書かない＝investigation。§0）。移行で古い一意が消えたら、種類ごとに 1 通ずつ受けられる。
- 2b は 2a が本番に出て、§7 の確かめが済んでから始める。

## 2. 範囲

入れる:
- 2a: 移行 1 つと戻し 1 つ、`scripts/run_all_migrations.sh` に 2 行、試験 1 つ
- 2b: `backend/app/routers/ops_case.py` の報告の口、移行 1 つと戻し 1 つ、`scripts/run_all_migrations.sh` に 2 行、試験の追加と直し、`frontend/api-contract/openapi.json` の書き出し、書類の直し（§5-2b-5）

入れない:
- 注記の口（`backend/app/routers/ops.py:411-484`）の kind・round。許可の出来事は便4（C1-1）
- 伏せた窓のビュー・分類（便3 の C3-2）
- 相談係の指示書の送り方（kind を書かない今の送り方のまま。種類を送るのは便5 以降の実行係）
- 報告を出来事の表に写すこと（PO 決定 D4。detail は報告の id だけ）
- 画面・nginx・`deploy.yml`・secret

## 3. 決めること: 報告が届いた出来事の kind と actor

| | 案 A【おすすめ】 | 案 B |
|---|---|---|
| kind | `case_report` を足す | 今の `ai` を使う |
| actor | `case_agent` を足す | 今の `ops_token` を使う |
| 表の決まり | 2 つ広げる（2a で一緒に行う） | 変えない |
| 誰が書いたか | 相談係の鍵で入った口、と正しく残る | 保守の鍵（ops_token）で入ったように残る。実際の鍵（相談係の鍵 `backend/app/routers/ops_case.py:72-73`）と違う |
| 便4 の見分け | kind だけで見分ける。`ai` は今の「回」（round）と便4 の許可のまま | `ai` に「回」・許可・報告の 3 つが混ざり、detail の形で見分ける。detail は伏せた窓では伏せてあり（§0）、窓からは見分けられない |
| 伏せた窓の理由の文 | 決まりの名前が同じなのでそのまま正しい | 変わらない |

案 A を薦める理由: 障害記録の目的は「いつ・誰が・何をしたか」を正しく残すこと。案 B は actor が実際の鍵と食い違い、見分けに伏せた列（detail）を使うことになる。案 A の追加の手間は、2a の移行に決まり 2 つを足すだけで、2a はどのみち表を変える。

以下は案 A で書く。案 B に決まったら、§5 の 2a-（３）（４）を外し、2b の出来事の kind・actor を `ai`・`ops_token` に替え、detail に `{"report_id": …, "type": "case_report"}` を入れて見分けの試験を足す（審査をやり直す）。

## 4. 本番の数（GO の前に Opus が読む）

2a の GO の前に、Opus が本番の読み取りの鍵で次を数え、生の出力を作業用のフォルダに残す（値は読まない。数だけ）:
- `ops_case.reports` の行数、件ごとの最大の通数（1 のはず）
- `public.ops_incident_events` の行数、kind・actor ごとの数（決まりの外が 0 のはず）

読み取りの鍵で ops_case が読めないとき、数が説明できないときは、止めて PO に聞く（推測で GO を出さない）。

## 5. 作り方

ファイルの名前の時刻は、作る時点の `migrations/` で一番新しいものより後ろにする（今の最後は 20261113_100001。`scripts/run_all_migrations.sh:1271-1272`）。下の名前はその例。2b の時刻は 2a より後ろ。

### 5-2a 表だけ足す（ブランチ release/ai-ops-stage4-bin2a）

（１）新しいファイル migrations/20261113_200000_add_ops_case_report_kind.sql（全文）:

```sql
-- ADR-1012 段階4 便2a: 報告を種類（kind）ごとに 1 通にする準備と、報告が届いた出来事の kind・actor を足す。
-- 古い一意（incident_id だけ）は残す（今のコードの ON CONFLICT (incident_id) が使うため。消すのは便2b）。冪等。

-- 1. 報告の種類の列（既存の行は investigation になる）
ALTER TABLE ops_case.reports ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'investigation';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'ops_case.reports'::regclass AND conname = 'reports_kind_check') THEN
        ALTER TABLE ops_case.reports
            ADD CONSTRAINT reports_kind_check CHECK (kind IN ('investigation', 'verification', 'effect'));
    END IF;
END $$;

-- 2. 種類ごとに 1 通の一意
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'ops_case.reports'::regclass AND conname = 'reports_incident_id_kind_key') THEN
        ALTER TABLE ops_case.reports
            ADD CONSTRAINT reports_incident_id_kind_key UNIQUE (incident_id, kind);
    END IF;
END $$;

-- 3. 出来事の kind に case_report を足す（名前は変えない。伏せた窓の分類の理由がこの名前を指すため）
DO $$
DECLARE
    def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.ops_incident_events'::regclass
      AND con.conname = 'ops_incident_events_kind_check';

    IF def IS NULL OR def NOT LIKE '%case_report%' THEN
        ALTER TABLE public.ops_incident_events DROP CONSTRAINT IF EXISTS ops_incident_events_kind_check;
        ALTER TABLE public.ops_incident_events
            ADD CONSTRAINT ops_incident_events_kind_check
            CHECK (kind IN ('notified', 'resolved', 'annotated', 'first_aid', 'ai', 'halt', 'case_report')) NOT VALID;
    END IF;
END $$;
ALTER TABLE public.ops_incident_events VALIDATE CONSTRAINT ops_incident_events_kind_check;

-- 4. 出来事の actor に case_agent を足す
DO $$
DECLARE
    def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.ops_incident_events'::regclass
      AND con.conname = 'ops_incident_events_actor_check';

    IF def IS NULL OR def NOT LIKE '%case_agent%' THEN
        ALTER TABLE public.ops_incident_events DROP CONSTRAINT IF EXISTS ops_incident_events_actor_check;
        ALTER TABLE public.ops_incident_events
            ADD CONSTRAINT ops_incident_events_actor_check
            CHECK (actor IN ('alertmanager', 'ops_token', 'super_admin', 'case_agent')) NOT VALID;
    END IF;
END $$;
ALTER TABLE public.ops_incident_events VALIDATE CONSTRAINT ops_incident_events_actor_check;

COMMENT ON COLUMN ops_case.reports.kind IS '報告の種類。investigation=調べた結果・verification=直ったかの確かめ・effect=効果の確かめ。種類ごとに 1 通';
```

（２）新しいファイル migrations/20261113_200001_add_ops_case_report_kind_down.sql（全文）:

```sql
-- ADR-1012 段階4 便2a の戻し（手動実行のみ・本番デプロイでは実行しない）。便2b を戻した後にだけ流す。
-- 出来事の kind・actor の決まりは戻さない（case_report の行があると狭めると失敗するため。値が 1 つ多く許されるだけで害は無い。前例 migrations/20261113_100001_create_secretary_rules_down.sql）。
BEGIN;
ALTER TABLE ops_case.reports DROP CONSTRAINT IF EXISTS reports_incident_id_kind_key;
ALTER TABLE ops_case.reports DROP CONSTRAINT IF EXISTS reports_kind_check;
ALTER TABLE ops_case.reports DROP COLUMN IF EXISTS kind;
COMMIT;
```

（３）`scripts/run_all_migrations.sh` の最後の行の後ろに 2 行:

```
# ADR-1012 段階4 便2a: 報告の種類の列と種類ごとの一意・出来事の kind case_report と actor case_agent を足す（古い一意は残す・冪等）
run_sql migrations/20261113_200000_add_ops_case_report_kind.sql
# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_200001_add_ops_case_report_kind_down.sql
```

（４）`backend/tests/test_ops_case_router.py` の :159（`20261031_210000_create_ops_case.sql` を流す行）の次に、新しいファイルを流す 1 行を足す。今ある試験は 1 行も変えない（2a の後も古いコードが同じに動くことの確かめになる）。

（５）新しいファイル backend/tests/ops/test_ops_case_report_kind_migration.py。`backend/tests/ops/test_ops_case_db.py` の使い捨て DB の作り方（:44-50・:185）をまねて、次を確かめる:
- 新しいファイルを 2 回流しても失敗しない
- kind を書かずに入れた報告は investigation になる
- 同じ件に investigation の 2 通目は一意で断られる（古い一意でも新しい一意でも断られる）
- kind に決まりの外の値（例 `other`）は断られる
- 出来事の表に kind `case_report`・actor `case_agent` の行が入る。決まりの外（例 `other`）は断られる
- 2 つの決まりが VALID（`pg_constraint.convalidated` が true）
- 古い一意（incident_id だけの一意）がまだある（`contype = 'u'` で列が incident_id だけのものが 1 つ）

### 5-2b 口を変える（ブランチ release/ai-ops-stage4-bin2b。2a が本番に出てから）

（１）`backend/app/routers/ops_case.py` の import に 1 行足す（出来事を書く SQL を 2 つ持たないため。ops.py は ops_case を読み込まないので輪にならない）:

```python
from app.routers.ops import _INSERT_EVENT_SQL
```

（２）`ReportBody`（:189-198）に 1 行足す（status の上）:

```python
    kind: Literal["investigation", "verification", "effect"] = "investigation"
```

（３）`post_report`（:496-540）の書き換え。変更前（:510-531 の SQL と 409 まで）:

```python
                    "INSERT INTO ops_case.reports (incident_id, status, summary, cause, evidence, proposal, risk, "
                    "needs_decision) VALUES (CAST(:iid AS uuid), :status, :summary, :cause, CAST(:evidence AS jsonb), "
                    "CAST(:proposal AS jsonb), :risk, :needs) "
                    "ON CONFLICT (incident_id) DO NOTHING RETURNING id::text"
                ),
                {
                    "iid": incident_id,
                    "status": body.status,
```

変更後:

```python
                    "INSERT INTO ops_case.reports (incident_id, kind, status, summary, cause, evidence, proposal, risk, "
                    "needs_decision) VALUES (CAST(:iid AS uuid), :kind, :status, :summary, :cause, CAST(:evidence AS jsonb), "
                    "CAST(:proposal AS jsonb), :risk, :needs) "
                    "ON CONFLICT (incident_id, kind) DO NOTHING RETURNING id::text"
                ),
                {
                    "iid": incident_id,
                    "kind": body.kind,
                    "status": body.status,
```

409 を投げる行（:530-531）の後ろ、`await db.commit()` の前に足す（同じ取引。出来事が書けなければ報告も残らない）:

```python
        await db.execute(
            _INSERT_EVENT_SQL,
            {
                "incident_id": incident_id,
                "kind": "case_report",
                "actor": "case_agent",
                "detail": json.dumps({"report_id": row[0]}),
            },
        )
```

返す値に kind を足す: `return {"id": row[0], "incident_id": incident_id, "kind": body.kind}`。
docstring を直す: :9 の「報告（1 件 1 通）」→「報告（1 件に種類ごと 1 通）」、:500 の「報告（1 件 1 通。2 回目は 409。…）」→「報告（1 件に種類ごと 1 通。同じ種類の 2 通目は 409。届いたら出来事の表に報告の id だけを 1 行。本文は 32KB まで）。」。ほかの行は変えない。

（４）新しいファイル migrations/20261113_210000_drop_ops_case_report_single_unique.sql（全文）:

```sql
-- ADR-1012 段階4 便2b: 報告の古い一意（incident_id だけ）を消す。名前ではなく中身で探す（作ったときに名前を付けていないため）。冪等。
DO $$
DECLARE
    c TEXT;
BEGIN
    FOR c IN
        SELECT con.conname
        FROM pg_constraint con
        WHERE con.conrelid = 'ops_case.reports'::regclass
          AND con.contype = 'u'
          AND con.conkey = ARRAY[(SELECT a.attnum FROM pg_attribute a
                                  WHERE a.attrelid = 'ops_case.reports'::regclass AND a.attname = 'incident_id')]::int2[]
    LOOP
        EXECUTE format('ALTER TABLE ops_case.reports DROP CONSTRAINT %I', c);
    END LOOP;
END $$;

COMMENT ON TABLE ops_case.reports IS '相談係の報告。1 件につき種類（kind）ごとに 1 通';
```

（５）新しいファイル migrations/20261113_210001_drop_ops_case_report_single_unique_down.sql（全文）:

```sql
-- ADR-1012 段階4 便2b の戻し（手動実行のみ・本番デプロイでは実行しない）。
-- 先に「SELECT count(*) FROM (SELECT incident_id FROM ops_case.reports GROUP BY 1 HAVING count(*) > 1) t」が 0 か確かめる。
-- 0 でなければ流さない（報告は消さない。PO に聞く）。
BEGIN;
ALTER TABLE ops_case.reports ADD CONSTRAINT reports_incident_id_key UNIQUE (incident_id);
COMMENT ON TABLE ops_case.reports IS '相談係の報告。1 件につき 1 通';
COMMIT;
```

（６）`scripts/run_all_migrations.sh` の最後に 2 行（2a の 2 行の後ろ）:

```
# ADR-1012 段階4 便2b: 報告の古い一意（incident_id だけ）を消す（種類ごとに 1 通・冪等）
run_sql migrations/20261113_210000_drop_ops_case_report_single_unique.sql
# ADR-1012 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_210001_drop_ops_case_report_single_unique_down.sql
```

（７）試験:
- `backend/tests/test_ops_case_router.py` の :159 の後ろ（2a で足した行の次）に 2b の新しいファイルを流す 1 行を足す。
- `test_report_once_then_409_and_oversize_413`（:298-312）は名前と中身をそのまま残す（kind を書かない 2 通目は 409・数は 1）。
- 新しい試験を同じファイルに足す:
  - 同じ件に investigation → verification → effect の 3 通が 200、4 通目（effect の 2 通目）が 409、報告は 3 行
  - 報告 1 通ごとに出来事の表に kind `case_report`・actor `case_agent` の行が 1 行増える。409 のときは増えない
  - 出来事の detail は `{"report_id": "<返した id>"}` だけ。キーは report_id の 1 つだけで、summary・cause などの値が入っていない（PO 決定 D4 の見張り）
  - 出来事が書けないとき、口は 503 を返し（`backend/app/routers/ops_case.py:124-127` の `_unavailable`）、報告の行も残らない（同じ取引）。書けない状態の作り方は、試験の DB の中で出来事の表への INSERT の権限を一時的に外すか、出来事の表に一時的な決まりを足すか、のどちらか。どちらもできなければ NEEDS_DECISION で止まる
  - kind に決まりの外の値は 422 で、本文の値が応答に出ない
- 2b の移行ファイルを 2 回流しても失敗しない・古い一意が 0 個・新しい一意が 1 個、を 5-2a（５）の試験ファイルに足す。

（８）`frontend/api-contract/openapi.json` を `backend/tools/export_openapi.py` で書き出し直す（ReportBody に kind が増えるため）。差分が報告の口の本文の kind だけであることを確かめる。

（９）書類の直し（どれも「1 件 1 通」を「種類ごとに 1 通」に合わせるだけ）:
- `docs/ai-agents/ops-incident-agent.md:79`: 「2 回目の報告は 409 で断られます。」の後ろに「（`kind` を書かない報告は「調べた結果」の 1 種類として扱われます）」を足す。:69 の見出し「報告（1 回だけ）」は変えない（相談係の送り方は変えないため）。
- `docs/handoff/cloud-case-ai/design.md:354`: 「二重の報告」→「同じ種類の二重の報告」。
- `docs/handoff/ai-ops-247/stage4-design.md` §13 に便2 の結果の行を足す（Opus が本番の確かめの後に行う。Sonnet は触らない）。

## 6. 想定される分岐（ここに無い分岐は止まって報告）

| 起きたこと | すること |
|---|---|
| 行番号が実物とずれる | 中身で同じ場所を探す。中身も違えば止まる |
| `migrations/` に 20261113_200000 より新しいファイルがある | 名前の時刻をそれより後ろにする（2b は 2a より後ろ）。`scripts/run_all_migrations.sh` の最後の行の後ろに足す |
| `ops_case.reports` に incident_id だけの一意が 1 つでない（0 個・2 個） | 止まる |
| 2a の後、今ある試験（`backend/tests/test_ops_case_router.py`・`backend/tests/test_ops_router.py`・`backend/tests/test_ops_incident_tables_rls.py`・`backend/tests/ops/test_ops_case_db.py`）が 1 つでも赤 | 名前と生の出力を出して止まる（2a は古いコードを変えない約束のため） |
| `from app.routers.ops import _INSERT_EVENT_SQL` で読み込みの輪のエラー | 止まる。SQL を写して 2 つ目を作らない |
| openapi.json の差分が kind 以外にも出る | 止まる。手で書き換えない |
| 伏せた窓の分類の試験（`backend/tests/ops/test_ai_cloud_views.py:486` の 1151）が変わる | 止まる（public に列を足していないはずのため） |
| 移行の 2 回目の流しで失敗 | 止まる |

## 7. 本番での確かめ（Opus。各便の本番反映の後）

2a の後（読み取りの鍵で。値は読まない）:
- `ops_case.reports` に kind の列があり、全行が investigation。行数が §4 の数と同じ
- `reports_kind_check`・`reports_incident_id_kind_key` があり、incident_id だけの一意も残っている
- 出来事の表の 2 つの決まりに case_report・case_agent があり、VALID
- 本番反映の後、報告の口の 5xx が増えていない（反映の前後 1 時間の nginx の数）

2b の後:
- incident_id だけの一意が 0 個、新しい一意が 1 個
- 相談係の次の本物の件で、報告 1 通に対して出来事の表に case_report の行が 1 行、detail のキーが report_id だけ（件が来るまで待つ。来るまでは「未確認」と記録する）
- 本番で試しの報告は送らない（本物の件の記録を汚さないため）。代わりに CI の試験を根拠にする

## 8. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 2a の後も、報告の口の動き（200・2 通目の 409・413・422）が変わらない | 2a の PR の CI で `backend/tests/test_ops_case_router.py` が緑（今ある試験を変えずに） |
| 移行が冪等 | migration-test の 2 回目の流しが緑・新しい試験の 2 回流しが緑 |
| 種類ごとに 1 通ずつ受け、同じ種類の 2 通目は 409 | 2b の新しい試験（3 通 200・4 通目 409・3 行） |
| 報告 1 通ごとに出来事が 1 行、detail は報告の id だけ | 2b の新しい試験（D4 の見張り）。本番は §7 |
| 報告と出来事は一緒に残るか、一緒に残らないか | 2b の新しい試験（出来事が書けないと 503・報告 0 行） |
| 誰が書いたかが正しい（案 A） | 出来事の actor が case_agent（試験と本番の §7） |
| 伏せた窓の分類が変わらない | `backend/tests/ops/test_ai_cloud_views.py` が緑（1151 のまま） |
| 戻し方が書いてあり、流せる | 戻しのファイル 2 つ。§9 |
| 触ったファイルが §2 の範囲だけ | `git diff --name-only origin/main...HEAD` を Opus が読む |

## 9. 戻し方

- 2b を戻す: PR を revert（コードが古い口に戻る）。そのあと、戻しのファイルの冒頭の数え方で 2 通以上の件が 0 なら、2b の戻しを手で流す（古い一意が戻る）。0 でなければ流さず、古いコードのまま（古いコードは `ON CONFLICT (incident_id)` を使うので、古い一意が無いと報告が全部 500 になる）。この場合は revert せず、口を直す前の版を出し直すか PO に聞く。
  - つまり 2b の revert は「2 通以上の件が 0」のときだけ安全。2b の本番反映から、実行係が種類を送り始める（便5）までの間がその期間。
- 2a を戻す: 2b を戻した後にだけ。PR を revert し、2a の戻しを手で流す。出来事の決まりは広げたまま残す（§5-2a（２）の理由）。
- 戻しのファイルを本番で流すのは、PO の許可（危険操作の同意）を得てから。

## 10. 実装を頼む手順（Opus）

（１）この段取り表の審査（クラウド）→ PO の承認（案 A／B の選択を含む）→ 書類の PR を合流。
（２）§4 の本番の数を読む。
（３）2a をクラウドの Sonnet に頼む（このカードの §5-2a・§6 を渡す。preflight → ブランチ → 書く → 試験 → push して止まる）。頼む文は送る前に `scripts/card-lint.sh` で違反 0 にする（この段取り表そのものは頼む文ではないので、この表には流さない。便1 の表 `docs/handoff/ai-ops-247/card-stage4-bin1.md` も同じ扱い）。報告の形: ①preflight ②`git diff --stat origin/main...HEAD` ③試験の生出力 ④HEAD の sha と push の結果。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い>。
（４）Opus が PR を作り（Draft）、審査役 APPROVE・CI 緑・GO 記録（POの委任に基づくClaude Opus発行・GO #番号）→ 合流 → 本番反映 → §7 の 2a の確かめ。
（５）2b を同じ形で頼み、同じ手順で出す → §7 の 2b の確かめ → 設計 §13 に結果を書く。

## 11. 外部・過去事例

- 過去事例（同じリポジトリ）: CHECK を同じ名前のまま広げる冪等の形（`migrations/20261113_100000_create_secretary_rules.sql:106-122`）。戻しで CHECK を狭めない形（`migrations/20261113_100001_create_secretary_rules_down.sql:1-2`）。この便はどちらにも合わせた。
- 外部事例: 「先に表を足し、コードを替え、そのあと古いものを消す」2 段の出し方（expand / contract と呼ばれる）は一般に知られた形だが、数値つきの公開事例は使わない。この便で 2 段にする根拠は、外部事例ではなく、この本番の出し方の順（`.github/workflows/deploy.yml:497-498` と :840-857）と PostgreSQL の決まり（§0）の 2 つ。

## 12. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

- 判定: APPROVE（段取り表として。PO の案の選択と、クラウドの設計審査の後に実装可）。
- 根拠:
  - 本番の出し方（コードが先・移行が後）で、2a の後も 2b の入れ替え中も、今の報告（investigation）が 500 にならない順になっている（§1）。
  - 出来事の detail は報告の id だけで、値を写さない（D4）。試験で見張る（§5-2b（７））。
  - 出来事を書く SQL を写さず、今の 1 つを使う（配線の正本は 1 か所）。
  - 伏せた窓の分類の理由が指す決まりの名前を変えない。
- 残る点:
  - §4 の本番の数はまだ読んでいない（GO の前に読む）。
  - 2b の後、本物の件が来るまで本番での出来事の行は確かめられない（§7。来るまで「未確認」）。
  - 2b の戻しは、種類を送り始めると古い一意に戻せなくなる（§9）。便5 の前に、戻し方を「口を直した版を出す」に切り替える。

## 維持の仕組み

- 守り手: 2b の試験（detail のキーが report_id だけ・出来事と報告が一緒に残る）が CI の必須の backend 試験で毎回走る。決まりの値は表の CHECK で守る。
- 担当: ADR-1012 のテーマとして Opus が持つ。便4（許可の出来事）は、この便の kind（案 A なら case_report）と混ざらないことを試験に足す。
- 見直し: 便5 で実行係が verification・effect を送り始めたら、30 日の記録で種類ごとの数と 409 の数を数える。
