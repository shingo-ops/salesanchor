# ルールテーブル統一 設計書 v2

**テーマ**: 状態ルール UI 改善 + condition_def_id / unit_id プルダウン追加
**日付**: 2026-09-25
**状態**: 設計草案（PO承認済み方針に基づく）
**前提**: PR #3768 / #3771 で match_type/effect カラム追加済み・デプロイ済み

---

## PO壁打ち記録（2026-09-25）

### 議論の経緯

1. **ステータスルールと同じシンプルさに**
   - PO: 状態ルールと単位ルールは冗長に値の入力項目が並んでいる。ステータスルールと同様にシンプルでいい
   - 合意: code は非表示（バックエンド自動生成）、別名管理は非表示（解析で未使用）

2. **質問形式ラベル**
   - PO: 非エンジニアが見ても理解できるように質問形式に整形できるか？
   - 合意: 各フィールドを「何の値を入れるか」が直感的に分かる質問形式に変更

3. **出力値をDBから選択**
   - PO: canonical をフリーテキストではなくDBから選択してフォーマット化すべき
   - 合意: condition_definitions テーブルからプルダウンで選択

4. **状態と単位の分離 vs 合体**
   - PO: Sealed boxのように状態+単位の合成値は、分離してデータ分析の粒度を上げたい
   - 設計者: 分離保存なら「未開封の商品は全部で何件？」のようなクロス集計が可能になる
   - 合意: 状態定義マスタ(condition_definitions) = 純粋な状態、販売単位マスタ(units) = 単位

5. **直接判断 vs 分離+合体（精度の問題）**
   - PO: 「シュリなし→No shrink box」と直接判断したほうが精度が高いのでは？
   - 合意: ルールのマッチング（検索ワード→ヒット判定）は直接。分離は出力値の構造化のみ
   - つまり: ルールが「シュリなし」を検知→出力は state=No shrink + unit=Box として構造化保存

6. **状態ルールに単位プルダウンが必要な理由**
   - PO: Damaged case、Damaged sealed box のように、最終出力値がどの状態のどの単位かを登録しておく必要がある。これで請求書発行時に売上データに反映できる
   - 合意: 状態ルールに condition_def_id（状態定義）と unit_id（対象単位）の両プルダウンを設置

### PO承認済みの設計方針
- 状態ルールの各フィールドを質問形式ラベルに変更
- code は非表示（バックエンド自動生成）
- condition_def_id プルダウン（状態定義マスタから選択）を追加
- unit_id プルダウン（販売単位マスタから選択、nullable）を追加
- 出力値はシステムが「状態名 + 単位名」を自動結合してプレビュー表示
- 別名管理は非表示

---

## 1. 目的・利用者に見える変化

### 目的
状態ルールの UI を非エンジニアでも操作できる質問形式に改善し、出力値を DB マスタからの選択に変更してデータ整合性を確保する。

### 利用者に見える変化
- フィールドラベルが質問形式になる（例:「どの言葉が含まれていたらこの状態ですか？」）
- 出力する状態を「状態定義マスタ」からプルダウンで選択できる
- 対象単位を「販売単位マスタ」からプルダウンで選択できる（任意）
- 選択に応じて出力値（例: "Sealed box"）が自動プレビュー表示される
- code フィールド、別名管理ボタンが非表示になる

### 成功条件（○×判定）
| # | 条件 | 判定方法 |
|---|------|---------|
| S1 | 状態定義マスタからプルダウンで選択できる | 画面操作 |
| S2 | 販売単位マスタからプルダウンで選択できる | 画面操作 |
| S3 | 出力プレビューが「状態名 + 単位名」で表示される | 画面確認 |
| S4 | 質問形式ラベルが全フィールドに適用されている | 画面確認 |
| S5 | code が非表示で自動生成される | 新規作成時に確認 |
| S6 | 既存の11件の conditions データが壊れない | DB確認 |
| S7 | resolve_condition_v2 の動作が変わらない | 既存テスト全PASS |

---

## 2. 対象と対象外

### 対象
- `public.line_conditions` テーブルへの `unit_id` カラム追加 + `condition_def_id` 確認・追加 + `note` カラム追加
- `public.conditions` VIEW の再作成（新カラム反映）
- フロントエンド ConditionsMasterPanel の UI 改修
- バックエンド super_admin_conditions / conditions API の新カラム対応

### 対象外
- `resolve_condition_v2` のロジック変更（既存動作維持）
- `analysis_results` への condition_def_id 保存（次便）
- UnitMasterPanel / StatusMasterPanel の質問形式化（次便）
- `condition_definitions` へのシードデータ投入（POがUI経由で登録）

---

## 3. 変更前後

### 3-1. DB スキーマ（line_conditions に追加）

```sql
unit_id          INTEGER REFERENCES public.units(id) ON DELETE SET NULL,  -- 新規
condition_def_id INTEGER REFERENCES public.condition_definitions(id) ON DELETE SET NULL,  -- 確認・追加
note             TEXT NOT NULL DEFAULT '',  -- 新規
```

### 3-2. フロントエンド ConditionsMasterPanel

**変更前のフィールド**:
1. code (テキスト、必須)
2. canonical (テキスト、必須)
3. app_kubun (テキスト)
4. priority (数値)
5. match_type (セレクト)
6. effect (セレクト)
7. search_kw (テキストエリア)
8. exclude_kw (テキストエリア)
9. is_active (チェックボックス)
10. 別名管理ボタン

**変更後のフィールド（質問形式）**:
1. 「どの状態ですか？」→ condition_def_id プルダウン（condition_definitions から取得）
2. 「どの単位が対象ですか？」→ unit_id プルダウン（units から取得、nullable）
3. → 出力プレビュー: 「Sealed box」（自動表示）
4. 「どの言葉が含まれていたらこの状態ですか？」→ search_kw テキストエリア
5. 「この言葉が含まれていたら除外しますか？」→ exclude_kw テキストエリア
6. 「言葉の探し方は？」→ match_type セレクト
7. 「見つけたらどうしますか？」→ effect セレクト
8. 「どの商品タイプに適用しますか？」→ app_kubun テキスト
9. 「優先順位（小さいほど優先）」→ priority 数値
10. 「メモ」→ note テキスト
11. 「有効にしますか？」→ is_active チェックボックス

**非表示**:
- code（バックエンド自動生成: CN + タイムスタンプ or 連番）
- canonical（condition_def_id + unit_id から自動生成されるため不要）
- 別名管理ボタン

### 3-3. API スキーマ変更

CentralConditionBase / ConditionBase に追加:
```python
condition_def_id: Optional[int] = None
unit_id: Optional[int] = None
note: str = ""
```

### 3-4. code 自動生成ロジック（バックエンド）

POST（新規作成）時、code が未指定なら自動生成:
```python
code = f"CN{datetime.now().strftime('%Y%m%d%H%M%S')}"
```

---

## 4. 影響範囲

| ファイル | 変更内容 |
|---------|---------|
| `migrations/20260925_020000_conditions_add_def_unit_note.sql` | ALTER TABLE + VIEW 再作成 |
| `backend/app/schemas/central_masters.py` | condition_def_id, unit_id, note 追加 |
| `backend/app/schemas/condition.py` | 同上 |
| `backend/app/routers/super_admin_conditions.py` | CRUD 対応 + code 自動生成 |
| `backend/app/routers/conditions.py` | CRUD 対応 |
| `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx` | UI 全面改修 |
| `frontend/src/locales/ja.json` | 質問形式ラベル |
| `frontend/src/locales/en.json` | 同上 |
| `scripts/run_all_migrations.sh` | migration 登録 |
| `.github/workflows/migration-test.yml` | テストDB定義更新 |

### 影響しないもの
- `resolve_condition_v2` — 変更なし（canonical テキストベースの動作を維持）
- `analysis_results` — 変更なし
- UnitMasterPanel / StatusMasterPanel — 変更なし
- ConditionDefsMasterPanel — 変更なし（POが状態定義を登録するUIとして既存のまま使用）

---

## 5. リスクと対処

| リスク | 対処 |
|--------|------|
| condition_definitions が空の場合プルダウンが空 | 「（未設定）」オプション + canonical テキストフォールバック |
| 既存データに condition_def_id/unit_id がない | nullable、UI で「未設定」表示。既存動作に影響なし |
| VIEW 再作成失敗 | CREATE OR REPLACE VIEW（idempotent） |
| code 自動生成の衝突 | タイムスタンプベースで衝突確率極小 |

---

## 6. 受入条件と検証方法

| # | 条件 | 検証方法 |
|---|------|---------|
| V1 | line_conditions に unit_id, condition_def_id, note カラムが存在 | information_schema 確認 |
| V2 | VIEW が新カラムを含む | SELECT * FROM public.conditions LIMIT 1 |
| V3 | ConditionsMasterPanel で状態定義プルダウンが表示される | 画面操作 |
| V4 | ConditionsMasterPanel で単位プルダウンが表示される | 画面操作 |
| V5 | 出力プレビューが表示される | 画面操作 |
| V6 | 質問形式ラベルが適用されている | 画面確認 |
| V7 | 既存テスト全PASS | CI |
| V8 | resolve_condition_v2 の動作が変わらない | 既存テスト |

---

## 外部・過去事例の参照と我々への応用

不要（既存UIパターンの改善であり、新技術導入を伴わない）。

---

## 維持の仕組み

| 対象 | 守り手 |
|------|-------|
| `condition_definitions` / `units` マスタデータ | PO が ConditionDefsMasterPanel / UnitsMasterPanel 経由で UI 登録 |
| `resolve_condition_v2` の動作保証 | 既存テスト（test_condition_vocab.py 等） + CI |
| migration の安全性 | CI `migration-test` ジョブ + `migration-guard`（DROP COLUMN 検知） |
| i18n キー整合性 | ADR-027 + CI lint（ja.json / en.json キー一致チェック） |
