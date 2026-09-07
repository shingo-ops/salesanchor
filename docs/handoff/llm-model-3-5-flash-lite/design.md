# Phase 3 設計 — 翻訳・在庫解析のモデルを gemini-3.5-flash-lite に変更

**対象ADR**: ADR-110  
**recon**: docs/handoff/llm-model-3-5-flash-lite/recon.md  
**日付**: 2026-09-07  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: 同リポジトリの docs/handoff/translation-model-flashlite/design.md は、
  送信英訳のモデルを環境変数の既定値の書き換えで切り替えた前例である
  → 我々への応用: 同じ形（既定値の変更・環境変数での切り戻しは維持）で最小の変更にとどめる。
- 事例2: 同リポジトリの TCG 抽出は `backend/app/services/gemini_extraction_svc.py:126` で
  新しい世代のモデルを指定しており、提供終了の影響を受けていない
  → 我々への応用: 提供終了が起きる前提で、モデル名を 1 箇所にまとめる必要がある（第 2 段で対応）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 翻訳の既定モデルが gemini-3.5-flash-lite である | `git show origin/main:backend/app/services/message_translator.py` の該当 2 行を確認 |
| 在庫解析の既定モデルが gemini-3.5-flash-lite である | `git show origin/main:backend/app/services/inventory_parser_llm.py` の該当 2 行を確認 |
| 価格表に gemini-3.5-flash-lite がある | `pytest backend/tests/test_llm_budget.py` |
| 在庫解析のテストが新しいモデル名で通る | `pytest backend/tests/test_inventory_parser_llm.py` |
| 本番で翻訳の 404 が止まる | デプロイ後に celery worker のログを検索し、no longer available の出現が 0 件であること |

---

## 技術 How・KPI

- KPI: 翻訳処理の 404 失敗 0 件（デプロイ後の観測）。
- 技術選択: モデル名は環境変数で上書きできる形を維持し、既定値のみ変更する
  （理由: 障害時にコード変更なしで切り戻せる状態を保つため）。
- 価格は 1M トークンあたり入力 0.30 ドル・出力 2.50 ドルを採用する。
  出典は公開情報であり、請求実績での裏取りは未実施（recon 参照）。

---

## 弊害・トレードオフ

- 送信英訳も Flash-Lite になるため、ADR-110 の「送信英訳は最上位モデル必須」という
  方針と食い違う → 対策: 訳質の確認後、必要なら環境変数 TRANSLATION_MODEL_SEND で
  上位モデルに戻す。ADR-110 の記述更新は第 2 段の SSOT 化便で扱う。
- モデル名が依然として複数ファイルに散在する → 対策: 第 2 段で 1 箇所に集約する。
- 価格が参照値のため、コスト記録に誤差が残りうる → 対策: 請求実績との突き合わせを別途行う。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 既定値と価格表とテストを変更し PR を作る | Generator |
| 2 | デプロイ後にログで 404 の停止を確認する | Generator |
| 3 | モデル名の SSOT 化を設計する | Planner |

---

## 維持の仕組み

- 守り手1: `backend/tests/test_llm_budget.py` が価格表の内容を検査する。
  使用するモデルが価格表に無ければテストで気づける。
- 守り手2: `docs/handoff/llm-model-3-5-flash-lite/recon.md` に、モデル名が
  複数ファイルに散在している事実と所在を記録した。次に提供終了が起きたとき、
  この一覧から探せる。
- 未確立（正直な明記）: 使用モデルと価格表の整合を機械が検査する仕組みは未設計。
  提供終了を事前に検知する仕組みも無い。第 2 段の SSOT 化便で設計する。
  それまでは人が守る。

---

## 継続

- 完了後の監視: デプロイ後に celery worker のログで 404 の再発を確認する。
- 次フェーズへの引き継ぎ: モデル名と価格の SSOT 化（用途 → モデル → 価格を 1 箇所に集約し、
  整合を CI で検査する）。ADR-110 の記述更新もそこで行う。
