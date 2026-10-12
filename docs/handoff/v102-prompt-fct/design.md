# design: v102 の既定の指示書を raw_copy_v101_f_ct に切り替え

関連 recon: `docs/handoff/v102-prompt-fct/recon.md`

関連 ADR: ADR-085（仕入先別 Gemini 解析プロンプトの管理。指示書を DB で管理する点の関連のみ。既定 key を定める ADR はない。PR本文と同じ参照）

## 目的
〆だけの投稿（完売の知らせ）を、1件の「件」として取り出せるようにする。PO 承認 2026-10-11「切り替える」。

## 変更前後
| 項目 | 前 | 後 |
|---|---|---|
| 既定の指示書 key（`V102_PROMPT_KEY`） | raw_copy_v101_f_c | raw_copy_v101_f_ct |
| engine_version（`V102_ENGINE_VERSION`） | v102-f_c | v102-f_ct |

触らない: `backend/app/services/gemini_raw_copy_v101.py`（`DEFAULT_V102_PROMPT_NAME`）、DB 上の f_c の行（残す）。

## 根拠（G3 v2、125投稿×2回の A/B）
- 行の一致: f_ct 4500 / f_c 4493
- 抜け: 2 / 4
- 〆だけの9投稿の件: f_ct 27/27、f_c 4/27
- f_ct のみで出た差: 7bbac5f1 価格の写しに単位数を含め price_unresolved 1/250、ec1d8759 数量 none 1/250

## 検証基準
|基準|検証方法|
|---|---|
| 本番の新しい解析の extraction_jobs.prompt_version が `v102:raw_copy_v101_f_ct:` で始まる | 本番SQL |
| analysis_results.engine_version が v102-f_ct | 本番SQL |
| 単体試験緑 | CI |

## ロールバック
この PR を revert する。DB の f_c の行は残してあるので、revert だけで元に戻る。

## 外部・過去事例の参照と我々への応用
外部事例なし（直接の根拠は社内正解表 G3 v2 による A/B 比較）。過去事例: 指示書の文言調整は BASE SHOP で7回不合格（f_d〜f_g, f_cb, f_cs, f_csb）→ 今回は1行追加に限り、2段階（9投稿×3回 → 125投稿×2回）で確認した。

## 維持の仕組み
守り手: `docs/specs/line-analysis-tuning/README.md`（Gemini 抽出セッションが指示書を変えるたびに正解表 G3 v2 で A/B 採点し、ここに記録）
