<!-- rules-ack: 607cd6e7 -->
# 実装カード 便4a — 在庫の商品画面の口（POST /products・PATCH /products）にも9項目の検査を入れる（ADR-1020 定着）

> この文書は何か：ADR-1020 の定着点検（/tmp/CC報告ファイル/master-required-fields/governance/verdict.md の X1）で見つかった抜け道を塞ぐ作業指示書です。在庫の商品画面が使う `POST /products` と `PATCH /products/{id}` は、PostgreSQL では共用の表 `public.products` に書きますが、9項目の検査を通りません。この便では、共用の行（tenant_id が NULL）に対して、作るときは9項目の不足を、直すときは「値か印があった項目を空にする」ことを、便3a と同じ符号の 422 で止めます。画面は便3b の共通関数で言葉にして出します。

- 設計: docs/handoff/master-register-required-fields/design.md（便3「止める」の範囲を、在庫の商品画面の口にも広げる。§2-2 に Opus の技術判断）。ADR-1020 本文:32-38「共用商品を書くすべての入口は check_required_fields を通す」
- PO 承認: PO 2026-10-17「y」（抜け道を塞ぎ、欠け5つを埋める便を設計から本番反映まで進める）
- 対象ADR: ADR-1020、ADR-090（public.products 一本化）、ADR-027（i18n）
- 状態: Opus 自己審査 APPROVE
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／コード審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（在庫の商品画面の口に9項目の検査を入れる） |
| 5 | 起点と作業場所を明示 | ○（§10 手順1） |
| 6 | 書式は実例で示した | ○（§4 に完成形のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main の実物。/tmp/CC報告ファイル/master-required-fields/bin4a/recon/） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | 新しい作業場所は `scripts/new-worktree.sh` で作る | ○（§10 手順1） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番には触らない | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード ADR-1020 便4a の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/routers/products.py` の `create_product`（POST /products）: PostgreSQL のときだけ、INSERT の前に9項目を検査して足りなければ 422 `REQUIRED_FIELDS_MISSING:...`（§4-1）
2. 同 `update_product`（PATCH /products/{id}）: PostgreSQL で対象行が共用（tenant_id IS NULL）のときだけ、日本語名・英語名・型番・発売日を「値か印があったのに空にする」更新を 422 `REQUIRED_FIELDS_CLEARED:...` で止める（§4-2）
3. `frontend/src/pages/products/ProductEditPage.tsx`: 保存の失敗で便3b の `requiredFieldsMessage` の言葉を出す（§4-3）
4. 試験（§4-4）
5. `docs/handoff/master-register-required-fields/design.md` に便4a の追記（§4-5）とこのカードの写し

入れない:
- SQLite の経路（試験用のテナント表。今の 59 本の試験の期待は変えない）
- `search_keywords`・`exclude_keywords` の products 列（正本は `product_search_keywords`・`product_exclude_keywords` 表。この口はそこへ書かないので、検査では「無い」として扱う）
- 新規作成画面の入力欄を増やすこと・画面の行き先を変えること
- migration・DB の制約・本番データ

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main の実物。生出力は /tmp/CC報告ファイル/master-required-fields/bin4a/recon/）
- `create_product`: backend/app/routers/products.py:356-428。PostgreSQL では `_products_ctx`（:94-96）で `public.products` に、`payload["tenant_id"] = None`（:375）で INSERT（:377-398）。INSERT 列に `work_id`・`product_format_id`・`product_category_id` が無い。`ProductCreate`（backend/app/schemas/product.py:40）にも無い。9項目の検査は呼ばない
- 本番の `public.products.work_id` は NOT NULL・既定値なし（/tmp/CC報告ファイル/master-required-fields/bin4a/recon/opus-workid-default.txt）。そのため今の本番では、この INSERT は DB の制約で失敗する（エラーは 500 相当で、理由が画面に出ない）。nginx の直近 720 時間の記録で `POST /api/v1/products` は 0 件（R8_nginx.txt）
- `update_product`: products.py:430-507。対象の行を `public.products` から読み（:445-449 `old_row`。キーは応答契約の名前 `name_ja`・`name_en`・`mark`・`release_date`）、`_UPDATABLE_COLUMNS`（:53-72）の列だけ UPDATE。`work_id`・`product_format_id`・`product_category_id` は更新できない。空に戻す検査は無い
- 権限: POST は `products.create`、PATCH は `products.update`。各テナントの owner / admin が持つ（R3）。正規の共用商品の作成口（POST /tcg/products・POST /tcg/products/create）は `require_super_admin`
- 検査関数: `check_required_fields(values, blank_confirmations)`（backend/app/services/tcg_product_master_svc.py:59）、`find_cleared_fields(before, before_marks, after, after_marks)`（同 :94）。値のキーは `REQUIRED_FIELDS`（:35-38）の名前
- 画面: frontend/src/pages/products/ProductEditPage.tsx:165 が `api.post("/products", payload)`、:167 が PATCH。失敗は :171 付近の `setError(e instanceof Error ? e.message : t("common.saveError"))` で、符号そのものが出る

### 2-2. 設計の細部（Opus の技術判断）
- D1 POST /products は、PostgreSQL では中分類・細分類・商品区分を受け取れず、検索ワード・除外ワードの正本の表にも書かない。そのため9項目の検査では、この3つと検索・除外ワードを「無い」として渡す。結果、PostgreSQL では常に 422 になり、今の「DB 制約で 500」が「どの項目が要るかを言う 422」に変わる。共用商品の登録は正規の口（TCG 商品マスタ）でだけできる、という ADR-1020 の形に揃う
- D2 PATCH は、更新できる4項目（日本語名・英語名・型番・発売日）だけを `find_cleared_fields` に渡す。古い空欄（前から空・印なし）は止めない。印は `public.product_blank_confirmations` から読む
- D3 テナントの行（tenant_id がある行）と SQLite の経路は変えない
- D4 応答の形は便3a と同じ `{"detail": "REQUIRED_FIELDS_MISSING:..."}`／`REQUIRED_FIELDS_CLEARED:...`。画面は便3b の `requiredFieldsMessage` をそのまま使う（新しい文言キーは足さない）

## 3. 触るファイル

1. `backend/app/routers/products.py`
2. `frontend/src/pages/products/ProductEditPage.tsx`
3. 試験: `backend/tests/test_products_required_fields_pg.py`（新規）・`frontend/src/pages/products/ProductEditPage.required.test.tsx`（新規。既存の ProductEditPage の試験ファイルの書き方に合わせる）
4. `docs/handoff/master-register-required-fields/design.md`・`docs/handoff/master-register-required-fields/card-bin4a.md`（新規）

## 4. 実装

### 4-1. `create_product`（products.py）
- import に足す: `from app.services.tcg_product_master_svc import check_required_fields, find_cleared_fields`（循環 import で落ちるときは、関数の中で import する。どちらにしたかを報告に書く）
- `payload["tenant_id"] = ...`（:375）の直後に:

```python
    # ADR-1020: 共用の表（public.products）に作るときは9項目を検査する。
    # この口は中分類・細分類・商品区分を受け取らず、検索・除外ワードの正本の表にも書かないので、それらは「無い」として渡す。
    if is_postgresql(db):
        missing = check_required_fields({
            "name": payload.get("name_ja"),
            "name_en": payload.get("name_en"),
            "mark": payload.get("mark"),
            "release_date": payload.get("release_date"),
            "search_keywords": None,
            "exclude_keywords": None,
            "work_id": None,
            "product_format_id": None,
            "product_category_id": None,
        }, set())
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="REQUIRED_FIELDS_MISSING:" + ",".join(missing),
            )
```

### 4-2. `update_product`（products.py）
- `if "tcg_type" in update_data:` の検査（:461 付近）の直後、SET 句を組む前に:

```python
    # ADR-1020: 共用の行で、値か印があった項目を空にする更新は止める（古い空欄は止めない）。
    if is_postgresql(db):
        shared = (await db.execute(
            text("SELECT 1 FROM public.products WHERE id = :id AND tenant_id IS NULL"),
            {"id": product_id},
        )).first()
        if shared is not None:
            marks = {r[0] for r in (await db.execute(
                text("SELECT field_code FROM public.product_blank_confirmations WHERE product_id = :id"),
                {"id": product_id},
            )).all()}
            keys = {"name": "name_ja", "name_en": "name_en", "mark": "mark", "release_date": "release_date"}
            before = {f: old_row.get(k) for f, k in keys.items()}
            after = {f: (update_data[k] if k in update_data else old_row.get(k)) for f, k in keys.items()}
            cleared = find_cleared_fields(before, marks, after, marks)
            if cleared:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="REQUIRED_FIELDS_CLEARED:" + ",".join(cleared),
                )
```

（`old_row` のキー名が `name_ja` でなければ、実物の `_select_columns`（:128）の別名に合わせ、報告に書く）

### 4-3. `ProductEditPage.tsx`
- import に `import { requiredFieldsMessage } from "../../features/tcg-product-import/productDetailModel";`
- 保存の catch（:171 付近）を `setError(requiredFieldsMessage(e, t) ?? (e instanceof Error ? e.message : t("common.saveError")));` にする

### 4-4. 試験

| # | ファイル | 試験 | 期待 |
|---|---|---|---|
| 1 | test_products_required_fields_pg.py | PG で POST /api/v1/products に `name_ja` だけ | 422・detail が `REQUIRED_FIELDS_MISSING:` で始まり `work_id`・`product_format_id`・`product_category_id`・`search_keywords` を含む。products の行数が増えない |
| 2 | 同 | PG で共用の行の `name_en` を値あり→空文字に PATCH | 422 `REQUIRED_FIELDS_CLEARED:name_en`。行の値は変わらない |
| 3 | 同 | 同じ行で `name_en` の印を入れてから空に PATCH | 200 |
| 4 | 同 | 前から `mark` が空・印なしの共用の行で、`notes` だけ PATCH | 200（古い空欄は止めない） |
| 5 | 同 | テナントの行（tenant_id あり）の `name_en` を空に PATCH | 200（対象外） |
| 6 | ProductEditPage.required.test.tsx | 新規保存で 422 `REQUIRED_FIELDS_MISSING:work_id` | 画面に符号 `REQUIRED_FIELDS_MISSING` が出ず、中分類の言葉を含むエラーが出る |

- PG の試験は、既存の `backend/tests/test_tcg_product_detail_pg.py`・`test_product_blank_confirmations_pg.py` の準備（PG の接続・migration の流し方・共用の行の作り方・ログインの作り方）を写して書く。PG が無い環境では既存と同じ形で skip になること
- 既存の試験は変えない

### 4-5. design.md への追記（末尾に節を足す）

```markdown
## 便4a 在庫の商品画面の口（2026-10-17 追記）
- 定着点検（Opus・2026-10-17）で、`backend/app/routers/products.py:379` の `POST /products` を「テナント商品」として対象外にしていたのは読み違いと分かった。PostgreSQL では `public.products` に tenant_id NULL で作る（:94-96・:375）。
- 本番では work_id の NOT NULL で INSERT が失敗しており、行は作られていない（直近720時間の呼び出し0件）。ただし理由が画面に出ず、口を直せば入れ忘れの行を作れる状態だった。
- 対処: POST は PostgreSQL では常に9項目を検査して 422（中分類・細分類・商品区分を受け取れないため）。PATCH は共用の行で4項目を空に戻す更新を 422。画面は requiredFieldsMessage で言葉を出す。
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. backend の試験: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a/backend && python -m pytest -q tests/test_products_required_fields_pg.py tests/test_products.py tests/test_products_tcg_type_fk.py tests/test_order_items_ben2.py 2>&1 | tail -15`（PG 試験が skip になるときは、既存の PG 試験の起動方法（例: テスト用 PostgreSQL の環境変数）を同じ形で使い、PG 試験が実行されたことを示す。どうしても PG で走らせられなければ、その事実と原文を報告に書く。CI の pytest (SQLite + PostgreSQL RLS) で走ることを Opus が確かめる）

5-2. 試験の名前: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && grep -nE "^\s*(async )?def test_" backend/tests/test_products_required_fields_pg.py | head -10` と `grep -nE "^\s*(it|test)\(" frontend/src/pages/products/ProductEditPage.required.test.tsx | head -5`

5-3. 検査の箇所: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && grep -nE "check_required_fields|find_cleared_fields|REQUIRED_FIELDS_" backend/app/routers/products.py | head -10`（POST に1組・PATCH に1組）

5-4. 画面の試験・型・lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/products/ 2>&1 | tail -10`、`npx tsc --noEmit -p tsconfig.json 2>&1 | tail -5`、`npx eslint src/pages/products/ProductEditPage.tsx src/pages/products/ProductEditPage.required.test.tsx 2>&1 | tail -5`（`src/api/generated/schema.d.ts` が無ければ先に `npm run generate:api-types 2>&1 | tail -3`。生成物はコミットしない）

5-5. backend の lint: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a/backend && ruff check app/routers/products.py tests/test_products_required_fields_pg.py 2>&1 | tail -5`

5-6. 差分: `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && git diff origin/main...HEAD --stat | tail -10` が §3 のファイルだけ

5-7. PR の CI は担当が待たない。PR を作ったら URL を報告して終える

## 6. 分岐ごとの対処

- §2-1 の行番号やコードが実物と違う → 実物の該当行を貼り、同じ意味・同じ位置に合わせて書く。見つからなければ NEEDS_DECISION:
- 既存の試験（test_products.py ほか）が落ちる → 落ちた試験名と原文を貼り NEEDS_DECISION:（期待を勝手に変えない）
- API の契約の検査（API contract is up to date）が差分を出す → 応答の型は変えていないので本来出ない。出たら原文を貼り NEEDS_DECISION:
- husky や CI の自動検査が落ちる → 検査名と原文を貼る。迂回（`--no-verify` など）しない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| PG の POST /products が9項目の不足を 422 で返し、行を作らない | 試験 1 |
| PG の共用の行で、値か印があった項目を空にする PATCH を 422 で止める | 試験 2 |
| 印があれば空にできる・古い空欄とテナントの行は止めない | 試験 3・4・5 |
| 画面に符号でなく言葉が出る | 試験 6 |
| SQLite の既存試験の期待は不変 | §5-1 の test_products.py ほかが合格 |

## 8. 反映の前後（Opus が行う。担当はしない）

- CI の緑を確かめ、差分を審査し、「確認済み」のコメントを残してマージ → deploy の成功を Actions の記録で確かめる
- 反映後、本番の HEAD がマージ commit と一致すること、backend コンテナの products.py に `REQUIRED_FIELDS_MISSING` が入っていること、未ログインの POST /api/v1/products が 401 のことを読み取りで確かめる
- 生出力は /tmp/CC報告ファイル/master-required-fields/bin4a/ に置く

## 9. 戻し方

- この PR の revert を main にマージ（POST は DB 制約の 500 に、PATCH は検査なしに戻る）

## 10. PR

手順1 新しい作業場所を作る
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && bash scripts/new-worktree.sh release/master-register-required-fields-bin4a --claude 2>&1 | tail -5
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && git status -sb | head -3 && git log -1 --oneline
期待する出力 作業場所が origin/main の先頭から作られている。以下のコマンドの作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a
    このカードを /tmp/CC報告ファイル/master-required-fields/bin4a/card-bin4a.md から Read し、Write ツールで `/Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a/docs/handoff/master-register-required-fields/card-bin4a.md` に同じ内容で置く。frontend の依存が無ければ `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a/frontend && npm ci 2>&1 | tail -5`

手順2 §4 を Write/Edit ツールで実装し、§5-1〜5-6 を実行する

手順3 commit と push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && git add backend/app/routers/products.py backend/tests/test_products_required_fields_pg.py frontend/src/pages/products docs/handoff/master-register-required-fields && git status -s | head -20
期待する出力 §3 のファイルだけが追加されている（それ以外が出たら git restore --staged で外す）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && git commit -m "fix: ADR-1020便4a 在庫の商品画面の口(POST/PATCH /products)にも共用商品の9項目検査を入れる"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && git push -q -u origin release/master-register-required-fields-bin4a && git log -1 --oneline && git log origin/release/master-register-required-fields-bin4a -1 --oneline
期待する出力 2 つの git log が同じハッシュ

手順4 PR を作る
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4a && gh auth status 2>&1 | grep -c "Active account: true"

- 名義が `shingo-cc` であることを確かめる
- 本文は Write ツールで英字だけのパスのファイル（/private/tmp/claude-501/bin4a-pr-body.md）に作り、作業場所に cd してから `scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめる（2 分以上かかるので timeout を長めにする）
- PR は `scripts/gh-pr-create-safe.sh` に本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。base は main。ready で作る（下書きにしない）。担当はマージしない
- 作成後に `.pr-number` と `gh pr list --head release/master-register-required-fields-bin4a --json number` の一致を確かめる
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-090・ADR-027 を書く。PO承認: に「PO 2026-10-17『y』（定着点検の抜け道1・欠け5を設計から本番反映まで）」と書く。validate-pr-body.sh が「設計docに参照がない」と ADR を指摘したら、その ADR だけを `対象ADR` から外し、外したことを報告に書く
- 本文に `### GO記録` の見出しと欄を置く（中身は Opus が書く。担当は欄の雛形だけ: `- GO発行者:`・`- 日時:`・`- GO原文:`・`- 対象 HEAD:`）
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。触るファイル: は実際に変えた全ファイル（`git diff origin/main...HEAD --name-only` と一致）。削除するファイル: は既存行を変えた全ファイル（新しく作ったファイルを除く）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-6 の出力の要点／PR の URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin4a/impl/）／import の置き方（§4-1）／PG 試験が実際に走ったか／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える
- 登録ルールのフック（master-register-rules-guard）に止められたら、言い換えずに報告して終える。ack の行は書かない
- Bash のコマンドに削除の SQL の語（大文字の削除文）を書かない

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
