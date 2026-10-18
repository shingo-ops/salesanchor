# design: 商品の荷姿の表（ADR-1028）

- 現在地: [recon.md](./recon.md)（docs/handoff/product-packaging/recon.md）／決定: [ADR-1028](../../adr/ADR-1028-product-packaging-table.md)
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
- **便4（画面）**: 商品の編集画面に荷姿の欄（単位ごとの入数・重さ・出典の種類・URL）を出す。入力欄は components/ の金型を使い、文字は t("key") 経由（ADR-027・ADR-144）。販売サイトの URL は同じものを2つ入れられないようにする（DB の制約では同じ URL の重複を止められないため。出典つきの入力を受ける API も便4 で足し、そこで重複を 422 で拒む。§11-2）。見積・請求の重さは便3の応答で今のまま動く。
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
PO 2026-10-18 チャット「y」（便3 のカード→審査→実装→マージ→本番まで）。現在地の生出力は /tmp/CC報告ファイル/product-packaging/bin3/（recon/・recon/extra/・recon/prod/）、カード審査の記録は同 review-card/。行番号は origin/main 833a28713 時点（backend は 88391573c から差分なし）。

### 11-1. 着手前に分かった事実（本番・読み取りの道）
- 照合のやり直し（2026-10-17T16:28Z、data-change-1/02_verify_read.sql）: K3 CASE 146・BOX 176・計 322／K4 0|0|0|0／K5 4 行で便2 直後と同じ（recheck_k3k5.out）。
- 本番の products は 1424 行すべて共用（tenant_id NULL）。テナントの商品は 0 行。古い4列に値がある商品 176、表の行が付いたテナント商品 0（recon/prod/q1.out）。
- 商品 API（POST/PATCH /products）で作った・直した記録は各テナントの audit_logs に 0 件（record_audit_log は tenant_NNN.audit_logs に書く: backend/app/services/audit.py:303。recon/prod/q4.out）。アプリは salesanchor_app で接続し RLS が効く（docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:16）。共用行の書き込みは app.is_operator='true' のときだけ許され（migrations/20260626_130000_force_rls_public_products.sql:15-38）、商品 API はそれを張らない（products.py に is_operator 0 件、backend/app/auth/dependencies.py:307-309 が毎回 '' にする）。今は共用行の PATCH が UPDATE 0 行→:534 の `ProductResponse(**None)` で 500 になる（審査の試行 A）。
- 新しい表の書き込みも app.is_operator='true' のときだけ（migrations/20261018_100000_create_product_packagings.sql:69-81）。許されないと UPDATE・DELETE は黙って 0 行、INSERT はエラー（審査の試行 D・E）。**便3 は「誰が書けるか」を変えない**（is_operator を新しく張らない）。商品の行を書けたときだけ表を書く。
- リポジトリ外の在庫一覧 GAS 4 フォルダは4列を読まない（recon/gas_grep.out 0 件）。§7 の「GAS の参照」は解消。

### 11-2. 決めたこと（設計判断）
- 応答の4項目（boxes_per_case・packs_per_box・box_weight_kg・case_weight_kg）は名前と型を変えず、新しい表から組み立てる。対応は便2（data-change-1/01_apply.sql）と同じ: boxes_per_case＝CASE 行の contained_count（中の単位が BOX のとき）／case_weight_kg＝CASE 行の weight_kg／packs_per_box＝BOX 行の contained_count（中の単位が PACK のとき）／box_weight_kg＝BOX 行の weight_kg。
- この対応は新しいファイル backend/app/services/product_packagings.py の1か所だけに書き、商品 API と在庫検索の両方がそこを使う（SSOT）。
- 書き込みの決まり（古い4項目で送られたとき）:
  - 「今の値」は `legacy_field_sql` と同じ決まりで表から組み立てた値（例: CASE 行の中の単位が BOX でなければ boxes_per_case の今の値は NULL）。
  - 送られた値が今の値と同じ → その値に触らない（出典・URL・updated_at を保つ）。
  - 違う値（NULL でない）→ 値を入れ、出典を `legacy`（ADR-1028:19「出典が残っていない」）、その URL を `'{}'` にする。入数なら contained_unit_id も対応の中の単位（BOX／PACK）に入れる（UPDATE でも INSERT でも）。
  - NULL → その値・出典を NULL、URL を `'{}'`、入数なら contained_unit_id も NULL。入数も重さも NULL になった行は DELETE（表の not_empty 制約）。
  - UPDATE・DELETE は1行に当たったことを確かめ、0 行なら RuntimeError（RLS で黙って0行になるのを見逃さない）。
- 出典つきの入力・販売サイトの URL の重複を 422 で拒むことは便4（画面に出典の欄が付く便）で API に足す（§5 の便4 を直した）。
- updated_by は `user:<ユーザーid>`。
- 古い4列には書かない・読まない（列は便5 まで残る）。
- SQLite（pytest の簡易表）には新しい表を作らない。SQLite では4項目を NULL・packagings を空で返し、表の書き込みは飛ばす（前例: backend/app/routers/me_inventory_filters.py:91,130）。4項目の試験は PostgreSQL の試験へ移す。
- テナントの商品（tenant_id が NULL でない行。本番 0 行）に PostgreSQL で4項目を送ったら 422 `PACKAGING_SHARED_ONLY`（表の RLS がテナントを持たないため。何も書かない）。
- 共用行で products の UPDATE が 0 行（今の 500 の場合）は、audit_log と commit の前にすぐ `raise HTTPException(403, "PRODUCT_NOT_WRITABLE")`。rollback は get_db（backend/app/database.py:46-61）の except が行うので、route では呼ばない（同じ PATCH の 422 と同じ形）。
- 応答に `packagings`（単位ごとの行と出典）を足す（§5）。GET 一覧・詳細・POST・PATCH のすべての応答で詰める。
- scripts/seed_products_from_master.py（手で流す取り込み）は古い4列に書かなくする（§5・§2 のとおり便3 の対象）。表への取り込みは便6 の手順で行うので、`--apply` で CSV の4項目のどれかに値がある行が1つでもあれば、何も書かずに終了コード 3 で止める。

### 11-3. 触るファイルと変更
1. **新規 backend/app/services/product_packagings.py**
   - 定数 `LEGACY_FIELDS = {"boxes_per_case": ("CASE", "count", "BOX"), "case_weight_kg": ("CASE", "weight", None), "packs_per_box": ("BOX", "count", "PACK"), "box_weight_kg": ("BOX", "weight", None)}`。
   - `legacy_field_sql(field: str, product_id_expr: str) -> str`: 1項目ぶんのスカラー副問い合わせ。入数の例（boxes_per_case）:
     `(SELECT pk.contained_count FROM public.product_packagings pk JOIN public.quantity_units u ON u.id = pk.unit_id JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id WHERE pk.product_id = {product_id_expr} AND u.code = 'CASE' AND cu.code = 'BOX')`。重さは cu の JOIN なしで `pk.weight_kg`。
   - `async def load_packagings(db, product_ids: list[int]) -> dict[int, list[dict]]`: `WHERE pk.product_id = ANY(:ids)` の1回の SELECT。unit_code・contained_unit_code・contained_count・count_source・count_source_urls・weight_kg・weight_source・weight_source_urls・note・updated_at を返す（並びは quantity_units.display_order, quantity_units.id）。
   - `async def save_legacy_fields(db, product_id: int, fields: dict, updated_by: str) -> None`: fields は4項目のうち送られたものだけ。最初に `SELECT code, id FROM public.quantity_units WHERE code IN ('CASE','BOX','PACK')` で id を引き、3つ揃わなければ RuntimeError（id の定数は書かない）。単位（CASE・BOX）ごとに今の行を `SELECT ... FOR UPDATE` で読み、11-2 の決まりで UPDATE／INSERT／DELETE（変わる値が無ければ何もしない）。
2. **backend/app/routers/products.py**
   - :66 の `_UPDATABLE_COLUMNS` から4項目を外す（:66-67 の残りは残す）。
   - :129-146 `_select_columns(ctx)`: :139 の4列を、PostgreSQL では `legacy_field_sql(<項目>, f"{ctx['ref']}.id")` の4式 `AS boxes_per_case` 等に、SQLite では `NULL AS boxes_per_case` 等にする（`_products_ctx` :95-98 の戻り値に方言の項目を足して判定する）。
   - GET 一覧（:251-255）・詳細（:347-354）: PostgreSQL では `load_packagings` で `packagings` を詰める（SQLite は空）。
   - POST（:398-448）: INSERT 列と値から4項目（:407・:418）を外す。INSERT の後、PostgreSQL では4項目のうち None でないものを `save_legacy_fields` に渡す。再取得（:433-437）の後に packagings を詰める。audit_log の new_data（:442）はそのまま。
   - PATCH（:456-534）:
     - :472 の `model_dump(exclude_unset=True)` の直後、:473 の絞り込みの前に4項目を `packaging_fields` へ取り出す。
     - :474 の 400 は、update_data と packaging_fields の両方が空のときだけ。
     - PostgreSQL で packaging_fields があり、商品が tenant_id NOT NULL なら 422 `PACKAGING_SHARED_ONLY`（11-2）。
     - SET 句は項目のリストを `", ".join` で組み、リストが空なら `updated_at = NOW()` だけにする（先頭のカンマを作らない。archived_at の追加は is_archived があるときだけなので空のときは起きない）。products の UPDATE は必ず流す（RLS の判定を今と同じにするため）。
     - RETURNING の行が無ければ 11-2 の 403。
     - 行があり packaging_fields があれば、PostgreSQL で `save_legacy_fields` を呼び、`SELECT {_select_columns(ctx)} ... WHERE id = :id` で取り直す。
     - packagings を詰めて返す。
     - audit_log の new_data には4項目も入れる（今と同じ中身）。
   - DELETE は触らない（表は ON DELETE CASCADE）。
3. **backend/app/schemas/product.py**
   - :68-71 と :116-119 の4項目の `ge=0` を `gt=0` にする（0 は 422。型・桁は変えない）。
   - 新しい `ProductPackagingOut`（load_packagings の10項目。urls は `list[str]`）を足し、`ProductResponse`（:171-176 付近）に `packagings: list[ProductPackagingOut] = []` を足す。4項目の定義は変えない。
4. **backend/app/services/inventory_search.py:343-344**（`build_search_sql` :163 の f-string の中）: `p.box_weight_kg, p.case_weight_kg` を `{legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg, {legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg` にする（波かっこで埋め込む）。:101-104・:437-442 と router・schema は変えない。
5. **scripts/seed_products_from_master.py**: :179-205 の INSERT 列・ON CONFLICT の SET・値から4項目を外す。`--apply` で4項目（:138-141 で読む値）のどれかに値がある行があれば、DB につなぐ前（create_async_engine より前）に件数を数え、標準エラーに `ADR-1028: 入数・重さは書かない` で始まる1行と件数を出して、何も書かずに終了コード 3（argparse の使い方の誤りの 2 と分ける）。`--dry-run` はその件数を表示する。:17-20 の見出しの対応表と :70-73 の dataclass は残す（読みはする）。:27-28 の説明に1行「入数・重さは書かない（ADR-1028）」を足す。
6. **frontend/api-contract/openapi.json**: schema が変わるので必ず作り直す。`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（.github/workflows/api-contract-check.yml:31-55 の検査と同じ）。手で書かない。
7. **テスト**
   - 新規 backend/tests/test_product_packagings_pg.py。test_tcg_product_list_pg.py の product_db を借り、test_products_required_fields_pg.py:20-58 の client_factory（`_ROUTE_COLUMNS`・audit の no-op を含む）と同じ形で使う。試験の中で、quantity_units を design §3-4（.github/workflows/migration-test.yml の最小定義）と同じ DDL で作って CASE・BOX・PACK を入れ、migrations/20261018_100000_create_product_packagings.sql を流す（create_product_schema 本体は変えない）。確かめること:
     - T1 古い4列が NULL・表に CASE（BOX×12・6.5kg・official・URL1つ）と BOX（PACK×20・0.236kg・legacy）があるとき、GET 詳細と GET 一覧が 12・6.5・20・0.236 を返し、packagings が2行。
     - T2 PATCH boxes_per_case=10 → CASE 行の contained_count 10・count_source legacy・count_source_urls 空・contained_unit が BOX、重さとその出典（official・URL）は変わらない。products.boxes_per_case は変わらない。
     - T3 PATCH で4項目を今と同じ値で送る → 表の行の updated_at・出典が変わらない。
     - T4 PATCH box_weight_kg=null → BOX 行の weight_kg・weight_source が NULL・URL 空、入数は残る。続けて packs_per_box=null → BOX 行が消える。
     - T5 POST で4項目を入れる → CASE・BOX の2行（出典 legacy）、古い4列は NULL、応答の packagings 2行。9項目の検査は `monkeypatch.setattr("app.routers.products.check_required_fields", lambda *a, **k: [])` で外す。
     - T6 PATCH boxes_per_case=0 → 422。
     - T7 CASE 行の中の単位が PACK のとき、boxes_per_case は NULL で返り、boxes_per_case=8 を送ると中の単位が BOX・8 になる。
     - T8 テナントの商品に4項目を送る → 422 PACKAGING_SHARED_ONLY、表は変わらない。
     - T9 試験の中で ① migrations/20260626_130000_force_rls_public_products.sql を流して products に RLS を付ける ② `SET LOCAL ROLE salesanchor_app`（is_operator は未設定）③ 共用の商品に PATCH → 403 PRODUCT_NOT_WRITABLE ④ `RESET ROLE` の後、products・表とも変わらないことを確かめる。CI では salesanchor_app が有り、jarvis が作る表に権限が自動で付く（.github/workflows/test.yml:187-205）。ロールが無い環境（ローカル）だけ skip にして理由を書く。
   - 新規の DB を使わない試験（backend/tests/test_product_packagings_sql.py）: `legacy_field_sql` の4式の文字列と、`build_search_sql(...)` の戻りの SQL に `legacy_field_sql("box_weight_kg", "p.id")` と `legacy_field_sql("case_weight_kg", "p.id")` がそのまま入っていること、`p.box_weight_kg` が入っていないこと。
   - backend/tests/test_products.py: :594-597 の4項目の表明を外す。:608-622 の更新試験の boxes_per_case（:616・:622）を `_UPDATABLE_COLUMNS` に残る数値の moq に置き換える。:624-630（-1 → 422）は残し、0 → 422 を1つ足す。
   - backend/tests/conftest.py:816-819 は触らない（便5 で消す）。

### 11-4. 触らない範囲
frontend/src の全ファイル（項目名は変えない）、migrations/（新しい migration は作らない）、backend/tests/conftest.py、backend/tests/test_tcg_product_list_pg.py、test_products_required_fields_pg.py、quantity_units・weight_classes の管理画面、products.moq・weight・volume_weight。

#### 11-4a. 実装中に外れた所（2026-10-18 Opus 判断・審査で必要最小限と確認）
- 外れた所1: 試験の共有部品を触った（backend/tests/rls_bootstrap.py・test_tcg_product_list_pg.py・test_products_tcg_type_fk.py）。理由: 便3 後、PG の商品 API は load_packagings を通るため、product_db を借りる試験（test_products_required_fields_pg.py:14・test_tcg_product_detail_pg.py:24・test_product_packagings_pg.py:16）と test_products_tcg_type_fk の PATCH が、荷姿の表が無いと失敗した（CI fc7f3eed3 より前の実行で5件）。
- 外れた所2: §11-3-7 の「試験の中で最小 DDL で作る」をやめ、本番の migration 3本（20260921_140000・20260922_060000・20261018_100000）を、巻き戻す transaction の外で一度だけ確定で流す（rls_bootstrap.py の ensure_product_packagings、public_bootstrap_lock で直列化）。理由: (a) 試験の中で DDL を流すと rollback まで表のロックを持ち、並列 worker 間で deadlock した（CI fc7f3eed3 の T5、記録 /tmp/CC報告ファイル/product-packaging/bin3/impl/deadlock2_recon.out）(b) 文字列の DDL は test-schema-dup の関所で止まる。
- 外れた所3: ensure の先頭で public.products に ACCESS EXCLUSIVE を取り、test_tcg_distribution_pg（products → product_kinds の順）とロックの順を揃える。理由: 逆の順だと使い捨て PG で deadlock を再現し、先に取ると解消した（審査記録 /tmp/CC報告ファイル/product-packaging/bin3/review/ の repro1〜3）。
- T9 は試験の中で force_rls を流すまま。同じ transaction が先に products を ALTER しており、新しいロック順を増やさない（審査の判断）。

### 11-5. 点検（生出力を /tmp/CC報告ファイル/product-packaging/bin3/impl/ へ）
- `cd backend && pytest -q tests/test_products.py tests/test_product_packagings_pg.py tests/test_product_packagings_sql.py tests/test_products_required_fields_pg.py`（PG の試験はローカルに PostgreSQL 16 と RLS_ADMIN_DATABASE_URL が無ければ skip。skip なら「未実施・CI で確認」と書く）
- `cd backend && pytest -q`（全体）と `make lint`（backend/CLAUDE.md:69）
- openapi を作り直した後 `git diff --stat frontend/api-contract`
- `git grep -n -E "packs_per_box|boxes_per_case|box_weight_kg|case_weight_kg" -- backend frontend/src scripts` の結果を impl/k9_names.out に保存（便5 の K9 の元。Opus が 11-8 に一覧として写す）
- `git diff origin/main...HEAD --name-only` が 11-3 のファイルと design.md だけ

### 11-6. 想定分岐（当てはまったら直さずに止めて報告）
- 行番号が 11-3 とずれていて、同じ中身の行が見つからない
- `_select_columns` を products.py 以外が使っている
- 20261018_100000 の migration が §3-4 の最小の quantity_units では流れない
- openapi の生成で ProductCreate・ProductUpdate・ProductResponse・ProductPackagingOut 以外の schema が変わる
- pytest の失敗が便3 の変更と関係ない所で出る

### 11-7. 受入条件（§6 の K6・K7 の測り方をここで固める）
| 基準 | 検証方法 |
|---|---|
| B1 CI がすべて緑。"pytest (SQLite + PostgreSQL RLS)" で T1〜T9 が skip でなく pass | `gh pr checks` と CI の pytest の記録 |
| B2（K6）本番反映後、4項目の値が便3 前と全商品で同じ | 本番の読み取りの道で、`legacy_field_sql` と同じ式で組み立てた4値と古い4列を全 1424 商品で突き合わせて不一致 0。商品 API を AI が本番で呼ぶ鍵は無いので、API が同じ式を使うことは T1 と test_product_packagings_sql.py で確かめる |
| B3（K7）在庫検索の重さが同じ | test_product_packagings_sql.py（build_search_sql が同じ式を使う）と B2、frontend の quoteDraft.test.ts（変更なし）が CI で pass |
| B4 デプロイが成功し、本番の /health が 200 | `gh run view`・curl |
| B6 §11-8 に4項目名の残る所の一覧（impl/k9_names.out の写し）が入っている（K9 の元） | PR のマージ前に design.md を読む |
| B5 PO の目視: 商品の編集画面で入数・重さが今と同じに出る | PO が見る。見るまでは「未観測」と記録する（便3 のマージ・本番反映は止めない） |

ブランチ: release/product-packaging-readers（このカードと同じ PR）。最初に `./scripts/dev/executor-preflight.sh || exit 1`。commit は実装1つ（`feat: 入数と重さを荷姿の表から読み書きする（ADR-1028 便3）`）。push まで。PR は Opus が作る。報告は DONE/BLOCKED:/NEEDS_DECISION: で始め、HEAD・変更ファイル・点検の生出力のパス。

### 11-8. 4項目名が残る所（便3 後・K9 の元）
fa7f84b68 時点の `git grep -n -E "packs_per_box|boxes_per_case|box_weight_kg|case_weight_kg" -- backend frontend/src scripts` の結果（全 134 行・21 ファイル）。便5 の K9 はこの一覧を起点に、古い列を直接読む所が 0 になったかを見る。

| ファイル | 行数 |
|---|---|
| `backend/app/routers/inventory_search.py` | 2 |
| `backend/app/routers/products.py` | 3 |
| `backend/app/schemas/inventory_search.py` | 2 |
| `backend/app/schemas/product.py` | 12 |
| `backend/app/services/inventory_search.py` | 9 |
| `backend/app/services/product_packagings.py` | 5 |
| `backend/tests/conftest.py` | 4 |
| `backend/tests/test_product_packagings_pg.py` | 21 |
| `backend/tests/test_product_packagings_sql.py` | 8 |
| `backend/tests/test_products.py` | 8 |
| `backend/tests/test_products_required_fields_pg.py` | 1 |
| `frontend/src/components/CommerceSubmitButtonMigration.test.tsx` | 2 |
| `frontend/src/components/InventorySearchBar.tsx` | 2 |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx` | 3 |
| `frontend/src/pages/products/ProductEditPage.tsx` | 12 |
| `frontend/src/pages/products/ProductsPage.tsx` | 4 |
| `frontend/src/pages/products/products.types.ts` | 9 |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx` | 3 |
| `frontend/src/pages/quote-create/quoteDraft.test.ts` | 4 |
| `frontend/src/pages/quote-create/quoteDraft.ts` | 7 |
| `scripts/seed_products_from_master.py` | 13 |

<details><summary>全行</summary>

```
backend/app/routers/inventory_search.py:122:            box_weight_kg=c.box_weight_kg,
backend/app/routers/inventory_search.py:123:            case_weight_kg=c.case_weight_kg,
backend/app/routers/products.py:142:            for f in ("boxes_per_case", "packs_per_box", "box_weight_kg", "case_weight_kg")
backend/app/routers/products.py:146:            "NULL AS boxes_per_case, NULL AS packs_per_box, "
backend/app/routers/products.py:147:            "NULL AS box_weight_kg, NULL AS case_weight_kg"
backend/app/schemas/inventory_search.py:62:    box_weight_kg: float | None = Field(default=None, description="Box 単体重量 (kg)。")
backend/app/schemas/inventory_search.py:63:    case_weight_kg: float | None = Field(default=None, description="Case 重量 (kg)。")
backend/app/schemas/product.py:116:    boxes_per_case: int | None = Field(default=None, gt=0)
backend/app/schemas/product.py:117:    packs_per_box: int | None = Field(default=None, gt=0)
backend/app/schemas/product.py:118:    box_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
backend/app/schemas/product.py:119:    case_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
backend/app/schemas/product.py:186:    boxes_per_case: int | None = None
backend/app/schemas/product.py:187:    packs_per_box: int | None = None
backend/app/schemas/product.py:188:    box_weight_kg: Decimal | None = None
backend/app/schemas/product.py:189:    case_weight_kg: Decimal | None = None
backend/app/schemas/product.py:68:    boxes_per_case: int | None = Field(default=None, gt=0)
backend/app/schemas/product.py:69:    packs_per_box: int | None = Field(default=None, gt=0)
backend/app/schemas/product.py:70:    box_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
backend/app/schemas/product.py:71:    case_weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=3)
backend/app/services/inventory_search.py:102:    # box_weight_kg・case_weight_kg=形態別重量
backend/app/services/inventory_search.py:104:    box_weight_kg: float | None = None
backend/app/services/inventory_search.py:105:    case_weight_kg: float | None = None
backend/app/services/inventory_search.py:344:    {legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg,
backend/app/services/inventory_search.py:345:    {legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg,
backend/app/services/inventory_search.py:438:                box_weight_kg=(
backend/app/services/inventory_search.py:439:                    float(r["box_weight_kg"]) if r.get("box_weight_kg") is not None else None
backend/app/services/inventory_search.py:441:                case_weight_kg=(
backend/app/services/inventory_search.py:442:                    float(r["case_weight_kg"]) if r.get("case_weight_kg") is not None else None
backend/app/services/product_packagings.py:16:    "boxes_per_case": ("CASE", "count", "BOX"),
backend/app/services/product_packagings.py:17:    "case_weight_kg": ("CASE", "weight", None),
backend/app/services/product_packagings.py:18:    "packs_per_box": ("BOX", "count", "PACK"),
backend/app/services/product_packagings.py:19:    "box_weight_kg": ("BOX", "weight", None),
backend/app/services/product_packagings.py:3:応答の4項目（boxes_per_case・packs_per_box・box_weight_kg・case_weight_kg）は、
backend/tests/conftest.py:816:                boxes_per_case INTEGER,
backend/tests/conftest.py:817:                packs_per_box INTEGER,
backend/tests/conftest.py:818:                box_weight_kg NUMERIC(8, 3),
backend/tests/conftest.py:819:                case_weight_kg NUMERIC(8, 3),
backend/tests/test_product_packagings_pg.py:146:        assert body["boxes_per_case"] == 12
backend/tests/test_product_packagings_pg.py:147:        assert float(body["case_weight_kg"]) == 6.5
backend/tests/test_product_packagings_pg.py:148:        assert body["packs_per_box"] == 20
backend/tests/test_product_packagings_pg.py:149:        assert float(body["box_weight_kg"]) == 0.236
backend/tests/test_product_packagings_pg.py:158:        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 10})
backend/tests/test_product_packagings_pg.py:160:    assert response.json()["boxes_per_case"] == 10
backend/tests/test_product_packagings_pg.py:166:    old = (await db.execute(text("SELECT boxes_per_case FROM public.products WHERE id = :i"), {"i": pid})).scalar_one()
backend/tests/test_product_packagings_pg.py:177:            "boxes_per_case": 12, "case_weight_kg": "6.500", "packs_per_box": 20, "box_weight_kg": "0.236",
backend/tests/test_product_packagings_pg.py:189:        r1 = await client.patch(f"/api/v1/products/{pid}", json={"box_weight_kg": None})
backend/tests/test_product_packagings_pg.py:194:        r2 = await client.patch(f"/api/v1/products/{pid}", json={"packs_per_box": None})
backend/tests/test_product_packagings_pg.py:204:            "name_ja": "T5 商品", "boxes_per_case": 12, "packs_per_box": 20,
backend/tests/test_product_packagings_pg.py:205:            "box_weight_kg": "0.236", "case_weight_kg": "6.500",
backend/tests/test_product_packagings_pg.py:209:    assert body["boxes_per_case"] == 12 and body["packs_per_box"] == 20
backend/tests/test_product_packagings_pg.py:215:        text("SELECT boxes_per_case, packs_per_box, box_weight_kg, case_weight_kg FROM public.products WHERE id = :i"),
backend/tests/test_product_packagings_pg.py:225:        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 0})
backend/tests/test_product_packagings_pg.py:229:async def test_t7_case_contained_pack_is_not_boxes_per_case(client_factory):
backend/tests/test_product_packagings_pg.py:234:        assert (await client.get(f"/api/v1/products/{pid}")).json()["boxes_per_case"] is None
backend/tests/test_product_packagings_pg.py:235:        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 8})
backend/tests/test_product_packagings_pg.py:245:        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 5})
backend/tests/test_product_packagings_pg.py:265:            response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 10, "moq": 3})
backend/tests/test_product_packagings_pg.py:28:    "boxes_per_case INTEGER", "packs_per_box INTEGER", "box_weight_kg NUMERIC(8,3)", "case_weight_kg NUMERIC(8,3)",
backend/tests/test_product_packagings_sql.py:14:    sql = legacy_field_sql("packs_per_box", "x.id")
backend/tests/test_product_packagings_sql.py:19:    for field, unit in (("case_weight_kg", "CASE"), ("box_weight_kg", "BOX")):
backend/tests/test_product_packagings_sql.py:27:    assert set(LEGACY_FIELDS) == {"boxes_per_case", "case_weight_kg", "packs_per_box", "box_weight_kg"}
backend/tests/test_product_packagings_sql.py:32:    assert f'{legacy_field_sql("box_weight_kg", "p.id")} AS box_weight_kg' in sql
backend/tests/test_product_packagings_sql.py:33:    assert f'{legacy_field_sql("case_weight_kg", "p.id")} AS case_weight_kg' in sql
backend/tests/test_product_packagings_sql.py:34:    assert "p.box_weight_kg" not in sql
backend/tests/test_product_packagings_sql.py:35:    assert "p.case_weight_kg" not in sql
backend/tests/test_product_packagings_sql.py:7:    sql = legacy_field_sql("boxes_per_case", "p.id")
backend/tests/test_products.py:571:        "boxes_per_case": 16,
backend/tests/test_products.py:572:        "packs_per_box": 30,
backend/tests/test_products.py:573:        "box_weight_kg": "1.250",
backend/tests/test_products.py:574:        "case_weight_kg": "20.500",
backend/tests/test_products.py:620:    async def test_negative_boxes_per_case_rejected(self, client):
backend/tests/test_products.py:624:            "boxes_per_case": -1,
backend/tests/test_products.py:628:    async def test_zero_boxes_per_case_rejected(self, client):
backend/tests/test_products.py:632:            "boxes_per_case": 0,
backend/tests/test_products_required_fields_pg.py:26:    "boxes_per_case INTEGER", "packs_per_box INTEGER", "box_weight_kg NUMERIC(8,3)", "case_weight_kg NUMERIC(8,3)",
frontend/src/components/CommerceSubmitButtonMigration.test.tsx:26:  boxes_per_case: null, packs_per_box: null, box_weight_kg: null, case_weight_kg: null,
frontend/src/components/CommerceSubmitButtonMigration.test.tsx:39:const nonDefaultProductPayload = { ...productPayload, name_ja: 'Product', name_en: 'Product EN', product_kind: 'Kind', tcg_type: 'pokemon', set_type: 'Set', category: 'Category', mark: 'M', status: 'discontinued', unit_price: 12.5, quantity: 7, weight: 0.75, notes: 'memo', release_date: '2026-09-28', jan_code: 'JAN-1', card_number: 'CARD-1', expansion_code: 'EXP-1', rarity: 'Rare', language: 'en', unit_price_usd: 11.5, unit_price_eur: 10.5, image_url: 'https://example.com/p.png', boxes_per_case: 24, packs_per_box: 12, box_weight_kg: 1.5, case_weight_kg: 3.5, volume_weight: 4.5, moq: 6, hs_code: 'HS', material: 'Material', item: 'Item', required_output_value: 'Required', search_keywords: 'search', exclude_keywords: 'exclude', related_series: 'Series' };
frontend/src/components/InventorySearchBar.tsx:53:  box_weight_kg?: number | null;
frontend/src/components/InventorySearchBar.tsx:54:  case_weight_kg?: number | null;
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:132:        box_weight_kg: c.box_weight_kg ?? null,
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:133:        case_weight_kg: c.case_weight_kg ?? null,
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:377:                          updateItem(i, "weight", weightForUnit(nextUnit, item.box_weight_kg, item.case_weight_kg, item.weight));
frontend/src/pages/products/ProductEditPage.tsx:149:      boxes_per_case: form.boxes_per_case ? Number(form.boxes_per_case) : null,
frontend/src/pages/products/ProductEditPage.tsx:150:      packs_per_box: form.packs_per_box ? Number(form.packs_per_box) : null,
frontend/src/pages/products/ProductEditPage.tsx:151:      box_weight_kg: form.box_weight_kg ? Number(form.box_weight_kg) : null,
frontend/src/pages/products/ProductEditPage.tsx:152:      case_weight_kg: form.case_weight_kg ? Number(form.case_weight_kg) : null,
frontend/src/pages/products/ProductEditPage.tsx:321:                <TextFieldControl variant="product-edit" type="number" min="0" value={form.boxes_per_case} onChange={(e) => setForm({ ...form, boxes_per_case: e.target.value })} />
frontend/src/pages/products/ProductEditPage.tsx:325:                <TextFieldControl variant="product-edit" type="number" min="0" value={form.packs_per_box} onChange={(e) => setForm({ ...form, packs_per_box: e.target.value })} />
frontend/src/pages/products/ProductEditPage.tsx:329:                <TextFieldControl variant="product-edit" type="number" min="0" step="0.001" value={form.case_weight_kg} onChange={(e) => setForm({ ...form, case_weight_kg: e.target.value })} />
frontend/src/pages/products/ProductEditPage.tsx:333:                <TextFieldControl variant="product-edit" type="number" min="0" step="0.001" value={form.box_weight_kg} onChange={(e) => setForm({ ...form, box_weight_kg: e.target.value })} />
frontend/src/pages/products/ProductEditPage.tsx:83:          boxes_per_case: p.boxes_per_case != null ? String(p.boxes_per_case) : "",
frontend/src/pages/products/ProductEditPage.tsx:84:          packs_per_box: p.packs_per_box != null ? String(p.packs_per_box) : "",
frontend/src/pages/products/ProductEditPage.tsx:85:          box_weight_kg: p.box_weight_kg != null ? String(p.box_weight_kg) : "",
frontend/src/pages/products/ProductEditPage.tsx:86:          case_weight_kg: p.case_weight_kg != null ? String(p.case_weight_kg) : "",
frontend/src/pages/products/ProductsPage.tsx:373:                  <td>{p.boxes_per_case ?? "-"}</td>
frontend/src/pages/products/ProductsPage.tsx:374:                  <td>{p.packs_per_box ?? "-"}</td>
frontend/src/pages/products/ProductsPage.tsx:391:                  <td>{p.box_weight_kg != null ? Number(p.box_weight_kg).toFixed(1) : "-"}</td>
frontend/src/pages/products/ProductsPage.tsx:392:                  <td>{p.case_weight_kg != null ? Number(p.case_weight_kg).toFixed(1) : "-"}</td>
frontend/src/pages/products/products.types.ts:37:  boxes_per_case: number | null;
frontend/src/pages/products/products.types.ts:38:  packs_per_box: number | null;
frontend/src/pages/products/products.types.ts:39:  box_weight_kg: number | null;
frontend/src/pages/products/products.types.ts:40:  case_weight_kg: number | null;
frontend/src/pages/products/products.types.ts:78:  boxes_per_case: string;
frontend/src/pages/products/products.types.ts:79:  packs_per_box: string;
frontend/src/pages/products/products.types.ts:80:  box_weight_kg: string;
frontend/src/pages/products/products.types.ts:81:  case_weight_kg: string;
frontend/src/pages/products/products.types.ts:99:  boxes_per_case: "", packs_per_box: "", box_weight_kg: "", case_weight_kg: "",
frontend/src/pages/quote-create/QuoteCreatePage.tsx:226:                        updateItem(i, "weight", weightForUnit(nextUnit, item.box_weight_kg, item.case_weight_kg, item.weight));
frontend/src/pages/quote-create/QuoteCreatePage.tsx:84:        box_weight_kg: c.box_weight_kg ?? null,
frontend/src/pages/quote-create/QuoteCreatePage.tsx:85:        case_weight_kg: c.case_weight_kg ?? null,
frontend/src/pages/quote-create/quoteDraft.test.ts:32:        box_weight_kg: null,
frontend/src/pages/quote-create/quoteDraft.test.ts:33:        case_weight_kg: null,
frontend/src/pages/quote-create/quoteDraft.test.ts:40:  it("returns box_weight_kg when unit is box", () => {
frontend/src/pages/quote-create/quoteDraft.test.ts:43:  it("returns case_weight_kg when unit is case", () => {
frontend/src/pages/quote-create/quoteDraft.ts:22:  box_weight_kg?: number | null;
frontend/src/pages/quote-create/quoteDraft.ts:24:  case_weight_kg?: number | null;
frontend/src/pages/quote-create/quoteDraft.ts:33: * unit=box→box_weight_kg / unit=case→case_weight_kg / それ以外→fallback(products.weight)。
frontend/src/pages/quote-create/quoteDraft.ts:83:  box_weight_kg: null,
frontend/src/pages/quote-create/quoteDraft.ts:84:  case_weight_kg: null,
frontend/src/pages/quote-create/quoteDraft.ts:98:    box_weight_kg: null,
frontend/src/pages/quote-create/quoteDraft.ts:99:    case_weight_kg: null,
scripts/seed_products_from_master.py:139:                    boxes_per_case=_parse_int(raw.get("Boxes per Case", "")),
scripts/seed_products_from_master.py:140:                    packs_per_box=_parse_int(raw.get("Packs per Box", "")),
scripts/seed_products_from_master.py:141:                    box_weight_kg=_parse_float(raw.get("Box重量", "")),
scripts/seed_products_from_master.py:142:                    case_weight_kg=_parse_float(raw.get("Case重量", "")),
scripts/seed_products_from_master.py:157:        if any(v is not None for v in (r.boxes_per_case, r.packs_per_box, r.box_weight_kg, r.case_weight_kg))
scripts/seed_products_from_master.py:17:  Boxes per Case  → boxes_per_case
scripts/seed_products_from_master.py:18:  Packs per Box   → packs_per_box
scripts/seed_products_from_master.py:19:  Box重量          → box_weight_kg
scripts/seed_products_from_master.py:20:  Case重量         → case_weight_kg
scripts/seed_products_from_master.py:71:    boxes_per_case: int | None
scripts/seed_products_from_master.py:72:    packs_per_box: int | None
scripts/seed_products_from_master.py:73:    box_weight_kg: float | None
scripts/seed_products_from_master.py:74:    case_weight_kg: float | None
```

</details>

## 12. 実装カード（便4・画面・Sonnet）
PO 2026-10-18 チャット: 「商品マスタの編集ページを見たが重量、入数の入れる場所が無い」「便4 …作ってくれ」。対象の画面は「LINE解析」→「商品マスタ」→ 商品を押して出る詳細（TcgProductDetailDrawer）で「y」。
現在地の生出力: /tmp/CC報告ファイル/product-packaging/bin4/recon/・recon2/。

### 12-1. 着手前に分かった事実
- 入力欄が無い: frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx（317行）と productDetailModel.ts に荷姿の項目は無く、`git log -S` でも過去に無い（recon/02_*）。在庫側の frontend/src/pages/products/ProductEditPage.tsx:320-333 には古い4項目の欄があるが、メニューからの入口は見つからない（recon/01_*・未確認）。
- 保存 API: PUT /tcg/products/detail/{id}（backend/app/routers/tcg_product_import.py:301）。body は ProductDetailUpdate（:276-291、extra="forbid"）。処理は backend/app/services/tcg_product_detail_svc.py:126 update_product_detail（商品を FOR UPDATE → revision 照合 → :221 `SET LOCAL app.is_operator='true'` → 書く → audit_log → commit／例外で rollback）。入口は require_super_admin。
- revision は _snapshot（同 :54-70）の JSON の sha256。荷姿は snapshot に入っていない。
- 荷姿の正本の読み書きは backend/app/services/product_packagings.py だけ（対応表 LEGACY_FIELDS :15-20、load_packagings :44、save_legacy_fields :90）。出典・URL を受ける書き込みは未実装。
- 単位の名簿 public.quantity_units の列は id・code・name・name_en・display_order・is_active（migrations/20260921_140000_product_classification_masters.sql:38-48）。CARD は便2 で id 5 として追加済み。
- 金型: frontend/src/components/ に TextField（type="number"/"url" 可）・Select（options）・Textarea・Button。URL を複数入れる専用の金型は無く、このドロワーは複数の値を Textarea の改行区切りで受ける（productDetailModel.ts:49 words）。
- 文言は productDetail.*（ja.json・en.json とも :4002-4054・51キーで一致）。

### 12-2. 決めたこと（設計判断）

#### 単位と画面の行
- **画面で入れる単位は3つ。定義は backend の1か所だけにする**
  - CASE（中は BOX）・BOX（中は PACK）・PACK（中は CARD）。
  - product_packagings.py に `EDITABLE_UNITS = (("CASE","BOX"), ("BOX","PACK"), ("PACK","CARD"))` を足す。
  - GET の応答に `packaging_units` を入れる。中身は code・contained_code・name・name_en・contained_name・contained_name_en で、quantity_units から読む。
  - 画面はこれを並べる。単位の一覧と名前を frontend に直書きしない（SSOT）。
  - 名前は、言語が en なら name_en（無ければ name）、それ以外は name を出す。
- **画面の1行は1単位**。欄は次の8つ。
  - 中に入る数（数値）
  - 数の出典（選択）
  - 数の出典 URL（改行区切り）
  - 重さ kg（数値）
  - 重さの出典（選択）
  - 重さの出典 URL（改行区切り）
  - メモ（Textarea）
  - 最終更新（読み取り専用。updated_at）
- **出典の選択肢は4つ**: official＝公式サイト、official_store＝公式通販、retailer＝販売サイト、measured＝実測。
  - legacy（古い列から写した値）は、今の値の出典が legacy のときだけ選択肢に出す。表示は「古い値（出典なし）」で、選べない状態（disabled）にする。
  - 値を変えたら、別の出典を選ばせる。
- **URL の数は、DB の制約（§3-1）と同じ条件を API が先に確かめる**。
  - official・official_store は1つ以上。
  - retailer は違う URL を2つ以上。
  - measured・legacy は0でもよい。
  - 1つの欄に同じ URL が2回あれば 422。

#### 送り方と書き込みの決まり
- `packagings` は任意の配列で、1要素＝1単位。
- 配列を送らなければ、荷姿に一切触らない。除外ワード追加（addExcludeWord）の経路も壊さない。
- 送った単位は、次のどれかで扱う。
  - 今と全部同じ（数・中の単位・出典・URL の並び・重さ・重さの出典・URL・メモ）なら書かない。updated_at も変えない。
  - 数・重さ・メモがすべて空なら、行を消す。
  - それ以外は INSERT か UPDATE。updated_by は `user:<ユーザーid>`（便3 と同じ。routers/products.py:463,577）。
- UPDATE・DELETE は1行に当たったことを _expect_one（同 :84）で確かめる。
- 送らなかった単位の行（例: 画面で扱わない単位）には触らない。

#### トランザクション・競合・権限
- **同じトランザクションで書く**。update_product_detail の中で、`SET LOCAL app.is_operator='true'` の後に書く。どこかで失敗したら、商品の他の項目と一緒に巻き戻る。
- **revision に荷姿を入れる**。_snapshot に `packagings`（その商品の行を単位の display_order 順にした JSON）を足す。
  - 別の人が荷姿だけを直していても 409 で止まる。
  - audit_log の old/new にも荷姿が入る。
- **テナントの商品**（products.tenant_id が NULL でない）に packagings を送ったら、422 `PACKAGING_SHARED_ONLY` にする（便3 と同じ符号）。

#### 422 の符号
形は ProductDetailError(422, code)（tcg_product_detail_svc.py:44）。

| 符号 | 返す条件 |
|---|---|
| PACKAGING_UNKNOWN_UNIT | 単位が EDITABLE_UNITS に無い |
| PACKAGING_DUPLICATE_UNIT | 同じ単位が2回ある |
| PACKAGING_SOURCE_MISMATCH | 値があるのに出典が無い、または値が無いのに出典がある |
| PACKAGING_URLS_REQUIRED | URL の数が足りない |
| PACKAGING_DUPLICATE_URL | 同じ URL が2回ある |
| PACKAGING_INVALID_URL | http:// か https:// で始まらない、空白を含む、または2048字を超える |
| PACKAGING_LEGACY_NOT_ALLOWED | legacy を、今と違う値か新しい値に付けた |
| PACKAGING_NOTE_WITHOUT_VALUE | メモだけがあり、数も重さも無い（表の not_empty 制約） |
| PACKAGING_SHARED_ONLY | テナントの商品に送った |

- 画面は符号を productDetail.packaging.errors.<符号> の文言に直して出す（requiredFieldsMessage と同じ作り）。

#### 値の範囲
- 入数は 1〜1000000 の整数。
- 重さは 0 より大きく 99999.999 以下で、小数は3桁まで（NUMERIC(8,3)）。
- メモは1000字まで（表の制約）。
- 範囲外は pydantic で弾き、FastAPI の 422（detail が配列）にする。画面は既存どおり productDetail.invalid を出す。

#### 対象外
- **作成モード（新規の商品）では荷姿の欄を出さない**。作った後の編集で入れる。作成 API には触らない。
- **触らない**: 古い4項目の書き込み save_legacy_fields と routers/products.py、在庫側の ProductEditPage（入口の扱いは別件）、便6（外部の値を集めて入れる）。

### 12-3. 触るファイルと変更
1. **backend/app/services/product_packagings.py**
   - `EDITABLE_UNITS` と `SOURCES = ("official","official_store","retailer","measured")` を足す。
   - `async def load_packaging_units(db) -> list[dict]` を足す。EDITABLE_UNITS の順に quantity_units から code・name・name_en を読んで組み、足りない code があれば RuntimeError にする。
   - `def validate_packagings(rows, current) -> None` を足す。違反は `PackagingError(code)`（ValueError の子・このファイルに定義）で投げ、サービス側で ProductDetailError(422, code) に包む。
   - `async def save_packagings(db, product_id, rows, updated_by) -> None` を足す。比べる「今の値」は、load_packagings と同じ形の行。
   - 既存の関数は変えない。
2. **backend/app/routers/tcg_product_import.py**
   - `PackagingIn(BaseModel)`（extra="forbid"）を足す。項目は次のとおり。
     - unit_code: str
     - contained_count: int | None（ge=1, le=1000000）
     - count_source: Literal[official, official_store, retailer, measured, legacy] | None
     - count_source_urls: list[str]（max_length=10, default []）
     - weight_kg: Decimal | None（gt=0, le=Decimal("99999.999"), decimal_places=3）
     - weight_source: 同じ Literal | None
     - weight_source_urls: list[str]（max_length=10, default []）
     - note: str | None（max_length=1000）
   - ProductDetailUpdate に `packagings: list[PackagingIn] | None = Field(default=None, max_length=10)` を足す。
   - :315-317 の optional の扱いに "packagings" を足す。送られなければ values から外す。
   - updated_by に使うユーザー id を、サービスへ渡す引数として足す。既存の actor はそのまま。
3. **backend/app/services/tcg_product_detail_svc.py**
   - _snapshot に `packagings` を足す。
   - _response で `product["packagings"]`（その商品の行。数値と日時は JSON にできる形）と `response["packaging_units"]` を詰める。
   - update_product_detail では、"packagings" が values にあれば、テナントの判定 → validate → :221 の後で save_packagings、の順に呼ぶ。
4. **frontend/src/features/tcg-product-import/productDetailModel.ts**
   - Detail に `product.packagings` と `packaging_units` を足す。
   - Draft に `packagings: PackagingDraft[]` を足す。数・重さ・URL は文字列で持ち、URL は改行区切り。
   - draftFrom は packaging_units の順に組む。行が無い単位は空にする。
   - buildUpdateBody で、全単位を `packagings` として送る。数・重さは空なら null、URL は words() で分ける。
   - 符号を文言に直す `packagingErrorMessage(err, t)` を足す。
5. **frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx**
   - 除外ワードの印（:296）の後ろ、読み取り専用の欄（:297）の前に、見出し「入数・重さ」と単位ごとの行を出す。対象は mode === "edit" のときだけ。
   - 欄は TextField（type="number"）・Select・Textarea の金型だけで作る。
   - 保存に失敗したときの表示は、requiredFieldsMessage の後に packagingErrorMessage を試す。
   - emptyDraft に `packagings: []` を足す。
6. **frontend/src/features/tcg-product-import/product-csv.css**
   - 単位ごとの枠のクラス（`.product-detail__packaging` など）を足す。
   - 値は既存のトークン（var(--space-*)・var(--role-*)・境界線の色トークン）だけを使い、色の直値は書かない。
7. **frontend/src/locales/ja.json・en.json**
   - productDetail.packaging.* を両方に同じキーで足す。中身は、見出し・各欄の名前・出典4種＋legacy・説明・errors.<符号>。
8. **試験**
   - backend/tests/test_tcg_product_detail_pg.py に次を足す。
     - GET に packagings・packaging_units が出る。
     - 新規・変更・同じ値（同じ値なら書かず、updated_at が変わらない）。
     - 全部空にすると行が消える。
     - 送らなければ触らない。
     - 422 の各符号。
     - テナントの商品は 422。
     - 荷姿だけを別に直すと 409。
     - 失敗したら商品の他の項目も巻き戻る。
     - audit に荷姿が入る。
   - frontend の TcgProductDetailDrawer.test.tsx・productDetailModel.test.ts に次を足す。
     - 欄が単位の数だけ出る。
     - legacy が disabled になる。
     - 送る body の形。
     - 符号の文言。
     - 作成モードでは欄が出ない。
9. **docs/handoff/product-packaging/design.md**（この節）
10. **frontend/api-contract/openapi.json**
    - 便3 と同じ方法（Python 3.12・固定版）で作り直す。
    - 変わるのは ProductDetailUpdate と、新しい PackagingIn だけのはず。

### 12-4. 触らない範囲
- migrations/・deploy.yml・scripts/
- 表の制約
- routers/products.py・schemas/product.py
- 在庫検索
- ProductEditPage
- 作成 API
- quantity_units の管理画面
- backend/tests/rls_bootstrap.py（便3 で直した共有部品。足りなければ直さずに止めて報告する）

### 12-5. 点検（生出力を /tmp/CC報告ファイル/product-packaging/bin4/impl/ へ）
- backend: 足した試験と test_tcg_product_detail_pg.py の全体を、PostgreSQL で通す。test_product_packagings_pg.py も通す。
- frontend: `npm run check:all`・`npm run test -- tcg-product-import`・`npx tsc --noEmit`。
- i18n: ja と en の productDetail のキー差が0。
- 直書きの点検: 足した行に、日本語の直書き・生の `<select>`／`<input>`・色の直値が0件（`git diff` の追加行を grep する）。

### 12-6. 想定分岐（当てはまったら直さずに止めて報告）
- **見出しの金型が components/ にある**（SectionHeader など）
  - ある → それを使う。無い → `<h3>` に、既存トークンだけを使ったクラスを付ける。
  - どちらにしたかを報告する。この分岐だけは止めない。
- **本番の荷姿に、中の単位が EDITABLE_UNITS と違う行がある**（例: CASE の中が PACK）
  - 止める。画面で上書きすると値が変わるため。
  - 着手前に recon2 の件数で確かめる。
- **試験の PostgreSQL に CARD の行が無い**（rls_bootstrap が入れるのは PACK/BOX/CASE だけ）
  - 試験の中で CARD を足す（試験の DB だけ）。
  - 共有部品を直す必要が出たら止める。
- **openapi.json の差分に、ProductDetailUpdate・PackagingIn 以外の変更が出る** → 止める。
- **revision の計算を変えると既存の試験が落ちる** → 落ちた試験名と理由を報告して止める。

### 12-7. 受入条件
| 基準 | 検証方法 |
|---|---|
| U1 必須 CI がすべて緑 | `gh pr checks` で fail 0・pending 0 |
| U2 §12-5 の点検がすべて○ | impl/ の生出力 |
| U3 本番反映後、詳細を開くと「入数・重さ」に CASE・BOX・PACK の3行が出て、便2 で写した値が入っている | PO が super-admin の画面で目視する。API 側は、値のある1商品について、reader 鍵の道で読んだ product_packagings の値と GET 応答の形を試験で突き合わせる |
| U4 本番反映後、商品 API の4項目（便3 の K6）が全商品で今と同じ | §11-7 の K6 SQL（ai_ro の view 版）をもう一度流し、diff_any=0 |
| U5 本番反映後、デプロイが成功し /api/health が 200 | `gh run view`・curl |

### 12-8. 設計審査（1回目 REVISE）を受けた改訂 — §12-2〜12-7 と食い違う所はこの節を正とする
審査の生出力: /tmp/CC報告ファイル/product-packaging/bin4/review/design_review_evidence.txt。

#### 12-8-0. 着手前の本番確認（R7・済）
#4507 のデプロイ成功の後に、reader 鍵の道（ai_ro の view）で読んだ。生出力は recon2/*_retry.out、2026-10-17 23:43Z。
- 単位: CASE=1・BOX=2・PACK=3・CARD=5、4つとも is_active=True（17_card_unit）。
- 荷姿の行の組: CASE→BOX 109・CASE→(なし) 37・BOX→PACK 134・BOX→(なし) 42（13・16）。
  - 「(なし)」の 79 行は、数が無く重さだけの行（count_source が空・weight_source=legacy で 79 行、14）。
  - これは表の count_pair_check（中の単位が空 ⇔ 数が空）どおりの行で、EDITABLE_UNITS と違う組の行は 0。
  - よって §12-6 の「中の単位が違う行」の分岐には当たらない。
- 08:29 の失敗は、#4505 のデプロイが失敗して view が消えていた間の照会だった（成功の後は全本 result=ok）。

#### 12-8-1. 試験の DB（R1）
- 詳細サービスを呼ぶ試験 20 件は、すべて test_tcg_product_detail_pg.py の `edit_pg` を通る。
  - test_tcg_product_code_collision_pg.py は、この fixture を import して使う。
  - test_product_format_game_links_pg.py の fmt_pg は、edit_pg を土台にする。
- **edit_pg の中で、荷姿の表と4単位を作る。**
  - backend/tests/rls_bootstrap.py に、同期版の `provision_packagings_sync(cursor)` を足す。
  - 中身は既存の `PACKAGING_MIGRATIONS` を同じ順に流し、`quantity_units` に PACK・BOX・CASE・CARD を `ON CONFLICT (code) DO NOTHING` で入れる。CARD は名前「カード」、表示順 40。
  - edit_pg から `durable.pg` の直後に呼ぶ。
  - 試験ごとに新しい DATABASE なので、ロックの心配は無い。
- **rls_bootstrap.py への変更は、次の2つだけ許す**（§12-4 の「触らない」の例外）。
  - 上の関数を足すこと。
  - 既存の `ensure_product_packagings` の INSERT と `_packagings_ready` の件数を、CARD を含めた4にすること。
- 分岐:
  - durable の DB で PACKAGING_MIGRATIONS のどれかが失敗した（同じ表が既にある・依存の表が無い等）→ 直さずに止めて、エラー全文を報告する。
  - 上の2つ以外の共有部品を直す必要が出た → 止めて報告する。

#### 12-8-2. 送る条件（R2・R3）
- **画面の欄は、共用の商品（`product.tenant_id` が null か未定義）の編集モードだけに出す。** テナントの商品では出さない。
- **buildUpdateBody は `packagings` を `...draft` から外す**（分割代入で取り除く）。
  - 次の2つが両方とも真のときだけ `packagings` を body に入れる。
    1. 共用の商品である。
    2. `packagingsChanged(draft.packagings, initial?.packagings)` が真。
  - 判定の関数 `packagingsChanged` は、正規化した値（両端の空白を除いた文字列・URL の行の並び）で比べる。
  - 入れるときは、全単位を送る。
- addExcludeWord と CodeCollisionNotice の経路は、`initial`＝`base` なので変化なしとなり、packagings を送らない。
  - addExcludeWord の中でも、`packagings` を送らないことを試験で確かめる。
- **draftFrom は、`product.packagings` と `packaging_units`・`packaging_sources` のどれかが配列でない応答では throw する**（開かない）。
  - 理由は印と同じで、空とみなして送ると、保存済みの荷姿を消すため。

#### 12-8-3. 保存の順と決まり（R4・R6）
送られた行ごとに、上から順に確かめる。最初に当たった符号で 422 にする。

1. 単位が EDITABLE_UNITS に無い → UNKNOWN_UNIT。
2. 同じ単位が2回ある → DUPLICATE_UNIT。
3. 値を正規化する。
   - note は両端の空白を除き、空なら null。
   - URL は両端の空白を除き、空の行を捨てる。
4. 数と重さの欄を、それぞれ別に確かめる。
   - 値が null なのに、出典か URL がある（URL だけ送られた場合を含む）→ SOURCE_MISMATCH。
   - 値があるのに出典が null → SOURCE_MISMATCH。
5. 出典が legacy のときは、その欄だけで見る。次の両方を満たさなければ LEGACY_NOT_ALLOWED。
   - 今の行の同じ欄の値が送った値と同じ。数は `_same`、重さは `Decimal(str())` で比べる。
   - 今の出典が legacy。
6. URL の形を確かめる → INVALID_URL。
7. 1つの欄の中に同じ URL が2回ある → DUPLICATE_URL。
8. 出典ごとの URL の数を確かめる → URLS_REQUIRED。
9. note があるのに、数も重さも null → NOTE_WITHOUT_VALUE。

確かめ終えたら、行ごとに次のどれか1つを行う。

| 今の行 | 送った値 | すること |
|---|---|---|
| ある | すべて同じ | 書かない |
| 無い | 数・重さ・note がすべて null | **何もしない**（DELETE しない） |
| ある | 数・重さ・note がすべて null | DELETE（_expect_one） |
| 無い | それ以外 | INSERT（_expect_one） |
| ある | それ以外 | UPDATE（_expect_one） |

- 中の単位は、サーバーが EDITABLE_UNITS から決める。数が null なら中の単位も null にする（count_pair_check）。
- 画面で数か重さの値を変えたら、その欄の出典を "" に戻す（placeholder が出る）。
  - legacy の選択肢は「今の出典が legacy で、値が今と同じ」ときだけ、disabled で表示する。

#### 12-8-4. revision と応答の作り方（R5）
- _snapshot の SQL に、副問い合わせを1本足す。
  ```
  (SELECT coalesce(json_agg(json_build_object(
       'unit_code', u.code, 'contained_unit_code', cu.code, 'contained_count', pk.contained_count,
       'count_source', pk.count_source, 'count_source_urls', pk.count_source_urls,
       'weight_kg', pk.weight_kg, 'weight_source', pk.weight_source,
       'weight_source_urls', pk.weight_source_urls, 'note', pk.note, 'updated_at', pk.updated_at)
     ORDER BY u.display_order, pk.id), '[]'::json) ...) AS packagings
  ```
  - Python の Decimal と datetime を json.dumps に通さない。
  - updated_at を入れるので、荷姿を書けば revision も変わる。
- _response の `product["packagings"]` は、この snapshot の値をそのまま使う。GET と PUT の応答で形が同じになる。
- `packaging_units` は load_packaging_units から作る。
  - quantity_units の code が管理画面で変えられて CASE・BOX・PACK・CARD のどれかが見つからないと、RuntimeError で詳細が 500 になる。
  - これは便3 の legacy_field_sql と同じ前提として受け入れ、§7 に記す。

#### 12-8-5. SSOT（R8）
- **出典の一覧**: GET の応答に `packaging_sources` を足す。値は backend の `SOURCES`＋`"legacy"` で、並びもその順。
  - 画面はこれを並べ、文言は `productDetail.packaging.sources.<code>` の i18n だけで決める。
  - DB の CHECK と backend の `SOURCES` が一致していることを、PG 試験で確かめる（pg_constraint の定義に、5つの code が含まれる）。
- **EDITABLE_UNITS と LEGACY_FIELDS**: CASE→BOX・BOX→PACK の組が LEGACY_FIELDS と食い違わないことを、試験で確かめる。
- **weight_kg の受け取り**: model_dump(mode="json") で、文字列としてサービスに届く。比べるときは `_same`（Decimal(str())）、書くときは Decimal に直す。
- **行番号の訂正**:
  - router の optional の扱いは :314-316。
  - quantity_units には value の列もある（20260921_140000:38-48。NOT NULL は 20260922_060000 で外した）。

#### 12-8-6. リスクに足す（§7 への追記）
- 本番反映の前に開いていた詳細の下書きは、revision に荷姿が入るため、全商品で1回だけ 409 になる。開き直せば直る。
- quantity_units の code を書き換えると、詳細が 500 になる（12-8-4）。

#### 12-8-7. 受入条件の差し替え（R7）
| 基準 | 検証方法 |
|---|---|
| U1 必須 CI がすべて緑 | `gh pr checks` で fail 0・pending 0 |
| U2 §12-5 の点検と §12-8 の試験がすべて○ | impl/ の生出力 |
| U3 本番反映後、共用の商品の詳細を開くと「入数・重さ」に CASE・BOX・PACK の3行が出て、便2 の値が入っている | PO が画面で目視する（AI は本番 API を呼ぶ鍵を持たない、§11-7） |
| U4 本番反映後、商品 API の4項目が全商品で今と同じ | ai_ro の view 版の K6 SQL（bin3/prod/k6_after_ro.sql）を流し、diff_any=0 |
| U5 本番反映後、デプロイが成功し /api/health が 200 | `gh run view`・curl |
| U6 PO が1商品で値と出典を入れて保存し、再読み込みしても残っている | PO の目視。加えて、reader の道で、その商品の product_packagings に updated_by=`user:<id>` と出典の行が1件ある |
- U3 と U6 は、PO が戻るまで「未観測」として報告する。

#### 12-8-8. 再審査（APPROVE）の注記を実装の決まりにする
1. `packaging_units` と `packaging_sources` は、応答の最上位に置く。lookups の中には入れない（lookups の key の完全一致を見る試験 test_tcg_product_detail_pg.py:68 を壊さないため）。
2. 単位の表示順が、試験の DB（PACK=10・BOX=20・CASE=30）と本番（CASE=10・BOX=20・PACK=30）で逆になっている。
   - 試験では `product.packagings` を配列の並びで比べず、unit_code をキーにして比べる。
   - 画面は `packaging_units`（EDITABLE_UNITS の順）で行を組むので、表示は変わらない。
3. CI の接続は superuser で、RLS を素通りする。このため「:221 の SET LOCAL の後で書く」は試験では確かめられない。実装の審査で、Reviewer が順を目で確かめる。
4. 画面で数か重さの値を空にしたら、その欄の出典と URL も空に戻す（SOURCE_MISMATCH を出させない）。
5. 一度値を変えた欄は、legacy に戻せない。戻したいときは、取り消し（開き直し）を使う。これで受け入れる。
