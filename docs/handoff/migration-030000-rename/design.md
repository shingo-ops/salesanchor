# 設計図：刻印衝突の解消（develop の products FK migration を 030000→060000 にリネーム）

- **日付**: 2026-06-26
- **正本**: docs/STANDARD-WORKFLOW.md
- **対象**: develop ブランチの migration タイムスタンプ衝突
- **担当の経緯**: 本件は元々 D-1（別セッション）のスコープだったが、D-1が約2日停止（最終 2026-06-24 13:34・対応 open PR なし）のため、本セッションで巻き取る。
- **危険度**: 高（migrations/ を触る＝正本「危険な変更・人の承認必須」）
- **参照**: [recon.md](./recon.md)

---

## 何の問題か（素人向け）

develop に「030000番の札」を持つ migration ファイルが2枚ある：

1. products FK 用（`20260623_030000_add_products_tcg_type_fk.sql`）
2. 在庫用（`20260623_030000_drop_inventory_offer_key.sql`）

main では products FK 用を「060000番」に付け替え済み（#2538の clean-release で）。だが develop は古い「030000番」のまま。
この食い違いのせいで：

- develop→main のリリース (#2540) が CONFLICTING（衝突）でマージできない
- 安全装置（migration-guard チェック5）が「同じ札が2枚ある」と検知して BLOCK する

→ 壁1（テナント作成バグ修正）も release #2540 も、本番に出せない。

---

## どう直すか（素人向け）

develop の products FK 用の札を、main と同じ「060000番」に付け替える。

- 中身（FKの定義）は一切変えない（main の 060000 と完全同一と確認済み）
- 札（ファイル名）を付け替え、それを指している3箇所も合わせて直すだけ

「別物を持ち込む」のではなく「名前を揃える」だけ。

---

## ① KGI（成功条件・観測可能）

リネーム後:

1. develop→main の PR #2540 が CONFLICTING でなくなる（mergeable になる）
2. migration-guard チェック5 が BLOCK しなくなる
3. develop と main の products FK migration のファイル名が一致する（両方 060000）

---

## ② recon サマリ（確定事実・file:line）

- **(A)** `docs/handoff/migration-030000-rename/recon.md` の R-1 参照: develop:`migrations/20260623_030000_add_products_tcg_type_fk.sql` と main:`migrations/20260623_060000_add_products_tcg_type_fk.sql` の中身は git diff 空 = **完全同一**
- **(B)** develop の登録: `scripts/run_all_migrations.sh:445`（`030000`）/ main:`scripts/run_all_migrations.sh:448`（`060000`）
- **(C)** ファイル名参照（実効・変更必要）:
  - `scripts/run_all_migrations.sh:445`
  - `backend/tests/rls_bootstrap.py:27`
  - `backend/tests/test_products_tcg_type_fk.py:45`
  - docs 参照（変更不要・記録）: `.claude-pipeline/active-work.md:28` / `docs/ai-agents/evidence-registry.md:934`
- **(D)** `scripts/run_all_migrations.sh:176`: `20260623_030000_drop_inventory_offer_key.sql` はコメントアウト済み（HELD）・自動実行されない → リネーム後も問題なし
- **(E)** リネームで migration-guard チェック5 の BLOCK が消える（060000 が main 既存と一致 → 新規追加扱いされない）

注記: ファイル内コメント `Migration 20260623_030000:` は main:060000 側も同じ表記のまま。develop を main に揃えるので同状態になる（実害なし・動作非依存）。

---

## ③ 設計（変更前後・Generator は判断ゼロ）

### 変更（4ファイル）

| # | ファイル | 変更前 | 変更後 |
|---|---|---|---|
| 1 | `migrations/20260623_030000_add_products_tcg_type_fk.sql` | このファイル名 | `git mv` で `migrations/20260623_060000_add_products_tcg_type_fk.sql` にリネーム（中身は1文字も変えない） |
| 2 | `scripts/run_all_migrations.sh:445` | `run_sql migrations/20260623_030000_add_products_tcg_type_fk.sql` | `run_sql migrations/20260623_060000_add_products_tcg_type_fk.sql` |
| 3 | `backend/tests/rls_bootstrap.py:27` | `...20260623_030000_add_products_tcg_type_fk...` | `...20260623_060000_add_products_tcg_type_fk...` |
| 4 | `backend/tests/test_products_tcg_type_fk.py:45` | `...20260623_030000_add_products_tcg_type_fk...` | `...20260623_060000_add_products_tcg_type_fk...` |

※ ファイル参照の文字列置換は `030000_add_products_tcg_type` → `060000_add_products_tcg_type`
（`drop_inventory_offer_key` の 030000 は触らない・文字列が異なるので誤爆しない）

### 触らない範囲（重要）

- リネーム対象ファイルの中身（FK定義・SQL）は1文字も変えない（`git mv` のみ）
- `20260623_030000_drop_inventory_offer_key.sql`（在庫側）は触らない（別ファイル・HELD）
- 他の migration・backend 他・frontend・#2540 本体のコード・`deploy.yml` は触らない
- docs 参照（`active-work.md` / `evidence-registry.md`）は記録なので触らない

---

## 弊害対策

- **中身が変わらないこと**: `git mv` を使い、内容の diff がゼロであることをリネーム後に確認（`git diff` で中身変更が無い = rename のみ）
- **drop_inventory_offer_key を巻き込まない**: 置換文字列を `030000_add_products_tcg_type` に限定（`030000_drop_inventory` とは別文字列なので誤置換しない）
- **本番 DB への影響ゼロ**: FK は既に本番適用済み（060000 経由・EV-20260624-001）。冪等（IF NOT EXISTS）。このリネームは「develop のファイル名を main に揃える」だけで、本番 DB に新たな DDL は流れない
- **テスト整合**: `rls_bootstrap.py` / `test_products_tcg_type_fk.py` の参照を直さないとテストが古いファイル名を探して失敗する → 3ファイル同時更新で CI が通ることを確認

---

## KPI（成功判定）

| 基準 | 検証方法 |
|---|---|
| リネーム後 `git diff` ：ファイル中身の変更ゼロ（rename と参照3箇所の文字列変更のみ） | `git diff` |
| PR #2540 が CONFLICTING → mergeable になる | `gh pr view 2540` |
| migration-guard チェック5 が通る（BLOCK 消える） | CI |
| CI 緑（テストが新ファイル名で通る） | CI |

---

## 計画

1PR で4ファイル（リネーム＋参照3更新）。base=develop。
これ単体では本番 DB を変えない（ファイル名整理）。ただし `migrations/` を触るので GO 必須。

---

## ④ 継続・再発防止（＋外部・過去事例）

- **根本原因**: #2538 が develop を経由せず main 直行したため、develop に古い刻印（030000）が残り、main（060000）とズレた。今回のリネームでズレを解消。
- **再発防止**: release は develop→main を基本とし、main 直行した場合は develop 側の刻印も即揃える運用を徹底（main 直行が刻印ドリフトを生む）。
- **外部事例**: Flyway / Liquibase の migration 命名規則では「タイムスタンプ重複は実行順序の不定性を生む」として厳禁。本プロジェクトの migration-guard チェック5（`docs/handoff/migration-timestamp-dup-guard/design.md` 参照）はこの原則を CI で強制するもの。今回はそのガードが正しく機能している。
- このリネーム後、#2540 のコンフリクト解消（`deploy.yml` コメント1行）も別途必要（既知）。

---

## 関所・承認

- `migrations/` 変更 = 危険変更 = **GO 必須**
- recon を `recon.md` としてコミット＋CI 緑にし本 design と相互参照。
- PR 番号≥2600 なら触る/削除ファイル宣言必須（リネーム = 旧ファイル削除＋新ファイル追加なので削除宣言に旧 030000 ファイルを含める）。

### GO 記録（GO が出たらここに記入）

```
GO発行者:
GO日時:
GO原文:
バックアップ確認:
```
