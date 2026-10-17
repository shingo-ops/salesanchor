# design: 商品の荷姿の表（ADR-1028）

- 現在地: [recon.md](./recon.md)／決定: [ADR-1028](../../adr/ADR-1028-product-packaging-table.md)
- PO の言葉（2026-10-17 チャット）: 入数・重さは別の表で持つ「y」／実測も出典つきで可「y」／出典の決まり（ボックス重さは公式通販のページ優先、公式店は出典1つで採用、ほかのサイトは2つ以上一致、カートンとパックの重さは実測）「y」。同日の指示「配線と DB の SSOT は遵守してデータを分散させることは禁止」
- 便の区分: 便1・便2・便3 は危険 PR（migrations を含む）または本番データ変更で、GO は委任に基づく Opus 発行。便5 は DROP を含むので PO 本人の「GO #PR番号」

## 1. 目的（PO に見える変化）
- 商品ごとに「1ケースに何箱・1箱に何パック・1パックに何枚」と「ケース・箱・パック1つの重さ」を、出典（公式・公式通販・販売サイト・実測・古い値）と一緒に1か所で持つ。
- 商品の編集画面で、入数と重さの横に出典が見える・入れられる。
- 見積・請求の重さ、在庫検索の重さは今と同じ値が出る（読む場所が新しい表に変わるだけ）。

## 2. 対象と対象外
| 対象 | 対象外（触らない） |
|---|---|
| 新しい表 public.product_packagings（便1） | products.moq・weight・volume_weight（荷姿ではない。ADR-1028「守ること」） |
| quantity_units に CARD を1行足す（便2・データ変更） | product_lines（商品の系統）と products.product_line_id |
| products の4列の値を新しい表へ写す（便2・データ変更） | weight_classes の表と管理画面（0件。重さの帯の別の話） |
| 4列を読む所の切り替え（便3 API・在庫検索・取り込み、便4 画面） | product_line_available_units（系統→使える単位。そのまま使う） |
| 古い4列・quantity_unit_id・weight_class_id・product_quantity_units・quantity_units.value を消す（便5） | 外部サイトから値を集めて入れること（便6。候補一覧を PO に見せてから） |

## 3. 表の形（便1）
### 3-1. 新規 migrations/20261018_100000_create_product_packagings.sql
```sql
-- ADR-1028 便1: 商品の荷姿（単位ごとの入数・重さ・出典）。空の表を作るだけ。値は書かない（ADR-155・ADR-1007）。冪等。
-- ロールバック: DROP TABLE IF EXISTS public.product_packagings;

CREATE TABLE IF NOT EXISTS public.product_packagings (
    id                 SERIAL       PRIMARY KEY,
    product_id         INTEGER      NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    unit_id            INTEGER      NOT NULL REFERENCES public.quantity_units(id),
    contained_unit_id  INTEGER               REFERENCES public.quantity_units(id),
    contained_count    INTEGER,
    count_source       TEXT,
    count_source_urls  TEXT[]       NOT NULL DEFAULT '{}',
    weight_kg          NUMERIC(8,3),
    weight_source      TEXT,
    weight_source_urls TEXT[]       NOT NULL DEFAULT '{}',
    note               TEXT,
    updated_by         TEXT,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT product_packagings_product_unit_key UNIQUE (product_id, unit_id),
    CONSTRAINT product_packagings_not_self_check
        CHECK (contained_unit_id IS NULL OR contained_unit_id <> unit_id),
    CONSTRAINT product_packagings_count_pair_check
        CHECK ((contained_unit_id IS NULL) = (contained_count IS NULL)),
    CONSTRAINT product_packagings_count_positive_check
        CHECK (contained_count IS NULL OR contained_count > 0),
    CONSTRAINT product_packagings_weight_positive_check
        CHECK (weight_kg IS NULL OR weight_kg > 0),
    CONSTRAINT product_packagings_not_empty_check
        CHECK (contained_count IS NOT NULL OR weight_kg IS NOT NULL),
    CONSTRAINT product_packagings_count_source_check
        CHECK ((contained_count IS NULL) = (count_source IS NULL)
            AND (count_source IS NULL OR count_source IN ('official', 'official_store', 'retailer', 'measured', 'legacy'))),
    CONSTRAINT product_packagings_weight_source_check
        CHECK ((weight_kg IS NULL) = (weight_source IS NULL)
            AND (weight_source IS NULL OR weight_source IN ('official', 'official_store', 'retailer', 'measured', 'legacy'))),
    CONSTRAINT product_packagings_count_urls_check
        CHECK (array_position(count_source_urls, NULL) IS NULL AND (count_source IS NULL
            OR (count_source IN ('official', 'official_store') AND cardinality(count_source_urls) >= 1)
            OR (count_source = 'retailer' AND cardinality(count_source_urls) >= 2)
            OR count_source IN ('measured', 'legacy'))),
    CONSTRAINT product_packagings_weight_urls_check
        CHECK (array_position(weight_source_urls, NULL) IS NULL AND (weight_source IS NULL
            OR (weight_source IN ('official', 'official_store') AND cardinality(weight_source_urls) >= 1)
            OR (weight_source = 'retailer' AND cardinality(weight_source_urls) >= 2)
            OR weight_source IN ('measured', 'legacy'))),
    CONSTRAINT product_packagings_note_size_check
        CHECK (note IS NULL OR char_length(note) <= 1000)
);

-- 商品ごとの検索は UNIQUE (product_id, unit_id) の索引が使えるので、別の索引は作らない

CREATE OR REPLACE FUNCTION public.set_updated_at_product_packagings()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_packagings_updated_at ON public.product_packagings;
CREATE TRIGGER trg_product_packagings_updated_at BEFORE UPDATE ON public.product_packagings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_packagings();

COMMENT ON TABLE public.product_packagings IS
    'ADR-1028: 商品の荷姿。1行=商品×単位。中に入る単位と数、その単位1つの重さ、それぞれの出典。入数・重さの正本';
COMMENT ON COLUMN public.product_packagings.count_source IS
    'official=公式サイト / official_store=公式通販 / retailer=販売サイト(URL2つ以上の一致) / measured=実測 / legacy=旧列から写した値';

ALTER TABLE public.product_packagings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_packagings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_packagings_read ON public.product_packagings;
CREATE POLICY product_packagings_read ON public.product_packagings
    FOR SELECT
    USING (true);

DROP POLICY IF EXISTS product_packagings_write ON public.product_packagings;
CREATE POLICY product_packagings_write ON public.product_packagings
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
```
- RLS は前例 migrations/20261016_190000_create_product_blank_confirmations.sql と同じ形（共用商品の付属の表。読むのは誰でも、書くのは運営だけ）。
- 重さの型は古い列と同じ NUMERIC(8,3)（migrations/082_extend_products_box_attributes.sql の先頭コメント:16-17 の列一覧と、同ファイルの ADD COLUMN 文）。写しても桁が落ちない。
- updated_at を直すトリガは前例 migrations/20260920_130000_create_product_classification.sql:36-44（product_lines）と同じ形。ただし `CREATE TRIGGER … BEFORE UPDATE ON public.product_packagings` は1行に書く。表の名前を含む行は1行ずつ migration-guard チェック8 に照合され（scripts/check-migration-value-writes.py:35-37,138）、`BEFORE UPDATE ON …` だけの行は落ちるため（審査で再現・2026-10-17）。
- 出典の制約（count_source_check・weight_source_check）は「値が有る⇔出典が有る」を `=` で比べる。`IN (...)` だけだと出典が NULL のとき CHECK が NULL＝合格になり、出典なしの値が入ってしまう（審査で一時 DB で再現・2026-10-17）。

### 3-2. scripts/run_all_migrations.sh
末尾（`run_sql migrations/20261017_210000_drop_products_type_master_id.sql` の後。便1 の実装時に main の末尾を確かめ、違えば止める）に追加:
```bash
# ADR-1028 便1: 商品の荷姿の表（空・構造のみ・冪等）
run_sql migrations/20261018_100000_create_product_packagings.sql
```

### 3-3. scripts/migration-guard/protected-tables.txt
`product_blank_confirmations` の次の行に `product_packagings` を足す（migration で値を書かない表として守る）。

.github/workflows/migration-guard.yml の PUBLIC_TABLES は、他の表がこの表を参照するときだけ必要なので、この便では変えない（products と quantity_units は既に載っている・migration-guard.yml:224）。

### 3-4. .github/workflows/migration-test.yml（CI の前提の表）
CI「マイグレーションSQL 実行（内部）」は、変えた migration だけを前提の表を用意した空の DB に流す（.github/workflows/migration-test.yml:1074-1093）。この前提に quantity_units が無いので、§3-1 は「quantity_units が無い」で落ちる（審査で一時 DB で再現）。前例と同じ書き方で、public.product_lines の最小定義（`CREATE TABLE IF NOT EXISTS public.product_lines (` の文、同:652-661）の直後に足す:
```sql
          -- public.quantity_units: 20260921_140000_product_classification_masters.sql で本番作成済み。
          --   20261018_100000_create_product_packagings.sql が REFERENCES public.quantity_units(id) を
          --   使用するため、前提として最小定義を登録する（value は本番と同じく NULL 可）。
          CREATE TABLE IF NOT EXISTS public.quantity_units (
              id            SERIAL PRIMARY KEY,
              code          VARCHAR(50)  NOT NULL UNIQUE,
              name          VARCHAR(100) NOT NULL,
              name_en       VARCHAR(100),
              value         INTEGER,
              display_order INTEGER      NOT NULL DEFAULT 100,
              is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
              created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
              updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
          );
```
- 字下げは周りの行（10 文字）に合わせる。同じファイルの「現在登録済みのテーブル」の一覧（.github/workflows/migration-test.yml:163-178 付近）に `※ public.quantity_units は 20260921_140000 で本番作成済み（最小定義を登録）` の1行を足す。この workflow は .github/workflows/workflow-lint.yml ではないので、不可逆操作の一覧には当たらない。
- 実装時に、この前提の中で public.products が作られていることを確かめる（作られていなければ止めて報告）。

## 4. 値を写す（便2・1回だけのデータ変更。ADR-1007）
便1 のデプロイ後に、docs/handoff/product-packaging/data-change-1/ に SQL と記録を残して行う。読み取りで数を数え（DRY-RUN）、BEGIN…ROLLBACK で件数を確かめてから COMMIT する。

### 4-1. CARD を名簿に足す
```sql
INSERT INTO public.quantity_units (code, name, name_en, display_order, is_active)
SELECT 'CARD', 'カード', 'Card', 40, true
WHERE NOT EXISTS (SELECT 1 FROM public.quantity_units WHERE code = 'CARD');
```
- display_order は既存3行が 10・20・30（recon の a2.txt）なので 40。実施時に読み直して、違えば止めて Opus に報告する。
- value は NULL（便5 で列ごと消す。NOT NULL 制約は migrations/20260922_060000_product_unit_condition_infra.sql:104 で外れている）。

### 4-2. 古い列から写す
```sql
-- CASE の行（中は BOX）: boxes_per_case か case_weight_kg が有る商品。DRY-RUN の想定 146 行
INSERT INTO public.product_packagings
    (product_id, unit_id, contained_unit_id, contained_count, count_source, weight_kg, weight_source, updated_by)
SELECT p.id, uc.id,
       CASE WHEN p.boxes_per_case IS NOT NULL THEN ub.id END,
       p.boxes_per_case,
       CASE WHEN p.boxes_per_case IS NOT NULL THEN 'legacy' END,
       p.case_weight_kg,
       CASE WHEN p.case_weight_kg IS NOT NULL THEN 'legacy' END,
       'ADR-1028 data-change-1'
FROM public.products p
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'CASE') uc
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'BOX') ub
WHERE p.boxes_per_case IS NOT NULL OR p.case_weight_kg IS NOT NULL
ON CONFLICT (product_id, unit_id) DO NOTHING;

-- BOX の行（中は PACK）: packs_per_box か box_weight_kg が有る商品。DRY-RUN の想定 176 行
INSERT INTO public.product_packagings
    (product_id, unit_id, contained_unit_id, contained_count, count_source, weight_kg, weight_source, updated_by)
SELECT p.id, ub.id,
       CASE WHEN p.packs_per_box IS NOT NULL THEN up.id END,
       p.packs_per_box,
       CASE WHEN p.packs_per_box IS NOT NULL THEN 'legacy' END,
       p.box_weight_kg,
       CASE WHEN p.box_weight_kg IS NOT NULL THEN 'legacy' END,
       'ADR-1028 data-change-1'
FROM public.products p
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'BOX') ub
CROSS JOIN (SELECT id FROM public.quantity_units WHERE code = 'PACK') up
WHERE p.packs_per_box IS NOT NULL OR p.box_weight_kg IS NOT NULL
ON CONFLICT (product_id, unit_id) DO NOTHING;
```
- 想定の行数 146・176 は recon.md §1 の組み合わせ（b5.txt）から数えた。実施時の DRY-RUN の数と違えば止めて Opus に報告する（値が変わった可能性）。
- 0 以下の値があると CHECK で失敗する。DRY-RUN で `<= 0` の件数を先に数え、1 件でもあれば止めて報告する。
- 書く権限: 本番データ変更の道（manual-only 鍵・PO 委任済み）で、`SET LOCAL app.is_operator = 'true'` を同じトランザクションで張る。

### 4-3. 照合（写した後）
- 4列それぞれで「products の値」と「表から組み立てた値」が全行一致する（不一致 0 件）ことを読み取りの道で確かめる。読み取りの道ではビュー名を ai_ro.public__products・ai_ro.public__product_packagings・ai_ro.public__quantity_units に読み替える。
```sql
WITH r AS (
 SELECT p.id, p.boxes_per_case, p.case_weight_kg, p.packs_per_box, p.box_weight_kg,
   (SELECT x.contained_count FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'CASE') AS r_bpc,
   (SELECT x.weight_kg       FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'CASE') AS r_cwk,
   (SELECT x.contained_count FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'BOX')  AS r_ppb,
   (SELECT x.weight_kg       FROM public.product_packagings x JOIN public.quantity_units u ON u.id = x.unit_id WHERE x.product_id = p.id AND u.code = 'BOX')  AS r_bwk
 FROM public.products p)
SELECT count(*) FILTER (WHERE boxes_per_case IS DISTINCT FROM r_bpc) AS bpc_mis,
       count(*) FILTER (WHERE case_weight_kg IS DISTINCT FROM r_cwk) AS cwk_mis,
       count(*) FILTER (WHERE packs_per_box  IS DISTINCT FROM r_ppb) AS ppb_mis,
       count(*) FILTER (WHERE box_weight_kg  IS DISTINCT FROM r_bwk) AS bwk_mis
FROM r;
```
- 合格: 4つとも 0（審査の一時 DB で同じ組み合わせ 1424 行を再現し 0/0/0/0）。

## 5. 読む所の切り替え（便3・便4）と古い列の削除（便5）
この便は方針だけを決める。各便の実装カード（ファイル:行・変更前後・触らない範囲）は、その便を始める前にこの文書へ追記し、Opus 審査を通してから Sonnet に渡す。

- **便3（backend）**: 商品 API・在庫検索・取り込みスクリプトが、4列の代わりに新しい表を読み書きする。
  - API の応答の項目名（boxes_per_case・packs_per_box・box_weight_kg・case_weight_kg）は変えず、新しい表から組み立てて返す（画面と見積の作りを便4まで変えずに済む）。加えて `packagings`（単位ごとの行と出典）を返す。
  - 保存は新しい表へ書く。古い4列には書かない。updated_at はトリガが入れ、updated_by は保存した人を入れる。
  - backend/app/schemas/product.py:68-71・:116-119 は入数・重さが `ge=0`（0 を許す）。新しい表は 0 を拒むので、便3 で `gt=0` に変え、0 を送ると 422 になるようにする（DB エラーの 500 にしない）。
  - 読む所: recon.md §3 の backend とスクリプトの全行。テストも同じ便で直す。
- **便4（画面）**: 商品の編集画面に荷姿の欄（単位ごとの入数・重さ・出典の種類・URL）を出す。入力欄は components/ の金型を使い、文字は t("key") 経由（ADR-027・ADR-144）。販売サイトの URL は同じものを2つ入れられないようにする（DB の制約では同じ URL の重複を止められないため。便3 の API でも重複を 422 で拒む）。見積・請求の重さは便3の応答で今のまま動く。
- **便5（削除・PO 本人 GO）**: 4列・quantity_unit_id・weight_class_id を products から、product_quantity_units を表ごと、quantity_units から value を消す。消す前に値を CSV に退避する。参照の確認をしている backend/app/routers/super_admin_quantity_units.py:170 と backend/app/routers/super_admin_weight_classes.py:140 も同じ便で直す。列を足している migration の ADD 文を同じ PR で消す（ADR-1026 と同じ。列番号の上限のため）。
- **便6（値の追加）**: 外部の出典（recon.md §5）で集めた値を、商品ごとの候補一覧にして PO に見せ、y を受けてから画面か1回だけのデータ変更で入れる。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 便1 の CI がすべて緑（migration-guard を含む） | `gh pr checks <PR>` で fail 0・pending 0 |
| K2 便1 デプロイ後、本番に表 product_packagings が有り、0 行、名前つきの CHECK 制約 10 個（product_packagings_*_check）・UNIQUE 1・外部キー 3・RLS 有効（FORCE 含む） | 読み取りの道で ai_ro.public__product_packagings の count(*)＝0。制約と RLS は pg_constraint・pg_class（relrowsecurity・relforcerowsecurity）を読む。読み取りの道でカタログが読めなければ「未確認」として記録し、manual-only 鍵では読まない（本番 DB の読み取りは reader 鍵の道だけ） |
| K3 便2 後、表の行数＝CASE 146＋BOX 176＝322（実施時の DRY-RUN の数と一致） | 読み取りの道で単位ごとの count(*) |
| K4 便2 後、4列の値と表から組み立てた値の不一致が 0 件 | §4-3 の照合 SQL の結果 |
| K5 便2 後、quantity_units に CARD が1行、既存3行は変わらない | 読み取りの道で全行を読み、前の a2.txt と並べる |
| K6 便3 後、商品 API の4項目の値が便3 前と全商品で同じ | 便3 の直前に §4-3 の照合 SQL で不一致 0 を確かめ、便3 の本番反映後に共用の全商品の API 応答（GET /api/v1/products の4項目）を保存し、便3 前の products の4列（読み取りの道）と id ごとに突き合わせて不一致 0 |
| K7 便3 後、見積・請求で箱とケースを選ぶと今と同じ重さが入る | quoteDraft.test.ts と画面で、box_weight_kg の有る商品1つを選んで確かめる |
| K8 便5 後、products に4列・quantity_unit_id・weight_class_id が無く、product_quantity_units が無い。デプロイが成功し、次のデプロイも成功 | 本番カタログを読む・`gh run view` |
| K9 リポジトリで入数・重さを products の古い4列から読み書きする SQL・ORM が 0 件（便5 後） | `git grep -n -E "p(roducts)?\\.(packs_per_box|boxes_per_case|box_weight_kg|case_weight_kg)" -- backend scripts` が 0 行。応答の項目名として残る所（schemas と frontend）は便3 の実装カードに file:line の一覧で書き、その一覧と `git grep -n -E "packs_per_box|boxes_per_case|box_weight_kg|case_weight_kg" -- backend frontend/src scripts` の結果が一致すること |

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| 写した後に誰かが古い列を画面で直し、表とずれる（便2〜便3 の間） | 便2 と便3 の間を空けない。便3 の直前に §4-3 の照合をもう一度流し、ずれがあれば写し直す |
| 列を消した後に読む所が残っていて壊れる | 便5 の前に K9 を合格にする。便5 は便3・便4 の本番反映と K6・K7 の後 |
| 消した列は二度と足せない | 便5 の直前に CSV に退避。表に全部写っていることを K4 で確かめてから消す |
| 外部の値の信頼度の取り違え | 出典の種類と URL を表に必ず持たせ、販売サイトは URL 2 つ以上を制約で強制 |
| 便3〜便5 の間、products の古い4列が古い値のまま残り、リポジトリ外の GAS（recon.md §3 未確認）や ai_ro の利用者が古い値を読む | 便3 の前にリポジトリ外 GAS の参照を調べる（読んでいれば便3 の対象に足す）。便3 と便5 の間を空けない |
| 公式通販の「重量」が外箱込みかどうか分からない（recon.md §5 未確認） | 値を入れるときは note にページの書き方をそのまま写す。分かった時点で決まりを足す |

戻し方: 便1 は空の表なので DROP TABLE で戻る。便2 は updated_by='ADR-1028 data-change-1' の行を消せば戻る（古い列は残っている）。便3・便4 は PR を戻す（古い列が残っている間は値が戻る）。便5 は戻せない（列番号の上限）ので、退避 CSV から値を読む。

## 8. 維持の仕組み
- 守り手: 表の CHECK 制約（出典なしの値・販売サイトの URL 1 つだけ・URL の空欄・0 以下の値を DB が拒む）と、scripts/migration-guard/protected-tables.txt（migration で値を書かせない）
- 入数・重さの正本はこの表だけ。新しい単位（例: 新しい箱の形）は quantity_units の管理画面で足し、列は足さない。
- 便5 の後は、古い列の名前は API の応答の項目名としてだけ残る（K9）。

## 9. 外部・過去事例の参照と我々への応用
- 過去事例: ADR-1026（products の列を消した。列番号の上限 1600 のため、消す migration と足す migration の ADD 文を同じ PR で直した）→ 便5 で同じ手順を使う。
- 過去事例: migrations/20261016_190000_create_product_blank_confirmations.sql（共用商品の付属の表の RLS）→ 便1 の RLS の形をそのまま使う。
- 外部事例: 使わない（recon.md「外部事例」。表の形は自社 DB の実測で決まる）。

## 10. 実装カード（便1・Sonnet）
- ブランチ: release/product-packaging-table（`bash scripts/new-worktree.sh release/product-packaging-table --claude`）。最初に `./scripts/dev/executor-preflight.sh || exit 1`
- 触るファイル: migrations/20261018_100000_create_product_packagings.sql（新規）、scripts/run_all_migrations.sh、scripts/migration-guard/protected-tables.txt、.github/workflows/migration-test.yml。これ以外は触らない。
- 内容は §3-1〜3-4 のとおり。SQL の文言を変えない。
- 点検（生出力を /tmp/CC報告ファイル/product-packaging/bin1/ へ。作業場所で、commit 後に流す）:
  - `python3 scripts/check-migration-value-writes.py diff origin/main HEAD --check all`
  - `python3 scripts/check-migration-value-writes.py repo`
  - `bash scripts/check-migration-registration-exists.sh --mode host --repo-root "$PWD"`
  - `bash scripts/check-migration-duplicate-registration.sh`
  - `node scripts/check-migration-column-churn.js`（.github/workflows/migration-guard.yml の Check 10 と同じ引数で。引数は同ファイルの該当の run を読んで写す）
  - ローカルの PostgreSQL 16 があれば、空の DB に products と §3-4 の quantity_units の最小の表を作って §3-1 の SQL を2回流し、2回目もエラーが無い（冪等）ことと、次の6つが拒まれることを確かめる: 出典なしの入数／出典なしの重さ／retailer で URL 1 つ／URL 配列に NULL／contained_count 0／中の単位と外の単位が同じ。PostgreSQL が無ければ「未実施」と報告する（止めない）。
- 想定分岐: run_all_migrations.sh の末尾が §3-2 の想定と違う／protected-tables.txt に product_blank_confirmations の行が無い／migration-test.yml に product_lines の最小定義が無い・前提に public.products が無い／点検が失敗した → 直さずに止めて報告。
- commit は1つ（`feat: 商品の荷姿の表を作る（ADR-1028 便1）`）。push まで。PR は作らない（Opus が作る）。
- 報告: DONE/BLOCKED:/NEEDS_DECISION: で始め、HEAD・変更ファイル・点検の生出力のパス。

## 11. 実装カード（便3・Sonnet）
PO 2026-10-18 チャット「y」（便3 のカード→審査→実装→マージ→本番まで）。現在地の生出力は /tmp/CC報告ファイル/product-packaging/bin3/（recon/・recon/extra/・recon/prod/）。行番号は origin/main 88391573c 時点。

### 11-1. 着手前に分かった事実（本番・読み取りの道）
- 照合のやり直し（2026-10-17T16:28Z、data-change-1/02_verify_read.sql）: K3 CASE 146・BOX 176・計 322／K4 0|0|0|0／K5 4 行で便2 直後と同じ（recheck_k3k5.out）。
- 本番の products は 1424 行すべて共用（tenant_id NULL）。テナントの商品は 0 行。古い4列に値がある商品 176、表の行が付いたテナント商品 0（recon/prod/q1.out）。
- 商品 API（POST/PATCH /products）で作った・直した記録は各テナントの audit_logs に 0 件（record_audit_log は tenant_NNN.audit_logs に書く: backend/app/services/audit.py:303。recon/prod/q4.out）。アプリは salesanchor_app で接続し RLS が効く（docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:16）。共用行の書き込みは app.is_operator='true' のときだけ許され（migrations/20260626_130000_force_rls_public_products.sql:15-38）、商品 API はそれを張らない（products.py に is_operator 0 件）。
- 新しい表の書き込みも app.is_operator='true' のときだけ（migrations/20261018_100000_create_product_packagings.sql:69-81）。共用の商品と同じ条件なので、**便3 は「誰が書けるか」を変えない**（is_operator を新しく張らない）。商品の行を書けたときだけ表も書ける。
- リポジトリ外の在庫一覧 GAS 4 フォルダは4列を読まない（recon/gas_grep.out 0 件、Code.js は配信シートの13列だけ）。§7 の「GAS の参照」は解消。

### 11-2. 決めたこと（設計判断）
- 応答の4項目（boxes_per_case・packs_per_box・box_weight_kg・case_weight_kg）は名前を変えず、新しい表から組み立てる。対応は便2 と同じ: boxes_per_case＝CASE 行の contained_count（中の単位が BOX のとき）／case_weight_kg＝CASE 行の weight_kg／packs_per_box＝BOX 行の contained_count（中の単位が PACK のとき）／box_weight_kg＝BOX 行の weight_kg。
- この対応は新しいファイル backend/app/services/product_packagings.py の1か所だけに書き、商品 API と在庫検索の両方がそこを使う（SSOT）。
- 古い4項目で値が送られて**値が変わった**ときは、その値の出典を `legacy`（ADR-1028:19「出典が残っていない」）にし、URL を空にする。値が同じなら行に触らない（出典・updated_at を保つ）。null が送られたらその値と出典を消し、入数も重さも無くなった行は消す（表の not_empty 制約のため）。出典つきの入力は便4（画面に出典の欄が付く便）で API に足す。
- updated_by は `user:<ユーザーid>`。
- 古い4列には書かない・読まない（列は便5 まで残る）。
- SQLite（pytest の簡易表）には新しい表を作らない。SQLite では4項目を NULL で返し、書き込みは飛ばす（前例: backend/app/routers/me_inventory_filters.py:91,130）。4項目の試験は PostgreSQL の試験へ移す。
- 応答に `packagings`（単位ごとの行と出典）を足す（§5）。

### 11-3. 触るファイルと変更
1. **新規 backend/app/services/product_packagings.py**
   - 定数 `LEGACY_FIELDS`: 上の対応を `{"boxes_per_case": ("CASE", "count", "BOX"), "case_weight_kg": ("CASE", "weight", None), "packs_per_box": ("BOX", "count", "PACK"), "box_weight_kg": ("BOX", "weight", None)}` の形で持つ。
   - `legacy_field_sql(field: str, product_id_expr: str) -> str`: 1項目ぶんのスカラー副問い合わせを返す。例（boxes_per_case）:
     `(SELECT pk.contained_count FROM public.product_packagings pk JOIN public.quantity_units u ON u.id = pk.unit_id JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id WHERE pk.product_id = {product_id_expr} AND u.code = 'CASE' AND cu.code = 'BOX')`。重さは contained の JOIN なしで `pk.weight_kg`。
   - `async def load_packagings(db, product_ids: list[int]) -> dict[int, list[dict]]`: `WHERE pk.product_id = ANY(:ids)` の1回の SELECT で、unit_code・contained_unit_code・contained_count・count_source・count_source_urls・weight_kg・weight_source・weight_source_urls・note・updated_at を返す（並びは quantity_units.display_order, id）。
   - `async def save_legacy_fields(db, product_id: int, fields: dict, updated_by: str) -> None`: fields は4項目のうち送られたものだけ。単位（CASE・BOX）ごとに、今の行を `SELECT ... FOR UPDATE` で読み、11-2 の決まりで新しい値を作り、変わったときだけ UPDATE／INSERT／DELETE する。INSERT は `INSERT ... SELECT :pid, u.id, cu.id, ... FROM public.quantity_units u LEFT JOIN public.quantity_units cu ON cu.code = :ccode WHERE u.code = :code` で単位の id を引く（code→id の定数を書かない）。単位の行が無くて0行になったら RuntimeError。
2. **backend/app/routers/products.py**
   - :66 の `_UPDATABLE_COLUMNS` から4項目を外す（:66-67 の残りは残す）。
   - :129-146 `_select_columns(ctx)`: :139 の4列を、PostgreSQL では `legacy_field_sql(...)` の4式 `AS boxes_per_case` 等に、SQLite では `NULL AS boxes_per_case` 等にする（ctx に方言が分かる項目を足すか、引数を足す。products の参照は `{ctx['ref']}.id`）。
   - GET 一覧（:251-255）・詳細（:347-354）: PostgreSQL では `load_packagings` で `packagings` を詰める（SQLite は空の配列）。
   - POST（:398-425）: INSERT 列と値から4項目（:407・:418）を外す。INSERT の後、PostgreSQL では4項目のうち None でないものを `save_legacy_fields` に渡す。その後の再取得（:433-436）はそのまま。audit_log の new_data はそのまま。
   - PATCH（:472-534）: `data.model_dump(exclude_unset=True)` から4項目を別に取り出す。:474 の「更新するフィールドを指定してください」は、4項目も無いときだけにする。products の UPDATE は、他の項目が無くても `SET updated_at = NOW()` で必ず流す（商品の行を書けるかの RLS の判定を今と同じにするため）。UPDATE の結果の行が有り、4項目があれば PostgreSQL で `save_legacy_fields` を呼び、`SELECT {_select_columns(ctx)} ... WHERE id = :id` で取り直して返す。audit_log の new_data には4項目も入れる（今と同じ中身）。
   - DELETE は触らない（表は ON DELETE CASCADE）。
3. **backend/app/schemas/product.py**
   - :68-71 と :116-119 の4項目の `ge=0` を `gt=0` にする（0 は 422。値の型・桁は変えない）。
   - 新しい `ProductPackagingOut`（11-3-1 の10項目。urls は `list[str]`）を足し、`ProductResponse`（:171-176 付近）に `packagings: list[ProductPackagingOut] = []` を足す。4項目の定義は変えない。
4. **backend/app/services/inventory_search.py:343-344**: `p.box_weight_kg, p.case_weight_kg` を `legacy_field_sql("box_weight_kg", "p.id") AS box_weight_kg, legacy_field_sql("case_weight_kg", "p.id") AS case_weight_kg` にする。:101-104・:437-442 と router・schema は変えない。
5. **テスト**
   - backend/tests/test_tcg_product_list_pg.py:83-87 の `create_product_schema` が流す migration に、quantity_units を作る migration（migrations/20260921_140000_product_classification_masters.sql。すでに入っていれば足さない）と migrations/20261018_100000_create_product_packagings.sql を足す。
   - 新規 backend/tests/test_product_packagings_pg.py（product_db を借りる。test_products_required_fields_pg.py:14,52-53 と同じ形）。quantity_units に CASE・BOX・PACK が無ければ試験の中で入れる。確かめること:
     - T1 古い4列が NULL・表に CASE（BOX×12・6.5kg・official・URL1つ）と BOX（PACK×20・0.236kg・legacy）があるとき、GET 詳細と GET 一覧が 12・6.5・20・0.236 を返し、packagings が2行。
     - T2 PATCH boxes_per_case=10 → CASE 行の contained_count 10・count_source legacy・count_source_urls 空、重さとその出典（official・URL）は変わらない。products.boxes_per_case は変わらない。
     - T3 PATCH で4項目を今と同じ値で送る → 表の行の updated_at・出典が変わらない。
     - T4 PATCH box_weight_kg=null → BOX 行の weight_kg・weight_source が NULL、入数は残る。続けて packs_per_box=null → BOX 行が消える。
     - T5 POST で4項目を入れる → CASE・BOX の2行（出典 legacy）。古い4列は NULL。
     - T6 PATCH boxes_per_case=0 → 422。
     - T7 在庫検索（search_inventory か GET /api/v1/inventory/search）が表の box_weight_kg・case_weight_kg を返す。
   - backend/tests/test_products.py: :594-597 の4項目の表明と :608-622 の boxes_per_case の更新は SQLite では値が返らないので、4項目を除いた形に直す（:616・:622 は `_UPDATABLE_COLUMNS` に残る別の数値の項目 moq に置き換える）。:624-630（-1 → 422）は残し、0 → 422 を1つ足す。
   - backend/tests/conftest.py:816-819 は触らない（便5 で消す）。
6. frontend/api-contract/openapi.json が `ProductResponse` から作られていて、CI で一致を確かめているなら、決まった生成手順で作り直す（手で書かない）。

### 11-4. 触らない範囲
frontend/src の全ファイル（項目名は変えない）、migrations/（試験の一覧に足すだけ。新しい migration は作らない）、scripts/seed_products_from_master.py（手で流す1回だけのスクリプト。CI・deploy から呼ばれない: recon/extra/F_seed_refs.out。便5 で直す）、backend/tests/conftest.py、test_products_required_fields_pg.py:26、quantity_units・weight_classes の管理画面、products.moq・weight・volume_weight。

### 11-5. 点検（生出力を /tmp/CC報告ファイル/product-packaging/bin3/impl/ へ）
- `cd backend && pytest -q tests/test_products.py tests/test_product_packagings_pg.py tests/test_products_required_fields_pg.py tests/test_tcg_product_list_pg.py`（PG の試験はローカルに PostgreSQL 16 と RLS_ADMIN_DATABASE_URL が無ければ skip になる。skip なら「未実施・CI で確認」と書く）
- `cd backend && pytest -q`（全体）と `make lint`（backend/CLAUDE.md:69）
- `git grep -n -E "packs_per_box|boxes_per_case|box_weight_kg|case_weight_kg" -- backend/app scripts` の結果を保存（便5 の K9 の元）
- `git diff origin/main...HEAD --name-only` が 11-3 のファイルだけ

### 11-6. 想定分岐（当てはまったら直さずに止めて報告）
- 行番号が 11-3 とずれていて、同じ中身の行が見つからない
- `_select_columns` を products.py 以外が使っている
- create_product_schema に足す migration が他の migration を前提にしていて流れない
- 在庫検索を PG の試験で呼ぶのに要る表が product_db に無い（T7 だけ「未実施」で止めずに報告に書く）
- openapi.json の生成手順が見つからない、または生成で ProductResponse 以外も変わる
- pytest の失敗が便3 の変更と関係ない所で出る

### 11-7. 受入条件（§6 の K6・K7 の測り方をここで固める）
| 基準 | 検証方法 |
|---|---|
| B1 CI がすべて緑（"pytest (SQLite + PostgreSQL RLS)" で T1〜T6 が skip でなく pass） | `gh pr checks` と、CI の pytest の記録で test_product_packagings_pg の pass を見る |
| B2（K6）本番反映後、4項目の値が便3 前と全商品で同じ | 本番の読み取りの道で、`legacy_field_sql` と同じ式で組み立てた4値と古い4列を全 1424 商品で突き合わせて不一致 0。商品 API を AI が本番で呼ぶ鍵は無いので、API が同じ式を使うことは T1 で確かめる |
| B3（K7）在庫検索の重さが同じ | T7 と、frontend の quoteDraft.test.ts（変更なし）が CI で pass。画面の目視は PO |
| B4 デプロイが成功し、本番の /health が 200 | `gh run view`・curl |

ブランチ: release/product-packaging-readers（このカードと同じ PR）。最初に `./scripts/dev/executor-preflight.sh || exit 1`。commit は実装1つ（`feat: 入数と重さを荷姿の表から読み書きする（ADR-1028 便3）`）。push まで。PR は Opus が作る。報告は DONE/BLOCKED:/NEEDS_DECISION: で始め、HEAD・変更ファイル・点検の生出力のパス。
