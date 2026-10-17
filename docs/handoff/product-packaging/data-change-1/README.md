# ADR-1028 便2: 商品の荷姿の表へ値を写す（1 回だけのデータ変更）

## 目的
`products` の古い 4 列（boxes_per_case・case_weight_kg・packs_per_box・box_weight_kg）の値を、新しい表 `public.product_packagings` へ写す。あわせて `quantity_units` に CARD を 1 行足す。SQL は [design.md](../design.md) §4-1・4-2 のまま。足したのはトランザクション・件数ガードだけ（ADR-1007: migration に値を書かず、記録した SQL を 1 回だけ流す）。

## PO 承認
PO 2026-10-18 チャット「y」（便2 の実施。CARD を足し、古い4列の値 322 行＝ケース146・ボックス176 を写す）

## 順序と実際のコマンド
SQL ファイルはどれも `docs/handoff/product-packaging/data-change-1/` の中。リポジトリのルートで流す。

| 段 | ファイル | 流す人 | 使う鍵 |
|---|---|---|---|
| 1 事前確認（読み取り） | `00_precheck_read.sql` | Opus か担当（Sonnet） | `~/.ssh/salesanchor-reader`（読み取り専用の鍵） |
| 2 DRY-RUN（書き込みの形・最後に巻き戻す） | `01_dryrun.sql` | Opus のみ | `~/.ssh/manual-only/id_ed25519`（無制限鍵） |
| 3 本実行（書き込み） | `01_apply.sql` | Opus のみ | 同上 |
| 4 事後確認（読み取り） | `02_verify_read.sql` | Opus か担当（Sonnet） | `~/.ssh/salesanchor-reader` |

読み取り（00・02）のコマンド全文:

```
ssh -F /dev/null -i ~/.ssh/salesanchor-reader -o IdentitiesOnly=yes -o BatchMode=yes ubuntu@49.212.137.46 < docs/handoff/product-packaging/data-change-1/00_precheck_read.sql
```
02 も同じ形（ファイル名だけ `02_verify_read.sql`）。読み取りの道は SELECT/WITH を 1 文しか受けないため、00 と 02 は UNION ALL で 1 文にしてある。

書き込み（01_dryrun・01_apply）のコマンド全文:

```
ssh -o BatchMode=yes prod1 'docker exec -i astro-webapp-postgres-1 psql -X -U jarvis -d jarvis_db -v ON_ERROR_STOP=1' < docs/handoff/product-packaging/data-change-1/01_dryrun.sql
```
apply も同じ形（ファイル名だけ `01_apply.sql`）。

- 書き込みは Opus が、PO 本人が出した使い捨ての許可（`bash scripts/permit-danger.sh "psql write"`。1 回ごと・30 分で失効）のもとで流す。DRY-RUN と本実行で、それぞれ許可が要る。
- prod1 への接続は `~/.ssh/manual-only/id_ed25519`（無制限鍵）を使う。担当（Sonnet）は流さない。流すのはこのコミットの中身そのまま。
- `01_dryrun.sql` は BEGIN…ROLLBACK で件数ガードが通れば `DRYRUN_OK`。`01_apply.sql` は件数ガードが違えば COMMIT に進まず、通れば `COMMIT_DONE`。`SET LOCAL app.is_operator = 'true'` を同じトランザクションで張る。
- jarvis は superuser のため RLS に絞られない（ADR-1024:18）。

## 想定件数
| 項目 | 想定 |
|---|---|
| CARD | 1 行（display_order 40。既存 3 行は 10・20・30） |
| CASE の行 | 146 |
| BOX の行 | 176 |
| 表の合計 | 322（実施前は 0） |
| `<= 0` の値 | 4 列とも 0 |
| 照合の不一致（K4） | 0 / 0 / 0 / 0 |

違えば止めて Opus に報告する。

## 戻し方
updated_by が 'ADR-1028 data-change-1' の行を消し、CARD の行を消す。古い列は残っているので値は失われない。戻しの SQL は次のとおり（ファイルにはしない。必要になったときだけ、この内容を Opus が流す）。

```sql
BEGIN;
SET LOCAL app.is_operator = 'true';

DO $$
DECLARE
  n_deleted bigint;
  n_ref bigint;
  card_id bigint;
BEGIN
  -- 印の付いた行を消し、消えた件数が 322 でなければ止める（止まれば全体が巻き戻る）
  DELETE FROM public.product_packagings WHERE updated_by = 'ADR-1028 data-change-1';
  GET DIAGNOSTICS n_deleted = ROW_COUNT;
  IF n_deleted <> 322 THEN
    RAISE EXCEPTION '戻し中止: 消えた行が % 件（想定 322）', n_deleted;
  END IF;

  SELECT id INTO card_id FROM public.quantity_units WHERE code = 'CARD';
  IF card_id IS NULL THEN
    RAISE EXCEPTION '戻し中止: CARD の行がない';
  END IF;

  -- CARD を参照している表がないことの確認（product_packagings を含め、quantity_units を指す外部キーを全部見る）
  SELECT coalesce(sum((xpath('/row/c/text()',
           query_to_xml(format('SELECT count(*) AS c FROM %s WHERE %I = %L',
                               c.conrelid::regclass, a.attname, card_id), false, true, '')))[1]::text::bigint), 0)
    INTO n_ref
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
   WHERE c.contype = 'f' AND c.confrelid = 'public.quantity_units'::regclass;
  IF n_ref <> 0 THEN
    RAISE EXCEPTION '戻し中止: CARD を参照する行が % 件ある', n_ref;
  END IF;
END
$$;

DELETE FROM public.quantity_units WHERE code = 'CARD';
COMMIT;
```

注意:
- 大量の削除にあたるため、PO の確認と使い捨ての許可（`bash scripts/permit-danger.sh "psql write"`）が要る。
- 便3 が表に書き始めた後は updated_by が変わり、この印で拾えない行が出る。その場合この戻し方は使えない（322 件の確認で止まる）。Opus に相談する。

## 実行結果（実施後に記入）
| 項目 | 内容 |
|---|---|
| 事前確認 | 下記（2026-10-18 実測。K5 の基準＝既存 3 行の値） |
| DRY-RUN | 2026-10-17T16:15:03Z・rc=0・ROLLBACK・DRYRUN_OK（SQL の shasum は下記）。試し実行後の読み取りで PACKAGINGS 0・CARD 0（残らず） |
| 実施日時・COMMIT | 2026-10-17T16:18:06Z・rc=0・COMMIT_DONE。流した人: Claude Opus（PO 本人が出した使い捨ての許可 "psql write" のもと。試し実行用 16:14:47Z 発行・本実行用 16:17:56Z 発行） |
| 事後確認（K3・K4・K5） | K3○（CASE 146・BOX 176・計 322）／K4○（0\|0\|0\|0）／K5○（既存 3 行は事前確認と同じ。CARD が 1 行・display_order 40・value NULL。CARD の id が 5 なのは試し実行で連番が 1 つ進んだため）。下記 |

事前確認の出力（`00_precheck_read.sql` を読み取りの道で流した生出力。AUDIT 行は省略）:

```
k	v
QU	1 | CASE | ケース | Case | <NULL> | 10 | true
QU	2 | BOX | ボックス | Box | <NULL> | 20 | true
QU	3 | PACK | パック | Pack | <NULL> | 30 | true
CASE_CAND	146
BOX_CAND	176
LE0_boxes_per_case	0
LE0_case_weight_kg	0
LE0_packs_per_box	0
LE0_box_weight_kg	0
PACKAGINGS	0
CARD_EXISTS	0
```

試し実行の出力（`01_dryrun.out` 全文）:

```
BEGIN
SET
INSERT 0 1
INSERT 0 146
INSERT 0 176
DO
     k     | count 
-----------+-------
 CARD      |     1
 CASE_ROWS |   146
 BOX_ROWS  |   176
 ALL_ROWS  |   322
(4 rows)

ROLLBACK
 ?column?  
-----------
 DRYRUN_OK
(1 row)

rc=0
2026-10-17T16:15:03Z
```

試し実行後の読み取り（`01_dryrun_after.out` の結果行と AUDIT 行の ts・result。どちらも 0 ＝ ROLLBACK で残っていない）:

```
?column?	count
PACKAGINGS	0
CARD	0
AUDIT ts=2026-10-17T16:15:10Z result=ok
```

SQL の shasum（`01_dryrun.sha`。2 行とも一致＝コミットの中身と同じ）:

```
2a17f306e4be6c32de2e05ca5ce2513f0693d95f  -
2a17f306e4be6c32de2e05ca5ce2513f0693d95f  -
```

本実行の出力（`01_apply.out` 全文）:

```
BEGIN
SET
INSERT 0 1
INSERT 0 146
INSERT 0 176
DO
  ?column?   
-------------
 COMMIT_NEXT
(1 row)

COMMIT
  ?column?   
-------------
 COMMIT_DONE
(1 row)

rc=0
2026-10-17T16:18:06Z
```

本実行の SQL の shasum（`01_apply.sha`。2 行とも一致）:

```
7eda0e1b4b225cde0a1c8ed2bd151f1b2f9095e6  -
7eda0e1b4b225cde0a1c8ed2bd151f1b2f9095e6  -
```

事後確認の出力（`02_verify.out` の結果行と AUDIT 行の ts・result）:

```
k	v
K3	CASE|146
K3	BOX|176
K3_TOTAL	322
K4	0|0|0|0
K5	1 | CASE | ケース | Case | <NULL> | 10 | true
K5	2 | BOX | ボックス | Box | <NULL> | 20 | true
K5	3 | PACK | パック | Pack | <NULL> | 30 | true
K5	5 | CARD | カード | Card | <NULL> | 40 | true
AUDIT ts=2026-10-17T16:18:15Z result=ok
```
