<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — stop-mark-seed-migrations

**対象ADR**: ADR-155（関連: ADR-1005）  
**recon**: docs/handoff/stop-mark-seed-migrations/recon.md  
**日付**: 2026-10-09  
**担当**: Dev（実装担当）、設計は Opus

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は自社の本番事故（mark の書き戻し）の原因 migration を1本削除するだけの小変更で、出典と数値のそろった外部事例を確認していないため。一般論としての「実行済み記録方式」は ADR-1005 が扱う（別セッション）。

---

## 変更内容（PO 指示：商品マスタの値を上書きする migration は廃止して削除）

- migrations/20260604_010000_seed_product_marks.sql をファイルごと削除（git rm）。
- `scripts/run_all_migrations.sh` の登録行（264 行）を削除し、理由の1行コメントに置換。
- 触らない：migrations/20260616_000000_fix_tcg_type_dedup.sql（テストが名前で読むため）、mark_en_t004 ほか上書き・補充型 migration 全般（第2便の判断）。
- 値の正はマスタ（画面・CSV）。今のマスタの値は変わらない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 登録先の実在点検が通る | ローカルで `bash scripts/check-migration-registration-exists.sh --mode host --repo-root $PWD` |
| カラム churn 検出が通る | ローカルで `node scripts/check-migration-column-churn.js` |
| 二重登録が無い | ローカルで `bash scripts/check-migration-duplicate-registration.sh` |
| 全件ドライランが通る | CI の migration-full-dryrun が pass |
| デプロイ後に直した値が残る | デプロイ後、Opus が本番で products id 440559 の mark=M2a、id 10 の mark=MC を SELECT で確認 |

---

## 技術 How・KPI

- KPI：デプロイ後に id 440559 の mark が M2a のまま、id 10 が MC のまま（戻りゼロ）。
- 技術選択：ファイル削除＋登録削除を同時に行う（登録だけ残すと実在点検が落ちる）。

---

## 弊害・トレードオフ

- 空の DB を一から作る試験・新テナントで mark が自動投入されなくなる → 対策：ADR-155 の方針どおり CSV 取り込みで入れる。テストからの参照は無し。
- 履歴として SQL が消える → 対策：git 履歴に残る。戻し方は下記。

---

## 維持の仕組み

- 新規 migration が保護表へ値を書くことは、既存のチェック7（`.github/workflows/migration-guard.yml:407`）が止める。
- 既存 migration が毎デプロイ流し直される問題は、ADR-1005 段階2（実行済み記録）で別セッションが扱う。本便では扱わない。

## 戻し方

- git revert（削除したファイルと登録行が戻る）。ただし戻すと次のデプロイで mark が再び上書きされる。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 削除と登録行の削除、docs 作成 | Dev |
| 2 | Draft PR 起票、GO 記録 | Dev / Opus |
| 3 | デプロイ後の本番確認 | Opus |

---

## 継続

- 完了後の監視：デプロイ後に 440559=M2a、10=MC を確認。
- 次フェーズへの引き継ぎ：第2便（fix_tcg_type_dedup と他の上書き型の扱い）は Opus の本番確認と設計判断待ち。
