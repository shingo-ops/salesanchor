# card: 便1-コード 状態マスタの CSV 取り込みを 3 つの権限で守る（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 取り込みの権限の穴を塞ぐ（＋catalog の鍵の付け替え） |
| 5 | 土台のブランチ | ○ `origin/main`（§0） |
| 6 | 形は例で示す | ○ §1・§2 に変更後のコード |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ 触ってよいファイル 8 つ（§1 の 4・§2 の 3・§5 の報告 1） |
| 9 | 出力の上限 | ○ tail -80 |
| 10 | 受付と終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-04 origin/main 996af2f0e の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Write/Edit・見張りで止まったら言い換えない | ○ |

- 設計: [design.md](design.md) §4-1・§6（設計審査 3 回目 APPROVE・[review-opus.md](review-opus.md)）
- PO の実装承認: 2026-11-04 チャット「1」（作る作業に進む）
- 作業ブランチ: `release/permission-keys-conditions-code`（`origin/main` から新しく作る）。この設計書のブランチ（`release/permission-keys-conditions-categories`）には書かない。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
次の行が、そのとおりの文字列であること。`grep -n` の結果を報告に貼る。
| ファイル | 想定 |
|---|---|
| `backend/app/routers/conditions.py` | `require_permission("work_items.view")` が 1 か所（catalog） |
| `backend/app/routers/conditions.py` | `"/import/preview"` と `"/import/commit"` の 2 経路が `dependencies=[Depends(require_permission("conditions.view"))]` |
| `backend/app/auth/dependencies.py` | `def require_permission(` があり、その関数の最後が `return checker` |
| `frontend/src/pages/conditions/ConditionImportPage.tsx` | `const canImport = hasPermission("conditions.view");` |
| `frontend/src/pages/conditions/ConditionsPage.tsx` | `data-testid="conditions-import"` のボタンが、`hasPermission("conditions.view") ?` の枝の中に条件なしで出ている |
| `backend/tests/test_order_purchase_details.py` | `patch("app.auth.dependencies.load_user_permissions"` を使う試験がある（前例） |

## §1 コードの変更（4 ファイル）
(1) `backend/app/auth/dependencies.py` の `require_permission`
- `return checker` の直前に 1 行足す。判定の中身は変えない。
```python
    checker.required_permission_keys = frozenset(required)  # type: ignore[attr-defined]
    return checker
```
- `required` は関数の中で求めるキーを入れている `set[str]`（2026-11-04 実物 `required: set[str] = set(permission_keys)`）。

(2) `backend/app/routers/conditions.py`
- catalog: `require_permission("work_items.view")` → `require_permission("conditions.view")`
- `/import/preview` と `/import/commit` の両方:
```python
    dependencies=[
        Depends(require_permission("conditions.create")),
        Depends(require_permission("conditions.update")),
        Depends(require_permission("conditions.delete")),
    ],
```
- ほかの経路（一覧・1 件・登録・編集・削除・CSV 出力・別名）は変えない。

(3) `frontend/src/pages/conditions/ConditionImportPage.tsx`
```tsx
  const canImport =
    hasPermission("conditions.create") && hasPermission("conditions.update") && hasPermission("conditions.delete");
```

(4) `frontend/src/pages/conditions/ConditionsPage.tsx`
- `data-testid="conditions-import"` のボタンだけを、次の条件で包む。ボタンの部品・文言・`data-testid`・`onClick` は変えない。
```tsx
            {hasPermission("conditions.create") && hasPermission("conditions.update") && hasPermission("conditions.delete") && (
              <HeaderButton variant="primary" data-testid="conditions-import" onClick={() => navigate("/management-center/conditions/import")}>
                {t("conditionCsv.importButton")}
              </HeaderButton>
            )}
```
- CSV 出力ボタン（`data-testid="conditions-export"`）は変えない。

触らない: `product_categories.py`・商品カテゴリの画面・`ManagementCenterPage.tsx`・`load_user_permissions`・翻訳ファイル・CSS・`components/`。

## §2 試験（新しいファイル 3 つ）
(A) `backend/tests/test_conditions_permission_keys.py`（DB を使わない）
- `from app.main import app` の `app.routes` から経路を探し、`route.dependant.dependencies` の `call` が `required_permission_keys` を持つものを集める。
- T1: `POST /api/v1/conditions/import/commit` の集合が `[{"conditions.create"}, {"conditions.update"}, {"conditions.delete"}]`（順不同）。
- T2: `POST /api/v1/conditions/import/preview` も同じ。
- T3: `GET /api/v1/conditions/catalog` が `[{"conditions.view"}]`。
- T4: パスが `/api/v1/conditions` または `/api/v1/product-categories` で始まる全経路で、求めるキーがすべて次の 7 つのどれか。`required_permission_keys` を持たない依存は飛ばす。
  - `conditions.view` `conditions.create` `conditions.update` `conditions.delete` `product_categories.view` `product_categories.edit` `product_categories.delete`
- 経路の前置きが `/api/v1` でなければ、実物の前置きに合わせ、報告に書く。

(B) `backend/tests/test_conditions_import_permission.py`（client の試験）
- 前例 `test_order_purchase_details.py` の `patch("app.auth.dependencies.load_user_permissions", ...)` の形をそのまま使い、試験の中だけ持っている権限を絞る。
- 送る CSV: 名前 `c.csv`、中身 `code,canonical\n`。commit の digest は文字列 `mismatch`。
- T5: `{"conditions.view"}` だけ → preview と commit がどちらも 403。
- T6: `{"conditions.view","conditions.create","conditions.update"}`・`{"conditions.view","conditions.create","conditions.delete"}`・`{"conditions.view","conditions.update","conditions.delete"}` の 3 組 → preview と commit がどちらも 403（parametrize）。
- T7: 4 つ全部 → preview は 200 で JSON の `total` が 0。commit は 409。
- 番号はちょうどの値で確かめる（`!= 403` で済ませない）。
- 送り方（multipart の欄の名前、commit の digest の渡し方）は `conditions.py` の該当の関数の引数を読んで合わせる。

(C) `frontend/src/pages/conditions/ConditionImportPage.test.tsx`
- 前例 `frontend/src/pages/management-center/ManagementCenterPage.test.tsx` の形（`vi.mock("../../hooks/usePermissions", () => ({ usePermissions: vi.fn() }))`、`MemoryRouter`、`i18n.changeLanguage("en")`）。
- 試験 1: `hasPermission` が `conditions.view` だけ真 → 拒否の文（`role="alert"`）が出て、取り込みパネルの入力が出ない。
- 試験 2: 4 つ全部真 → `role="alert"` が出ない。
- 文言は `i18n.t(...)` で比べ、日本語・英語の直書きをしない。

## §3 確かめ（出力はファイルへ。tail -80 で読む）
```
cd backend && python -m pytest tests/test_conditions_permission_keys.py tests/test_conditions_import_permission.py -q > /tmp/pytest.txt 2>&1; tail -80 /tmp/pytest.txt
cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/conditions/ConditionImportPage.test.tsx > /tmp/vitest.txt 2>&1; tail -80 /tmp/vitest.txt
cd frontend && npx tsc --noEmit -p tsconfig.json > /tmp/tsc.txt 2>&1; tail -80 /tmp/tsc.txt
cd frontend && npx eslint src/pages/conditions > /tmp/eslint.txt 2>&1; tail -80 /tmp/eslint.txt
bash scripts/dev/check-before-submit.sh > /tmp/cbs.txt 2>&1; tail -80 /tmp/cbs.txt
```
- 合格: pytest は失敗 0（新しい試験が全部 passed）。vitest 失敗 0。tsc の誤り 0。eslint の誤り 0。check-before-submit が成功で終わる。
- vitest の設定・tsconfig の名前は 2026-11-04 の `frontend/package.json`（`test:unit`・`build`）の実物。違えば実物に合わせ、報告に書く。

## §4 止まる条件
- 1 段目（NEEDS_DECISION で止まる）: §0 の想定と違う。§1・§2 の触ってよいファイル以外を変えないと通らない。試験の形が前例と合わず、設計（design.md §6）の意図を変えないと書けない。
- 2 段目（BLOCKED で止まる）: 見張り（hook）に止められた（言い換えない）。push が断られた。§3 が 2 回直しても通らない（原因の生出力を報告に貼る）。

## §5 報告
- `docs/handoff/permission-keys-conditions-categories/impl-report-1.md` を作り、同じブランチにコミットして push する。
- 中身: §0 の grep の生出力、変えたファイルの一覧（`git diff --stat origin/main`）、§3 の tail の生出力、最後の HEAD の sha、最後の行に `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>`。
