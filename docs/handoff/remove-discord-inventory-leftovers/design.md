# design: Discord 在庫取り込みの残り3ファイルの削除

- recon: `docs/handoff/remove-discord-inventory-leftovers/recon.md`
- 関連ADR: ADR-1004（LLM 使用量台帳。`inventory_parse_fallback` の経路は機能ごと削除済み）、ADR-135（main マージは本番投入）
- PO 決定: 「在庫取り込みだけで使っているものは削除、他の用途で使用しているものは残す」（2026-10-02）と、3 ファイル削除の直接の許可（同日）

## 変更

- 削除: `backend/app/services/inventory_drift_detector.py`、`backend/app/schemas/parse_review.py`、`scripts/seed_discord_inbound_from_api_analysis.py`
- 変更しないもの: DB（表の DROP は PR #3937）、ほかのコード

## 受入条件

| 基準 | 検証方法 |
|---|---|
| 3 ファイルが無い | `git ls-files` に出ない |
| 参照が残っていない | `git grep` で 0 件（recon §1 のコマンド） |
| アプリが起動する | `python3 -c "import app.main"` が成功、CI の pytest が緑 |
| 本番で他機能に影響が無い | 反映後、backend・celery・discord-gateway のログにエラーが増えない |

## リスクと戻し方

- 参照 0 件のため、実行時の影響は無い。
- 戻し方: この PR を revert する。

## 外部・過去事例の参照と我々への応用

該当事例なし。理由：参照 0 件の死んだコードの削除であり、外部の事例で裏付ける判断を含まないため。

## 維持の仕組み

- 削除後に同名の参照を足すと import エラーになり、CI の pytest で検出される。
- 守り手: `backend/tests`（CI の pytest）、`scripts/check-condition-vocab.js`
