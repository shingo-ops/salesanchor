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

---

## 12. 便2（Gemini 列の「—」表示・システム商品名・Gemini の要約）

根拠: recon.md「便2 追補 recon」R2-1〜R2-4。PO 決定（2026-10-16）:「geminiは原文を抽出するだけなので行番号と数量と単価以外は"-"と表示するのが正解でシステムが未解決になっているのは修正したい。それとgeminiの要約もスライドページ内に表示することは出来る？見える化したい」→「合意」。

### 12-1 目的と KGI
- K2-1: v102 の行の比較表で、Gemini 列の商品名・単位・状態・メモが「—」になる（「未解決」0件）。行番号・数量・単価の Gemini 列は今と同じ値。
- K2-2: 比較表の「システム最終結果」の商品名が商品マスタ名（system.product_title）になる。採用元は「System確定」。マスタ未紐付けの行だけ「未解決」。
- K2-3: スライドに「Geminiの要約」欄が出て、その投稿の最新の完了試行の要約（英語原文）が読める。記録が無い投稿は「要約の記録はありません」。

### 12-2 対象と対象外
- 対象: ItemComparison.tsx（readOnly と編集側の両方）、ReviewItemDrawer.tsx（要約欄）、feature の CSS、ja/en.json（新キー2つ）、tcg_analysis_review_svc.py（items_sql に LATERAL・応答に thought_summaries）、routers/tcg_analysis_review.py（AnalysisResultItem に任意フィールド）、openapi.json 再生成、テスト。
- 対象外: v6 の行の表示（値があるので今のまま）、要約の翻訳、「要確認の商品」「理由はありません」見出し（ReviewItemDrawer.tsx:151,157）、manual_values の応答落ち疑い、直す機能（§9・PO 未回答）、DB 変更（migration なし）。

### 12-3 変更前 → 変更後
| 場所 | 変更前 | 変更後 |
|---|---|---|
| Gemini 列 商品名/単位/状態/メモ（v102 行） | 未解決 | — |
| Gemini 列 行番号/数量/単価 | 値 | 値（不変） |
| Gemini 列（v6 行） | 値 or 未解決 | 不変 |
| システム最終結果 商品名 | gemini.name or 未解決／採用元 Gemini抽出値を採用 | system.product_title or 未解決／採用元 System確定 |
| スライド下部 | なし | 「Geminiの要約」見出し＋本文（pre-wrap・高さ上限でスクロール）／記録なし文言 |

### 12-4 技術設計
- (A) ItemComparison.tsx:56-57 の Gemini 列: `item.is_v102 && ["name","unit","state","memo"] に該当` のとき既存 `na`（:52 `tcgAnalysisReview.notApplicable`）を出す。:103 付近の編集側にも同じ判定を当てる。判定は1つの関数にまとめ、両方から呼ぶ（判定の分散禁止）。
- (B) ItemComparison.tsx:38-39 systemCell の name: 値 `item.system.product_title || unresolved`、採用元 `tcgAnalysisReview.systemConfirmed`。v6/v102 を問わない（システムの最終結果は商品マスタが正本。在庫表タイトル tcg_distribution_svc.py:293 と同じ出どころ＝SSOT）。数量・単価は不変。
- (C) バックエンド: tcg_analysis_review_svc.py の items_sql に
  `LEFT JOIN LATERAL (SELECT ea.thought_summaries FROM extraction_attempts ea WHERE ea.extraction_job_id = ej.id AND ea.phase = 'completed' ORDER BY ea.started_at DESC, ea.id DESC LIMIT 1) eat ON TRUE`
  を足し、SELECT に `eat.thought_summaries` を加える。応答 dict に `"thought_summaries": list[str] | None` を足す。router の AnalysisResultItem に `thought_summaries: list[str] | None = None` を足す。スキーマ修飾は同ファイルの既存 FROM 句と同じ書き方に合わせる（実装時に実物確認、合わなければ停止）。
- (C) フロント: ReviewItemDrawer.tsx の TwoColumn（:192-206）の直後に要約欄。見出しは原文・比較の見出しと同じ既存要素・クラスを使う。本文は `<p>` か `<div>` に feature CSS のクラス（white-space: pre-wrap、max-height と overflow-y: auto、色・余白・文字サイズはデザイントークン変数のみ）。要素が複数なら空行区切りで連結。新 i18n キー `tcgAnalysisReview.geminiSummaryTitle`（Geminiの要約 / Gemini summary）、`tcgAnalysisReview.geminiSummaryEmpty`（要約の記録はありません / No summary recorded）。型 AnalysisReviewItem に `thought_summaries?: string[] | null`。
- 要確認ページも同じ部品なので同じ改善が入る（意図どおり。PO の指摘は共用部品の不具合）。

### 12-5 代替案
- 名前を v102 の Gemini に出させる → 書き写し方式（v102 設計 design.md:72）に反するので不採用。
- 要約を別 API で個別取得 → 往復が増え、読み方が2か所になる。既存 API に1列足す方が SSOT。
- 折りたたみ部品を新設 → 金型が無く、新設は範囲外。高さ上限＋スクロールで足りる。

### 12-6 受け入れ基準と検証方法
| 基準 | 検証方法 |
|---|---|
| A1 v102 行の Gemini 商品名/単位/状態/メモが「—」 | vitest（is_v102=true の行） |
| A2 v102 行の行番号/数量/単価は値のまま | vitest |
| A3 v6 行の Gemini 列は従来どおり | vitest（既存期待値維持） |
| B1 システム商品名=product_title・採用元 System確定 | vitest |
| B2 product_title 空なら「未解決」 | vitest |
| C1 API が最新 completed 試行の thought_summaries を返す（failed・古い completed は選ばない） | pytest（PostgreSQL） |
| C2 試行が無いジョブは null | pytest |
| C3 要約欄に本文が出る／記録なし文言が出る | vitest |
| C4 本番で、ある行の API 値と SQL 直接の値が一致 | 本番 SELECT と比較（証跡ファイル） |
| G1 i18n ja/en 同一キー・ハードコード日本語 0 | frontend lint・check |
| G2 色直値・生要素 0 | UI governance gate・Lint & Dark Mode Check |
| G3 PO 画面確認 | PO 目視 |

### 12-7 リスクと対処
- 応答の重さ: 要約は最大約4KB×20件/ページ。上限500件でも約2MB。許容。
- LATERAL の遅さ: 索引 ix_pub_extraction_attempts_job_started が並びと一致。本番で EXPLAIN（読み取り）を確認する。
- 既存テストの期待値変更: ItemComparison.test.tsx :40,:49,:64-66 を is_v102 の条件で書き換え、v6 側の期待は残す。
- 戻し方: PR を revert（DB 変更なし）。

### 12-8 外部事例
- 該当なし。理由: 社内の表示条件と既存列の追加であり、外部の数値事例が判断を左右しない。

### 12-9 審査記録（Architect・同一 AI による自己審査）
- 判定: APPROVE（2026-10-16、Opus）
- 確認: 正本は商品マスタ（名前）・extraction_attempts（要約）のまま、新しい保存先なし。migration なし。判定関数は1か所。i18n キーは既存1・新規2。権限境界は不変（API の既存権限のまま）。受け入れ基準すべてに検証方法あり。
- 未解決（実装時に事実確定、合わなければ停止）: items_sql のスキーマ修飾の書き方、見出しの既存クラス名、編集側 :103 の正確な位置。

## 13. 便3（在庫表のスライドで直す・直したら DB・シート・閲覧ページへ反映）

根拠: recon.md「便3 追補 recon」R3-1〜R3-7。関連 ADR: ADR-1014（在庫表＝配信行）、ADR-1016（即時反映の合図。topics の対応表は変えない）、ADR-1019（閲覧ページは写しを作らない）、ADR-154、ADR-158、ADR-027、ADR-144。PO 決定（2026-10-16）: 質問「スライドから直したら、DB・シート・閲覧ページも更新されるようにしますか？（y/n）」に「y」。

### 13-1 目的と KGI（○×で判定）
- K3-1: super admin が PC の在庫表で行を押すと、スライドの比較表の行を押して直せる（要確認ページと同じ修正ウィザード）。
- K3-2: 直すと、正本 analysis_results が直る（新しい保存場所は作らない）。
- K3-3: 直したあと、在庫表の一覧が自動で取り直され、直した値で表示される（行が在庫の条件から外れたら一覧から消える）。
- K3-4: 直したあと、シート配信が予約される（v102・v6 とも。本番 TCG_AUTO_DISTRIBUTE=1）。解析中は既存の保留ルールに従う。
- K3-5: 閲覧ページは既存の1分ごとの作り直しで反映される（新しい仕組みは足さない）。
- K3-6: super admin 以外・スマホでは今と同じ（スライドは開かない）。

### 13-2 対象と対象外
- 対象（フロント）: frontend/src/features/inventory/InventoryRowDrawer.tsx、frontend/src/pages/inventory/InventoryPage.tsx（:622 の1行）、テスト（InventoryRowDrawer.test.tsx、InventoryPage.rowdrawer.test.tsx）。
- 対象（バックエンド）: backend/app/routers/item_corrections.py（v6 の商品付け替え・状態の修正のあとに配信予約を積む）、backend/tests の該当テスト。
- 対象外: ReviewItemDrawer・ReviewFixWizard・各フォームの中身（そのまま再利用）、realtime の対応表 topics.py（変更しない）、DB 変更（migration なし）、閲覧ページの仕組み、スマホ、super admin 以外への開放、在庫表の一覧で直接編集すること、「このままで良い（確認済み）」の扱いの変更。

### 13-3 変更前 → 変更後
| 場所 | 変更前 | 変更後 |
|---|---|---|
| 在庫表のスライド | 見るだけ（viewOnly） | 比較表の行を押すと修正ウィザードが出る |
| 直したあとの在庫表 | 自分で絞り込みを変えるまで古いまま | スライドの中身と一覧を自動で取り直す。v102 の再解析が終わった合図（tcg.review）でも、スライドを開いている間は取り直す |
| v6 の行の商品・状態の修正 | シート配信の予約なし（次に誰かが配信を起こすまで出ない） | 値の修正（item_corrections.py:288-290）と同じく配信を予約する |
| タブ（1行に複数の抽出）切替 | 内部の選択状態が持ち越される | タブごとに作り直す（key に extraction_item_id） |

### 13-4 技術設計
- (F1) InventoryRowDrawer.tsx: `viewOnly` を外す。Props に `onChanged: () => void` を足す。`refresh = async () => { await load(); onChanged(); }` を ReviewItemDrawer の onRefresh に渡す。`<ReviewItemDrawer key={current.extraction_item_id} ...>`。
- (F2) InventoryRowDrawer.tsx: `useRealtimeRefresh([TOPICS.tcgReview], () => { void refresh(); })`。スライドは super admin のときだけ描かれるので、購読も super admin だけ（フック側の変更なし。合図 tcg.review は global で super admin にしか届かない: hub.py:32-41）。
- (F3) InventoryPage.tsx:622: `<InventoryRowDrawer row={drawerRow} onClose={...} onChanged={() => { void load(); }} />`。load は既存の一覧取得（:195-243、古い応答を捨てる連番つき）をそのまま使う。新しい state は足さない。
- (B1) item_corrections.py: 商品付け替え（:180-181）と状態（:159-160 → :124-131）で、`saved > 0` かつ v102 でないとき `await run_in_threadpool(schedule_distribution)` を呼ぶ。書き方は :288-290 と同じ。v102 は今どおり再解析→再解析の最後で配信予約（二重予約は Redis nx で1回に畳まれる: tcg_extraction.py:670-693）。
- 正本: analysis_results（直す API が同じ取引で UPDATE）。在庫表・シート・閲覧ページはすべて analysis_results から作る（ADR-1014）。写し・新しい保存場所なし（SSOT）。
- 部品: 既存の ReviewItemDrawer・ReviewFixWizard・Tabs をそのまま使う。新しい UI 部品・文言・色なし（i18n キー追加なし）。
- B1 は要確認ページの v6 の修正にも効く（同じ API）。シートに出ないという同じ欠けが直るだけで、画面の動きは変わらない。

### 13-5 代替案と選んだ理由
- 在庫表のページ全体で合図を購読 → 再接続通知が super admin 以外にも届き、一覧の取り直しが増える（useRealtimeRefresh.ts:46-48、enabled 引数なし）。スライド内での購読なら super admin だけ。不採用。
- v6 の修正で再解析も積む → v6 の再解析は別の仕組みで、今回の依頼（反映）には配信予約で足りる。値の修正の v6 経路（:288-290）と同じ扱いにそろえる。
- 定期配信を beat に足す → 全体の負荷と挙動が変わる。範囲外。

### 13-6 受け入れ基準と検証方法
| 基準 | 検証方法 |
|---|---|
| E1 在庫表のスライドで比較表の行を押すと修正ウィザードが出る（viewOnly でない） | vitest（InventoryRowDrawer.test.tsx） |
| E2 修正のあと onRefresh で、スライドの再取得と onChanged が両方呼ばれる | vitest |
| E3 tcg.review の合図でスライドが取り直される | vitest（useRealtimeRefresh を差し替え） |
| E4 タブ切替で ReviewItemDrawer が作り直される（選択状態が残らない） | vitest |
| E5 InventoryPage が onChanged で一覧を取り直す | vitest（InventoryPage.rowdrawer.test.tsx） |
| E6 super admin 以外・スマホではスライドが開かない（既存テスト維持） | vitest 既存 |
| B1 v6 の商品付け替え（saved>0）で schedule_distribution が1回、再解析は0回 | pytest（test_v102_value_overrides.py:264 と同じ型） |
| B2 v6 の状態の修正（saved>0）で schedule_distribution が1回 | pytest |
| B3 v102 の付け替えは今どおり再解析だけ（router から schedule_distribution を直接呼ばない） | pytest |
| B4 saved=0 なら配信予約なし | pytest |
| P1 本番: 新しい bundle に InventoryRowDrawer の viewOnly 指定が無い・backend に B1 の行がある | 本番のファイルを grep（証跡） |
| P2 本番で直したあと配信が走る | Opus は本番データを試しに直さない（実データを変えるため）。代わりに既存の要確認ページ経路の配信ログ（scheduled_distribution）を観測できたときに記録。PO が実際に直したときの確認を G3 とする |
| G1 i18n・UI ガバナンス・lint・build | CI |
| G3 PO 画面確認（直して一覧とシートが変わる） | PO 目視 |

### 13-7 リスクと対処
- 誤操作で在庫のデータを直してしまう: 書き込みは super admin だけ（既存の権限）。修正は item_corrections に履歴が残り、要確認ページと同じ手順で直し直せる。
- 直した行が在庫の条件から外れて一覧から消える（例: 販売状況を Sold out）: スライドは ID で取り直すので開いたまま中身は見える。一覧からは消えるのが正しい動き（ADR-1014）。
- 配信の二重予約: Redis nx で60秒に1回へ畳まれる（既存テスト test_v102_human_decisions.py:46-76）。
- v102 の再解析中は配信が保留（既存の安全装置）。再解析後に予約されるので最終的に出る。
- 戻し方: PR を revert（DB 変更なし・設定変更なし）。

### 13-8 外部事例
- 該当なし。理由: 既存の修正部品と既存の配信予約を在庫表から呼べるようにする社内の配線変更で、外部の数値事例が判断を左右しない。

### 13-9 審査記録（Architect・同一 AI による自己審査）
- 判定: APPROVE（2026-10-16、Opus）
- 確認: 正本は analysis_results のまま、新しい保存場所・写しなし。migration なし。新しい UI 部品・文言なし。権限境界は不変（書き込み API は既存の require_super_admin、スライドは super admin・PC のみ）。v6 の配信予約は既存の v6 値修正（:288-290）と同じ書き方。受け入れ基準すべてに検証方法あり。
- 未解決（実装時に事実確定、合わなければ停止）: InventoryRowDrawer.test.tsx・InventoryPage.rowdrawer.test.tsx の既存の viewOnly 前提の期待値（変える場合は理由を残す）、router の状態の経路で v6 判定に使う既存関数（:124-131 の v102_job_id_of_item の戻り値で判定する）。

## 14. 便4: 原文だけのタブ（2026-10-16・PO「y」）

### 14-1 目的（PO の言葉）
「在庫表のスライドページにタブを追加…クリックしたら原文だけが表示されるように…スタッフの確認用…先程作ったページはsuperadminのみ…原文だけのページはadminとadminが権限付与して在庫表が見れるユーザーは全員見れるようにしたい」
- super admin: スライドに「解析」「原文」の2タブ（既定は解析＝今のまま）。
- 在庫表を見られる人（products.view。recon R4-2）: 原文だけのスライド。新しい権限キーは作らない。
- 原文は投稿全体を出し、在庫行に当たる行に色を付ける（ShadowSourcePane。recon R4-3）。送信者名は出さない（raw_text に入っていない）。
- PC のみ（スマホでは開かない＝今と同じ）。

### 14-2 対象 / 対象外
- 対象: backend/app/routers/inventory_offers.py（新 API 1本）、backend/app/schemas/inventory_offers.py（応答の型）、backend/tests/（新テスト）、frontend/src/pages/inventory/InventoryPage.tsx（入口の門）、frontend/src/pages/inventory/InventoryRowDrawer.tsx（タブと原文表示）、同テスト2本、frontend/src/locales/ja.json・en.json。
- 対象外: DB・migration（なし）、/tcg/analysis-results と書き込み API の権限（super admin のまま）、配信行の定義 distribution_rows_parts 本体（使い回すだけで変えない）、在庫表そのもののテナント分け（R4-4。既存の範囲外課題）、スマホ表示。

### 14-3 変更前 → 変更後
- 入口 InventoryPage.tsx:603: `isSuperAdmin && !isMobile ? open : undefined` → `!isMobile ? open : undefined`。`<InventoryRowDrawer>` に `isSuperAdmin` を渡す。
- 新 API: `GET /inventory/raw-texts?extraction_item_ids=<id>&extraction_item_ids=…`
  - 門: `dependencies=[Depends(require_permission("products.view"))]`（GET /inventory と同じ）。
  - 件数: 1〜50 件。0 件・51 件以上は 422。
  - 守り: GET /inventory と同じ組み立て（load_distribution_settings → _max_age_hours → include_flag_single → _age_window → distribution_rows_parts）で head（dist_base）を作り、`SELECT DISTINCT item_key FROM dist_base WHERE item_key = ANY(:ids)` に入った ID だけを source_messages／extraction_items と結んで返す。WHERE の写しを作らない（ADR-1014: 定義は1か所）。max_age_hours が None なら配信行は無い扱い。
  - 返す項目: `extraction_item_id, raw_text, line_start, line_end` だけ。gemini・system・要約・修正履歴・送信者・仕入先 ID は返さない。
  - 該当 0 件は 404（`{"detail": "not_found"}`）。
- InventoryRowDrawer:
  - props に `isSuperAdmin: boolean` を足す。
  - super admin: Drawer の headerSlot に Tabs（variant="underline"）「解析｜原文」。解析タブは今のまま（/tcg/analysis-results・ReviewItemDrawer・直す機能・tcg.review 購読）。原文タブを開いたときだけ新 API を呼ぶ。
  - 非 super admin: タブを出さず原文だけ。/tcg/analysis-results は呼ばない・tcg.review を購読しない。
  - 原文表示: 件ごとに `<ShadowSourcePane rawText blockRange={{start: line_start, end: line_end}} />`（line が null なら blockRange なし）。まとめ行（2件以上）は既存の件 pill タブ（inventory.rowDrawer.itemTab）で切り替える。
  - エラー: 403→forbidden 表示（既存）、404→notFound（既存キー）、その他→loadError（既存キー）。
- i18n 追加（ja/en 同時）: `inventory.rowDrawer.tabAnalysis`（解析 / Analysis）、`inventory.rowDrawer.tabRawText`（原文 / Original text）。

### 14-4 代替案と選んだ理由
- (a) /tcg/analysis-results の門を products.view に緩める → gemini・system・要約まで出るので不採用（スタッフは原文だけ）。
- (b) /inventory の応答に raw_text を足す → 一覧全行に長文が乗り重い・ページ全体の応答が変わるので不採用。
- (c) 新しい読み取り専用 API（採用）: 返す項目を絞れ、門を在庫一覧と同じにでき、行の定義を使い回せる。

### 14-5 リスクと対処
- ID 総当たりで在庫表に無い投稿を読む → dist_base の item_key に入る ID だけ返す（B2 で固定）。
- テナント: 原文の表にテナント列が無く在庫表自体が分かれていない（R4-4）。今回は「在庫表に出ている行の原文だけ」が守りの範囲。完了報告で PO に事実として伝える。
- super admin の既存挙動を壊す → 既定タブは解析・既存テストを維持（E1）。
- 金型外の部品 → Tabs・Drawer・ShadowSourcePane の既存部品のみ。色直値・生要素なし（ADR-144）。

### 14-6 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| E1 super admin は「解析｜原文」2タブ・既定は解析・既存の挙動維持 | vitest InventoryRowDrawer.test.tsx（既存テスト全緑＋タブ表示） |
| E2 原文タブで GET /inventory/raw-texts を呼び、該当行を強調表示 | vitest（API 呼び出し引数・ShadowSourcePane に blockRange） |
| E3 非 super admin は原文だけ・/tcg/analysis-results 0 回 | vitest（呼び出し回数 0・タブなし） |
| E4 非 super admin も PC でクリックで開く・スマホは開かない | vitest InventoryPage.rowdrawer.test.tsx（F2 を書き換え） |
| E5 まとめ行は原文でも件タブ | vitest |
| B1 products.view 無しは 403・有りは 200 | pytest（RBAC 前例 test_inventory_offers_rbac.py の形） |
| B2 配信行に無い ID は返さない・全部無ければ 404 | pytest（実 PG 前例 test_inventory_distribution_rows_pg.py の形、または dist_base 呼び出しを固定した単体） |
| B3 返す項目は 4 つだけ | pytest（キー集合の一致） |
| B4 0 件・51 件は 422 | pytest |
| P1 本番反映（bundle に tabRawText 文言・新 API が未認証で 401） | curl 本番 |
| G1 CI 全緑（i18n・UI ガバナンス・ADR index 等） | gh pr checks |
| G3 PO がスタッフのアカウントで原文スライドを目視 | PO 目視（完了後に依頼） |

### 14-7 外部事例
不要。社内の既存部品（ShadowSourcePane・Tabs）と既存の権限キー（products.view）の組み合わせで、新しい技術選択が無いため。

### 14-8 維持する仕組み
- 行の定義は distribution_rows_parts の1か所（ADR-1014）。原文 API はそれを呼ぶだけなので、定義が変われば自動で追従。
- 権限は products.view 1つ。admin のロール設定画面で付け外しすれば原文スライドの可否も変わる。
- テスト B1〜B4・E1〜E5 が CI で毎回回る。

### 14-9 設計審査（Opus・同一AIの自己審査）
- 判定: APPROVE。
- 根拠: 門（products.view）は GET /inventory と同一（R4-2）。行の判定は dist_base の再利用で写しなし（R4-4・ADR-1014）。返す項目は限定（gemini 等を出さない）。既存 super admin 挙動は既定タブで不変。部品はすべて金型（ADR-144）、文言は i18n（ADR-027）。migration なし・revert で戻せる。
- 未解決: 在庫表そのもののテナント分け（既存課題・今回範囲外）。G3 は PO 目視待ち。
