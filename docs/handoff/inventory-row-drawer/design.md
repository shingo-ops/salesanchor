# design: 在庫表の行から解析パネルを開く（便1・見るだけ）

> この文書は、super admin が在庫表の行をクリックすると、要確認ページと同じ右から出るパネルで「原文・Gemini抽出・システム解析」が見られるようにする設計です。
> 親（あるべき姿）: [../../specs/inventory-management/README.md](../../specs/inventory-management/README.md)（開発区分＝既存の延長）
> 現状の証拠: [recon.md](recon.md)（docs/handoff/inventory-row-drawer/recon.md）
> 関連 ADR: ADR-1014（在庫表＝配信行・行の定義は1か所）、ADR-027（i18n）、ADR-144（UI ガバナンス）

## 1. 目的と KGI

PO の依頼（2026-10-16 原文）:

> superadminのワタシが在庫表をクリックするとスライドページが表示されて原文とgemini抽出結果、システムの解析結果が見れるようにしてほしい、要確認ページのスライドページと同じ仕組み

KGI（PO の言葉を、○×で判定できる形に分けたもの）:

| # | KGI（○×） |
|---|---|
| G1 | super admin が `/inventory` の行をクリックすると、右からパネルが開く。パネルには3つが表示される。①原文（LINE 投稿の本文）②Gemini 抽出結果 ③システムの解析結果（商品・状態・単位・数量・単価など） |
| G2 | super admin 以外の利用者は、行をクリックしてもパネルが開かない（今と同じ挙動） |
| G3 | 「同じ投稿をまとめる」設定で1行にまとめた行は、元の行が全部パネルで見られる（件数＝`merged_count`） |
| G4 | 在庫表の一覧の中身と、GAS 在庫一覧（スプレッドシート）の出力は、変更前と同じ |

KGI の承認状況:
- G1・G2 は PO の依頼文そのもの。
- G3・G4 は設計担当が加えた分解。PO からは 2026-10-16 に「最後まで完結させる」の指示を受けた（同日の y/n 質問には未回答）。
- 未承認の判断は本便に入れていない（§2）。

## 2. 対象と対象外

対象:
- 在庫表の行クリックでパネルを開く。
- パネルは見るだけ。

対象外:
- パネルから直す機能（商品付け替え・値の直し・確認済み）。
  - 実現可能なことは PO に回答済み。採否が PO 未回答のため、本便では入れない。
  - 次便の判断材料は §9 に置いた。
- 在庫表の自動更新（即時反映）。見るだけなので不要。
- スマホのカード表示（`mobileCards`）からの開閉。PC の表のクリックだけを対象にする。
- recon §3 の `manual_values` 欠落の疑い（別件。本便では触らない）。

## 3. 変更前 → 変更後（利用者に見える変化）

| | 変更前 | 変更後 |
|---|---|---|
| super admin が在庫表の行をクリック | 何も起きない | 右からパネルが開き、原文・Gemini 抽出・システム解析が出る |
| super admin 以外がクリック | 何も起きない | 何も起きない（変わらない） |
| チェック欄をクリック | 行が選択される | 行が選択される（パネルは開かない） |
| まとめた行をクリック | ― | パネル上部のタブで、元の各行を切り替えて見られる |
| 在庫表の列・件数・GAS シート | ― | 変わらない |

## 4. 技術設計

方針: 新しいデータの写しを作らない（SSOT）。
- 行の定義は `distribution_rows_parts` の1か所に置いたまま、各行の元の ID を1列足す。
- パネルのデータは、要確認パネルと同じ `fetch_analysis_results` から取る。
- 画面は、要確認パネル `ReviewItemDrawer` をそのまま使う。

### 4-1. バックエンド A: 在庫の行に元の ID を足す

ファイル: `backend/app/services/tcg_distribution_svc.py`

(a) dist_base の SELECT（:308 の次の行）に1列足す。

```python
# 変更前（:308）
            ar.id::text                                             AS row_key,
# 変更後
            ar.id::text                                             AS row_key,
            ei.id::text                                             AS item_key,
```

(b) `dist_agg`（:360-368）に1列足す。まとめた組の全 ID を、並び順どおりに集める。

```python
# 変更前（:365 の次）
               MIN(sort_ord)  OVER (PARTITION BY ekey) AS sort_min
# 変更後
               MIN(sort_ord)  OVER (PARTITION BY ekey) AS sort_min,
               array_agg(item_key) OVER (PARTITION BY ekey ORDER BY sort_ord
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS item_keys_agg
```

(c) `_distribution_final_select`（:257-266）に引数 `item_keys: str` を足し、SELECT の末尾に `{item_keys} AS extraction_item_ids` を足す。
- `distribution_final_select_plain()`（:269-271）は `item_keys="ARRAY[item_key]"` を渡す。
- まとめありの final（:370）は `item_keys="item_keys_agg"` を渡す。
- 他の引数・列・式は変えない。

触らないもの:
- WHERE（:333-341）
- gkey
- まとめ条件（dist_groups）
- `_GAS_COLUMNS`（:251-254）
- `fetch_output_rows`（:390-412）

GAS 出力は `_GAS_COLUMNS` の固定14列だけを取り出すので、変わらない（G4）。

ファイル: `backend/app/schemas/inventory_offers.py`
- `InventoryRow`（:129-159）の `merged_count` の次に、次の1行を足す。

```python
    extraction_item_ids: list[str] = []  # 行の元になった extraction_items.id（まとめた行は組の全件。解析パネル用）
```

ファイル: `backend/app/routers/inventory_offers.py`
- `_project_inventory_rows`（:156-187）の `merged_count=...` の次に、次の1行を足す。

```python
                extraction_item_ids=[str(v) for v in (row.get("extraction_item_ids") or [])],
```

- `_build_inventory_view_sql`（:267-311）は変更しない。`nx.*` / `pg.*` で全列を通すので、新しい列もそのまま流れる。UNION ALL の3つの枝は同じ列構成のまま。

### 4-2. バックエンド B: 解析結果 API に「ID 指定」を足す

ファイル: `backend/app/services/tcg_analysis_review_svc.py`

(a) `_BASE_FROM`（:52-62）を関数にする。既存の定数名は残す。

```python
def _base_from(*, include_inactive: bool = False) -> str:
    # include_inactive=True は在庫表（配信行）と同じ範囲: 非アクティブ投稿も含め、代わりに ar.is_current = TRUE で絞る（ADR-158 と同じ型）
    return f"""
    FROM {TCG_SCHEMA}.analysis_results ar
    JOIN {TCG_SCHEMA}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {TCG_SCHEMA}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {TCG_SCHEMA}.source_messages sm ON sm.id = ej.source_message_id AND {"ar.is_current = TRUE" if include_inactive else "sm.is_active = TRUE"}
    JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
    LEFT JOIN public.products p ON p.id = ar.product_id
    LEFT JOIN public.type_master ws ON ws.id = p.work_id
    {review_joins(schema=TCG_SCHEMA)}
"""


_BASE_FROM = _base_from()
```

- `include_inactive=False` の出力は、変更前の `_BASE_FROM` と文字単位で同じにする（テストで固定。§6 B3）。
- 実装前に `git grep -n "_BASE_FROM" origin/main -- backend/` で参照箇所を全部列挙する。このファイル以外から参照があれば、停止して報告する。

(b) `_build_where`（:69-128）に、キーワード引数 `extraction_item_ids: list[str] | None = None` を足す。
- 値があるときは、`conditions.append("ei.id = ANY(CAST(:item_ids AS uuid[]))")` と `params["item_ids"] = extraction_item_ids` を、他の条件より先に足す。
- それ以外の分岐は変えない。

(c) `fetch_analysis_results`（:165）に、キーワード引数 `extraction_item_ids: list[str] | None = None` を足す。
- `inactive = extraction_item_ids is not None` とする。
- `src = source_cte(schema=TCG_SCHEMA, include_inactive=inactive)` と `base_from = _base_from(include_inactive=inactive)` を作る。
- count（:196）・providers（:200）・items（:210）の3本の SQL で、`source_cte(schema=TCG_SCHEMA)` を `src` に、`_BASE_FROM` を `base_from` に置き換える。
- `_build_where` に `extraction_item_ids` を渡す。
- それ以外（行の組み立て :271 以降）は変えない。

理由: 在庫表の行は、非アクティブな投稿からも作られる（`backend/app/services/tcg_distribution_svc.py:285` が `include_inactive=True`）。ID を指定したときは、在庫表と同じ範囲で引けるようにする。ID を指定しないときの挙動は変えない。

ファイル: `backend/app/routers/tcg_analysis_review.py`（:121-150）
- クエリ引数に `extraction_item_ids: list[UUID] | None = Query(default=None, description="extraction_items.id を指定して取得（在庫表の解析パネル用・最大50件）")` を足す。
  - `from uuid import UUID` を足す。
  - 形式が UUID でなければ、FastAPI が 422 を返す。
- 値があるときの扱い:
  - `len(extraction_item_ids) > 50` なら、`HTTPException(422, "extraction_item_ids は50件まで")` を返す。
  - `status_tab="ALL"`、`offset=0`、`limit=len(extraction_item_ids)` に置き換える。
  - `fetch_analysis_results(..., extraction_item_ids=[str(v) for v in extraction_item_ids])` を呼ぶ。
- 権限 `require_super_admin`（:133）は変えない。

### 4-3. フロントエンド

金型: `Drawer`・`Tabs`・`DataTable` は既存のものを使う（recon §5）。

新しい UI 部品は作らない。色・余白の直値、生の input・select・自作タブは使わない。読み込み中・エラーの表示は、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx` が使っている部品と文言キーの使い方に合わせる（実装時に同ファイルの読み込み中・エラー表示の行を読み、同じ部品を使う。該当する金型が無ければ停止）。

(a) `frontend/src/features/inventory/inventoryColumns.tsx:12-35` `InventoryRow` に `extraction_item_ids: string[];` を足す。

(b) `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`
- props（:27-36）に次の2つを足す（どちらも省略可）。
  - `viewOnly?: boolean`（見るだけ）
  - `headerSlot?: ReactNode`（本文の先頭に置く部品）
- `viewOnly === true` のとき、次の3つを満たす。
  - 「確認済みにする」（:170-176）と取消（:179-180）を出さない。`canKeep` 等の条件に `!viewOnly` を足す。
  - 比較表の行を押しても ReviewFixWizard が開かない。`selectRow`（:64-73）の先頭で `if (viewOnly) return;` とし、ItemComparison に渡す行選択の props も、行がボタンとして見えない値にする。現行 :195 付近の渡し方を読み、選択可能な行の集合を空にする。
  - 要確認の理由の欄（:149-169）は、そのまま表示する（理由が無ければ「理由はありません」）。
- `headerSlot` は `<Stack gap="4">`（:147）の最初の子として置く。
- `viewOnly` と `headerSlot` を渡さないときの表示・操作は、変更前と同じにする（既存テストが全部通ること）。

(c) 新規 `frontend/src/features/inventory/InventoryRowDrawer.tsx`
- props は `{ row: InventoryRow; onClose: () => void }`。
- 取得: `GET /tcg/analysis-results?extraction_item_ids=<id1>&extraction_item_ids=<id2>…`
  - 配列は `URLSearchParams` に1件ずつ append して作る（`[]` 付きの書式にしない）。
  - API 呼び出しは、`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:96-102` と同じクライアントを使う。
- 状態ごとの表示:
  - 読み込み中: `<Drawer open size="wide" title={t("inventory.rowDrawer.title")} onClose={onClose}>` の中に、読み込み中の表示。
  - 401/403: 同じ Drawer に、要確認パネルと同じ super admin 限定の文言キー（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:109-111` が使うキー）を出す。
  - その他のエラー: `t("inventory.rowDrawer.loadError")`。
  - 0件: `t("inventory.rowDrawer.notFound")`。
- 1件以上: `<ReviewItemDrawer item={items[active]} viewOnly onClose={onClose} onRefresh={refetch} headerSlot={tabs} />`
  - `items.length >= 2` のときだけ、`tabs` に `<Tabs items={items.map((it, i) => ({ key: it.extraction_item_id, label: t("inventory.rowDrawer.itemTab", { n: i + 1 }) }))} activeKey=… onChange=… variant="pill" />` を入れる。1件なら `undefined`。
  - 並び順は API が返した順（result_order）。

(d) `frontend/src/pages/inventory/InventoryPage.tsx`
- `const { isSuperAdmin } = useSuperAdmin();` を足す（`frontend/src/hooks/useSuperAdmin.ts`）。
- `const [drawerRow, setDrawerRow] = useState<InventoryRow | null>(null);` を足す。
- DataTable（:593-617）に `onRowClick={isSuperAdmin ? (row) => setDrawerRow(row) : undefined}` を足す。他の props は変えない。
- DataTable の直後に `{drawerRow && <InventoryRowDrawer row={drawerRow} onClose={() => setDrawerRow(null)} />}` を足す。
- ヘッダコメント（:4「public.inventory を表示」）は古いので、「LINE 解析の配信行を表示（ADR-1014）。super admin は行クリックで解析パネル」に直す。

(e) i18n: `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` に同じキーを足す（ADR-027）。

| キー | ja | en |
|---|---|---|
| `inventory.rowDrawer.title` | 解析の詳細 | Analysis details |
| `inventory.rowDrawer.loadError` | 解析結果を読み込めませんでした | Failed to load the analysis result |
| `inventory.rowDrawer.notFound` | この行の解析結果が見つかりません。在庫表を再読み込みしてください | No analysis result for this row. Reload the inventory table |
| `inventory.rowDrawer.itemTab` | {{n}}件目 | Item {{n}} |

読み込み中の文言は、既存の共通キーがあればそれを使い、新しく作らない。

## 5. 代替案と選んだ理由

| 案 | 内容 | 採否 |
|---|---|---|
| A（採用） | 行の定義に元 ID の列を1つ足す。既存の解析結果 API を ID 指定で使う | 行の定義と解析結果の読み方が、それぞれ1か所のまま。写しを作らない |
| B | 在庫表 API が、解析パネルの中身まで返す | 在庫表 API は products.view（一般利用者）向け。原文・内部の判定を一般利用者に返すことになるので、不採用 |
| C | 先頭行の ar.id から、まとめ条件を再計算して兄弟の行を探す新 API | まとめ条件が2か所になる（SSOT 違反）。不採用 |
| D | パネル用に別の部品を作る | 要確認パネルと二重管理になる。不採用 |

## 6. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| B1 まとめなしの行の `extraction_item_ids` が、その行の ei.id 1件 | `backend/tests/test_inventory_distribution_rows_pg.py` に追加（pg 実体） |
| B2 まとめた行の `extraction_item_ids` が、組の全 ei.id（件数＝merged_count、並びは sort_ord 順） | 同上 |
| B3 `_base_from()` の出力が、変更前の `_BASE_FROM` と文字単位で同じ | `backend/tests/test_tcg_analysis_review.py` に追加（変更前の文字列を固定） |
| B4 GAS 出力（fetch_output_rows）が変更前と同じ | 既存 `backend/tests/test_inventory_distribution_rows_pg.py` の GAS 同一性テストが緑。`test_distribution_rows_sql_is_pinned` は、固定値を新しい SQL に更新する（差分は §4-1 の3か所だけであることを PR で示す） |
| B5 ID 指定で、非アクティブな投稿の行も1件取れる。ID を指定しないときは、今までどおり非アクティブを除く | `backend/tests/test_tcg_analysis_review.py` に追加（pg 実体。無ければ同ファイルの既存方式） |
| B6 ID 指定で、super admin 以外は 403。UUID でない値は 422。51件は 422 | 同上 |
| F1 super admin が行をクリックすると、パネルが開き、原文・Gemini・システムの3つが出る | 新規 `frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx` |
| F2 super admin 以外は、行をクリックしてもパネルが開かない（API を呼ばない） | 同上 |
| F3 チェック欄のクリックでは、パネルが開かない | 同上 |
| F4 まとめた行（ID 2件）は、タブ2つで切り替えられる | 新規 `frontend/src/features/inventory/InventoryRowDrawer.test.tsx` |
| F5 viewOnly では、「確認済み」・取消・修正ウィザードが出ない | `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx` に追加 |
| F6 viewOnly 無しでは、今までの表示・操作のまま | 既存 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`・`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.acked.test.tsx`, `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`, `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.test.tsx` が全部緑 |
| F7 i18n・UI ガバナンス違反が0件 | `.github/workflows/frontend-check.yml`・`.github/workflows/ui-governance-gate.yml` が緑、`npm run lint` |
| P1 本番で、super admin が在庫表の行をクリックすると3つが出る | 本番反映後、Evaluator（Sonnet）が tenant_001 で確認し、`docs/ai-agents/evidence-registry.md` に記録。ログインできない場合は、本番 API を super admin トークンで叩いた結果で代える。代えた事実を明記する |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 配信行 SQL の変更で、GAS シートや在庫表の件数が変わる | WHERE・まとめ条件は触らず、列を足すだけにする。B4 の同一性テストで確認する |
| window の array_agg が重くなる | まとめの組は1投稿内の少数行。merge=False では window を通らない（ARRAY[item_key] だけ）。本番反映後、在庫表 API の応答時間を反映前と比べる（反映前に1回測ってから出す） |
| 一般利用者の在庫表 API に、内部 ID（UUID）が載る | 中身（原文・判定）は返さない。ID で引く API は super admin 限定（403）。B6 で確認する |
| ReviewItemDrawer の変更で、要確認パネルが壊れる | 追加 props は省略時に変更前と同じ動きにする。F6 で既存テストが全部緑であることを確認する |
| 本番で解析結果が再解析で入れ替わり、パネルが0件 | notFound の文言を出す（F の0件分岐） |

## 8. 外部・過去事例の参照と我々への応用

- 該当なし。理由: 社内に同じ仕組み（要確認パネル `ReviewItemDrawer`）が既にあり、それを再利用する変更だから。外部の方式を新しく取り入れる判断は無い。
- 社内の過去事例として、ADR-1014（在庫表とシートの行の定義を1か所にした）の方針に従う。

## 9. 次便（直す機能）の判断材料（PO 判断待ち）

- パネルの「直す」は、`analysis_results` を直接書き換える（`backend/app/services/item_corrections_svc.py:59-73`、`backend/app/services/v102_human_decisions_svc.py:604-620`）。
- シートへの反映は `schedule_distribution` が担う（`backend/app/tasks/tcg_extraction.py:670-693`）。`TCG_AUTO_DISTRIBUTE=1` のときだけ動く（本番値は未確認）。
- アプリ在庫表には自動更新が無い。
- 採否を PO に確認してから、別便で設計する。

## 10. 計画

1. 実装（Sonnet）: §4 のとおり。§6 のテストを追加する。
2. ローカル検証: backend pytest（対象ファイル）、frontend build/lint/test:unit。
3. PR を `--base main` で起票する。危険パス（migrations/・deploy.yml・本番 scripts/）は含まない。
4. 審査:
   - Opus がコード審査する。
   - CI 全緑を確認する。
   - GO 記録をコメントする（`GO: POの委任に基づくClaude Opus発行 2026-10-16`）。
   - マージする。
5. 本番反映を確認する（deploy の実行・時刻・P1）。

## 11. 審査記録（Architect・同一 AI による自己審査）

- 判定: APPROVE（2026-10-16、Opus）
- 確認したこと:
  - 行の定義は1か所のまま（§4-1 は列を足すだけ）。
  - 解析結果の読み方も1か所のまま（`fetch_analysis_results` の再利用）。
  - 権限境界は変えていない（super admin 限定のまま）。
  - UI は既存の金型だけで作る。
  - 受け入れ基準のすべてに検証方法がある。
  - recon の file:line は、Opus が要所（svc :52-62/:165-269、distribution :240-371、inventory_offers :150-311、schemas :129-159、router :110-140）を実物で再確認した。
- 改訂 r2（2026-10-16、実装中の停止を受けて）:
  - 初版の `_base_from` は、`is_active = TRUE` を f-string の外に出していた。
  - そのため、既存の守りテスト `backend/tests/test_tcg_is_active_filter.py:48-79` が落ちた。このテストは、source_messages を参照する SQL に `is_active = TRUE` か `is_current = TRUE` があることを確かめる。
  - 守りテストは変えない。条件式を f-string の中に置き、ID 指定のときは `ar.is_current = TRUE` で絞る形にした。これは配信行（`backend/app/services/tcg_distribution_svc.py:334`）と同じ絞り方で、ADR-158 の型にあたる。
  - 在庫表の行はすべて is_current なので、取りこぼしは出ない。
  - `_BASE_FROM` の使用は、count・providers・items の内側と外側の4か所。4か所すべてを `base_from` に置き換える。
  - B6 の「super admin 以外は 403」は、認証なしの確認で代えない。`backend/tests/test_inventory_offers_rbac.py` 等の、既存の非 super admin ユーザーの差し替え方式で確認する。
- 未解決（実装時に事実で確定し、合わなければ停止）:
  - `_BASE_FROM` の他ファイル参照の有無。
  - ItemComparison に渡す行選択 props の正確な名前。
  - 読み込み中に使う既存の金型・文言キー。

## 維持の仕組み

- 守り手: `.github/workflows/test.yml`（backend pytest）、`.github/workflows/frontend-check.yml`（frontend の型・lint・unit）、`.github/workflows/ui-governance-gate.yml`（金型外のハードコード）
- 対象:
  - 在庫の行に元 ID が付くこと（B1/B2）
  - GAS 出力が変わらないこと（B4）
  - ID 指定 API の権限（B6）
  - 見るだけモードで操作が出ないこと（F5）
  - 要確認パネルの既存動作（F6）
