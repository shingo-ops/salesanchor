# 実装カード: 状態未解決3列の実数値化

状態: **PO実装承認待ち**（承認前に着手しない）
設計: `docs/handoff/condition-fallback-count/design.md`／調査: `recon.md`
worktree: `/Users/tanizawashingo/worktrees/salesanchor/release-condition-fallback-count`（ブランチ `release/condition-fallback-count`、起点 origin/main `8cb3708fb`）

## 着手前の点検（どれか不一致なら全停止して報告）
1. `./scripts/dev/executor-preflight.sh` が OK
2. `sed -n '60p' backend/app/services/tcg_supplier_quality_svc.py` が `"condition_fallback_count": None,  # Q8実測不能 — GAS と同じく null 固定`
3. `sed -n '853p;877p;880p' backend/app/services/tcg_analyzer_svc.py` が順に `b4 = b4_prefix + "R4:単位既定"`／`return ("Searched pack", cid, b4_prefix + "R5:パック既定")`／`return ("FLAG_SINGLE", cid, b4 + ":単位不明")`
4. `sed -n '286p' backend/app/services/tcg_condition_review_svc.py` に `condition_basis='MANUAL_CONDITION_REVIEW'`

## 変更1: BE サービス `backend/app/services/tcg_supplier_quality_svc.py`
- :13 の直後に定数を追加:
```python
# condition_basis の書式（生成元: tcg_analyzer_svc.py:853,877,880 / tcg_condition_review_svc.py:286）。
# 接頭辞「単品語あり・要確認(<kw>),」が付く場合があるため末尾一致で判定する。
CONDITION_FALLBACK_PATTERN = r"(^|,)(R4:単位既定(:単位不明)?|R5:パック既定)$"
CONDITION_GIVE_UP_PATTERN = r"(^|,)R4:単位既定:単位不明$"
CONDITION_MANUAL_BASIS = "MANUAL_CONDITION_REVIEW"
```
- SQL（:39-40 の後）に3列追加。パターンはバインド引数で渡す（f-string 埋め込み禁止）:
```sql
COUNT(CASE WHEN ar.condition_basis ~ :fallback_pattern THEN 1 END) AS condition_fallback_count,
COUNT(CASE WHEN ar.condition_basis ~ :give_up_pattern THEN 1 END)  AS condition_give_up_count,
COUNT(CASE WHEN ar.condition_basis = :manual_basis THEN 1 END)     AS condition_manual_reviewed_count
```
- :51 を `db.execute(text(sql), {"fallback_pattern": ..., "give_up_pattern": ..., "manual_basis": ...})` に変更
- :60 を `"condition_fallback_count": row.condition_fallback_count,` に置換し、`condition_give_up_count` / `condition_manual_reviewed_count` を同様に追加
- docstring（:23-27）に3述語を追記
- 触らない: `fetch_supplier_source`（:66-104）、既存4列の CASE 式

## 変更2: API スキーマ `backend/app/routers/tcg_supplier_quality.py:35-42`
- :42 を `condition_fallback_count: int | None` のまま、コメントを `# condition_basis 末尾一致で集計（tcg_supplier_quality_svc 定数参照）` に更新
- 直後に `condition_give_up_count: int | None = None`、`condition_manual_reviewed_count: int | None = None` を追加（旧クライアント互換のため Optional）

## 変更3: FE 型・列 `frontend/src/features/tcg-analysis-review/supplierQuality.ts`
- :8-10 のコメントを「condition_basis 末尾一致で集計（BE: tcg_supplier_quality_svc.py）」に更新、+2フィールドの説明1行ずつ
- 型（:25 の後）に `conditionGiveUpCount: number | null;`、`conditionManualReviewedCount: number | null;`
- 列ID（:34）に `| 'CONDITION_GIVE_UP_COUNT' | 'CONDITION_MANUAL_REVIEWED_COUNT'`
- 列定義（:43 の後）に2行、`minWidth: '9rem', visible: true`、ラベルは `columns.conditionGiveUpCount` / `columns.conditionManualReviewedCount`

## 変更4: FE 表示 `frontend/src/features/tcg-analysis-review/SupplierQualityList.tsx`
- :14 ApiSummary に `condition_give_up_count?: number | null; condition_manual_reviewed_count?: number | null;`
- :29 mapSummary に `conditionGiveUpCount: raw.condition_give_up_count ?? null,` / `conditionManualReviewedCount: raw.condition_manual_reviewed_count ?? null,`
- :62-63 の case の後に2 case を追加（既存と同じ `!== null ? 値 : t("superAdmin.supplierQuality.conditionPending")` 形）
- 既存 :62-63 は変更しない

## 変更5: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:428-451`
- :433 の後に `condition_give_up_count?: number | null; condition_manual_reviewed_count?: number | null;`
- :450 の後に変更4と同じ2行のマッピング
- それ以外は触らない（本店に別作業の未保存変更あり。コンフリクトしたら停止報告）

## 変更6: i18n `frontend/src/locales/ja.json` / `en.json`（`superAdmin.supplierQuality.columns`）
| キー | ja | en |
|---|---|---|
| `conditionFallbackCount`（値変更） | 状態未解決 | Condition Unresolved |
| `conditionGiveUpCount`（新） | うち完全お手上げ | of which No Clue |
| `conditionManualReviewedCount`（新） | 人が確認済み | Manually Reviewed |
- `conditionPending` は残す（null 時の表示に継続使用）

## 変更7: テスト `backend/tests/test_tcg_supplier_quality.py`
- `_DUMMY_SUMMARIES`（:22-41）の `condition_fallback_count` を数値に、新2キーを追加
- :126 の期待キー集合に新2キー追加
- 新規テスト: 定数パターンを Python `re.search` で検証
  - 一致(fallback): `R4:単位既定`、`R4:単位既定:単位不明`、`R5:パック既定`、`単品語あり・要確認(バラ),R4:単位既定`、`単品語あり・要確認(バラ),R4:単位既定:単位不明`
  - 不一致(fallback): `R4:未開封`、`R3:MEMO:サーチ済`、`R2:開封`、`MANUAL_CONDITION_REVIEW`、`EMPTY_BOX:explicit`、`None`/空
  - 一致(give_up): `R4:単位既定:単位不明`、接頭辞付き同値のみ。不一致: `R4:単位既定`、`R5:パック既定`
- 新規テスト: サービス関数が `db.execute` に3つのバインド引数を渡すこと（AsyncMock で引数検証）

## 自己検証（生出力を報告）
1. `cd backend && pytest tests/test_tcg_supplier_quality.py tests/test_tcg_is_active_filter.py -q`
2. `cd backend && make lint`
3. `cd frontend && npx tsc --noEmit && npm run lint`
4. i18n キー一致: `node -e` で ja/en の `superAdmin.supplierQuality.columns` キー集合が一致
5. `git diff --stat origin/main...HEAD` が上記7ファイル＋docs のみ

## 完了条件・停止条件
- 完了: 上記自己検証が全て緑、PR を `--base main` で起票（shingo-cc 名義、`### 標準ワークフロー確認` 必須）。マージはしない。
- 停止: 点検不一致／想定外ファイルの変更が必要／テストが既存理由で赤／コンフリクト。事実を返して設計者判断を仰ぐ。
