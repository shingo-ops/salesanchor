# Recon: 仕入元 name 重複解消

調査日: 2026-09-24

---

## 既存 ADR 検索結果

`git grep -i supplier docs/adr/` および `docs/adr/FEATURE-INDEX.md` を確認。

| ADR | タイトル | 関連性 |
|-----|---------|--------|
| ADR-085 | Supplier Master Design | 仕入元マスタの正規化方針（line_name / supplier_code 二重管理の起源） |
| ADR-090 | LINE Import Service Architecture | SP-xxxxx レコード自動生成の設計根拠 |
| ADR-072 | Tenant Context Isolation | write endpoint での reset_tenant_context() 必須 |

---

## 重複の根本原因

2つの登録経路が同一人物を別レコードとして作成している。

| 経路 | スクリプト | supplier_code 形式 | line_name | category |
|------|-----------|-------------------|-----------|----------|
| 手動インポート（旧） | `seed_suppliers_from_line_master.py` | `SUP-xxx`（3桁） | NULL | individual |
| LINE自動登録（新） | `tcg_line_import_svc.py` | `SP-xxxxx`（5桁） | = name の値 | corporate |

同一人物の name が両方のレコードで一致しているため、UI・API でフィルタすると重複表示が発生する。

---

## 本番 DB 観測値（2026-09-24 実測）

- アクティブ仕入元: 245件（`WHERE is_active=TRUE AND tenant_id IS NULL`）
- name 重複組数: 21組（各組が旧 SUP-xxx 1件 + 新 SP-xxxxx 1件）

---

## FK 参照状況（全量）

| テーブル | 旧21件への参照数 | 処理方針 |
|---------|----------------|---------|
| `supplier_prompts` | 15件 | UPDATE: 旧→新へ付け替え（新側に既存なし） |
| `supplier_knowledge_links` | 47件 | DELETE: 新側に同一リンクが存在（DUPLICATE） |
| `inventory` | 31件（4名分） | UPDATE: 旧→新へ付け替え |
| `discord_inbound_messages` | 10件 | UPDATE: 旧→新へ付け替え |
| その他テーブル | 0件 | 操作不要 |

---

## 21組のIDマッピング（本番DB 2026-09-24 実測値）

| # | name | 旧ID (SUP-xxx) | 新ID (SP-xxxxx) |
|---|------|---------------|----------------|
| 1 | INスタッフ | 329 | 25542 |
| 2 | JUN OKUBAYASHI | 314 | 25499 |
| 3 | kyosuke | 301 | 25547 |
| 4 | SAMURAI-T | 303 | 25496 |
| 5 | T | 317 | 25501 |
| 6 | Yasu Kishi | 318 | 25500 |
| 7 | yusuke | 295 | 25494 |
| 8 | yuya | 312 | 26014 |
| 9 | かあ | 319 | 25502 |
| 10 | カンジン | 290 | 25492 |
| 11 | シンソク | 33 | 25536 |
| 12 | ヒロト | 311 | 25579 |
| 13 | むらお | 299 | 25572 |
| 14 | やまちゃん | 309 | 25546 |
| 15 | 三海 | 300 | 25618 |
| 16 | 平田光希 | 327 | 25505 |
| 17 | 村上 宝聡 | 315 | 25643 |
| 18 | 株式会社N&U | 308 | 25498 |
| 19 | 武 | 328 | 25506 |
| 20 | 竹内 | 316 | 25596 |
| 21 | 馬場和也 | 325 | 25605 |
