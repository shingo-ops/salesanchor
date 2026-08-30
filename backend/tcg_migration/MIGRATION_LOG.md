# MIG-02 Migration Log

## Phase 1: スキーマ作成
- **日付**: 2026-08-30
- **ブランチ**: mig02/schema → feat/tcg-migration
- **内容**: Alembic + SQLAlchemy で 17 テーブル新規作成
- **結果**: OK

## Phase 2: データインポート
- **日付**: 2026-08-30
- **ブランチ**: mig02/importer → feat/tcg-migration
- **内容**: suppliers=45 / extraction_items=1626 / products=267 / exclude_keywords インポート
- **結果**: 3/4 チェック OK。exclude_keywords で STOP 報告（後述の訂正参照）

### ⚠️ exclude_keywords 期待値訂正 (2026-08-30)

**訂正内容:**
> task-spec (CC_TASK_MIG-02) に記載の `exclude_keywords: 54` は
> ADR-093 策定時点のスナップショット値であり、現在のライブ実測とは一致しない。
>
> ライブ 商品マスタV2 (dataRows=268) から y13_07_backup (262行) を経由して
> コンマ区切りで集計した実測値 **123** が正しい値。
>
> 期待値を 54 → **123** に訂正する。Phase 2 STOP を解除。

**根拠:**
- `clasp run getProviderScoringMasterSnapshot` → 商品マスタ rowCount=269, dataRows=268
- `clasp run y1407ProbeSheetRowCount --params '["商品マスタV2"]'` → dataRows=268
- y13_07_backup (2026-08-26 07:13:19): rowCount=262, コンマ区切り集計 → 123 エントリ
- 54 の算出根拠は ADR-093 時点のスナップショットであることをユーザーが確認

## Phase 3: Compat Engine
- **日付**: 2026-08-30
- **ブランチ**: mig02/compat-engine → feat/tcg-migration
- **内容**: gemini_all.json system フィールドを analysis_results に投入 (compat-v1)
- **結果**: 全チェック OK (needs_review=1394 / pid_unresolved=344 / unit_unresolved=528 / SP0023=198)

## MIG-03 Phase 2: 欠陥是正

### 是正1: メモ不変確認 (2026-08-30)
- **ブランチ**: mig03/fix1-memo-stability → feat/tcg-migration-phase2
- **内容**: `reanalyze.py` による全件 UPDATE ベース再解析。item_notes は extraction_items FK であるため analysis_results の UPDATE では影響を受けないことを検証
- **結果**: item_notes=3（テスト用）残存確認 ✅ PASS

### 是正2: matching_name_first フラグ (2026-08-30) — STOP
- **ブランチ**: mig03/fix2-matching-name-first
- **内容**: `analyzer.py` に `matching_name_first` フラグを実装し名前先行マッチングを試験
- **実装**: flag=off→compat-v1 完全再現 PASS。flag=on→name-first-v1 実行
- **結果**: STOP — pid_unresolved が 344→781 (+437) の悪化

#### 悪化内訳

| 種別 | 件数 | 根本原因 |
|------|------|---------|
| NONE 悪化 | 258件 | DBの search_keywords にコンマが混入（importer.py がスペース分割した際コンマ付き文字列が残存） |
| MULTI 悪化 | 227件 | 単位カテゴリ絞り廃止により複数商品がマッチ |
| **計** | **485件** | — |

改善: 48件 (compat=NO → name-first=YES)

#### NONE 悪化の根本原因例

```
OP-15 → PM0207 のDBキーワード = ['OP-15,OP-15', '神の島の冒険,神の島の冒険,OP15']
         'OP-15,OP-15' は 'OP-15' の substring ではない → NONE
```

importer.py の search_kw 分割がスペース区切り (`split()`) だが、バックアップの Search Keywords 列がコンマ区切りだったため、コンマ付き文字列がそのまま格納された。

#### MULTI 悪化の根本原因例

```
バトルパートナーズ → PM0148 と PM0150 の両方が search keyword 'バトルパートナーズ' を持つ
                    compat は単位 Box で絞っても両方 Box カテゴリのため絞れず
                    → MULTI (ただし compat では PM0148 に一意解決していた)
```

compat-v1 が一意解決できていた理由は不明（ライブマスタキーワードと DB バックアップキーワードの差異が疑われる）。

#### 現状
- DB は compat-v1 にロールバック済み（analyzer.py --flag off で確認）
- analyzer.py は feat/tcg-migration-phase2 に merge 済みだが DB には適用しない
- 是正2 の方針を要確認

## Phase 4: 検収テスト
- **日付**: 2026-08-30
- **ブランチ**: mig02/acceptance → feat/tcg-migration
- **初回結果**: 11 passed, 1 xfailed (exclude_keywords 期待値不一致)

### 期待値訂正後の再検収 (2026-08-30)
- **ブランチ**: mig02/fix-exclude-keywords-expected
- **変更**: test_acceptance.py の exclude_keywords 期待値 54 → 123、xfail 除去
- **DB**: ローカル全件投入し直し (alembic downgrade → upgrade → importer → compat_engine)
- **結果**: **12 passed, 0 xfailed** → Phase 4 PASS
