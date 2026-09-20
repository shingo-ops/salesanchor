# design: tcg_status_master SSOT統合 Phase 1

## KGI

`tcg_status_master` が唯一の完売判定源になること。

| 基準 | 検証方法 |
|------|---------|
| 「sold」「売切」「SOLD OUT」「一旦ストップ」「〆」「ストップ」を含む商品名が `resolve_status_v2` で `(Sold out, excluded)` を返す | unit test: `test_resolve_status_v2_new_soldout_words` |
| 「売り切れの場合がございます」を含む商品名が `(active, None)` を返す（誤判定なし） | unit test: `test_resolve_status_v2_exclude_pattern_guard` |
| 「予告なく完売となる場合」を含む商品名が `(active, None)` を返す（誤判定なし） | unit test: `test_resolve_status_v2_exclude_pattern_guard` |
| migration が冪等（2回実行でエラーなし）| `ON CONFLICT DO NOTHING` + `WHERE exclude_pattern = ''` |

## 変更概要

### A. Migration: `migrations/20260921_000000_status_master_soldout_ssot.sql`
- INSERT 6行（ST0015〜ST0020）: 不足している完売ワードを追加
- UPDATE 2行（ST0012, ST0013）: exclude_pattern を設定（誤判定防止）
- 冪等: ON CONFLICT DO NOTHING / WHERE exclude_pattern = ''

### B. Backend: `backend/app/services/tcg_analyzer_svc.py`

**Change 1 (load_status_master, 行1063-1072):**
- `"exclude_pattern": r[3] or ""` を dict comprehension に追加
- SQL は既に exclude_pattern を SELECT しているが dict に含まれていなかった

**Change 2 (resolve_status_v2, 行1111-1116):**
- EXCLUDE ループで search_pattern がマッチした後、exclude_pattern もマッチする場合は `continue`（誤判定スキップ）

### C. run_all_migrations.sh
- 末尾に新 migration エントリを追加

## 影響範囲

呼び出し元:
- `backend/app/services/tcg_analyzer_svc.py:1174` — `resolve_status_v2` 呼び出し（1箇所）
- `backend/app/services/tcg_analyzer_svc.py:1332` — `resolve_status_v2` 呼び出し（1箇所）
- フロントエンド: 変更なし
- GAS (SystemResolverV2.gs): 変更なし（別系統・この PR には含まない）

## 変更しない範囲

- OUTPUT / DEFAULT エントリの処理ロジック
- priority sort・memo_exact 判定の動作
- テーブルスキーマ（カラム追加なし）
- フロントエンド全体

## 外部事例

N/A — 内部 SSOT 統合。既存の resolve_status_v2 ロジックの bug fix + マスタデータ補完。

## 守り手

1. **resolve_status_v2 unit test** — `backend/tests/` 配下の既存テストで exclude_pattern 挙動を検証
2. **本番マッチングテスト** — 実運用データに対して `tcg_analyzer_svc.py` を実行し、SSOT 完売ワードが正しく判定されることを確認

## ADR 参照

- `docs/adr/ADR-154-*.md` — tcg_status_master SSOT方針
- `docs/adr/ADR-109-*.md` — TCG解析パイプライン設計

## recon 相互参照

→ `docs/handoff/status-master-soldout-ssot/recon.md`

## 標準ワークフロー確認

- [x] ADR 検索済み（ADR-154, ADR-109）
- [x] recon.md: file:line 引用あり
- [x] design.md: KGI/KPI テーブル + 外部事例欄 + 守り手 記入済み
- [x] 冪等マイグレーション（ON CONFLICT DO NOTHING）
- [x] migration-guard.yml 確認 — INSERT/UPDATE のみ、新テーブル作成なし → 変更不要
