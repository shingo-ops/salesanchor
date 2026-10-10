# design: v102 の既定の指示書を raw_copy_v101_f_ct に切り替え

関連 recon: `/Users/tanizawashingo/salesanchor/docs/handoff/v102-prompt-fct/recon.md`

## 目的
〆だけの投稿（完売の知らせ）を、1件の「件」として取り出せるようにする。PO 承認 2026-10-11「切り替える」。

## 変更前後
| 項目 | 前 | 後 |
|---|---|---|
| 既定の指示書 key（`V102_PROMPT_KEY`） | raw_copy_v101_f_c | raw_copy_v101_f_ct |
| engine_version（`V102_ENGINE_VERSION`） | v102-f_c | v102-f_ct |

触らない: `gemini_raw_copy_v101.py`（`DEFAULT_V102_PROMPT_NAME`）、DB 上の f_c の行（残す）。

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

## 外部事例
該当なし（社内の正解表による A/B 比較が直接の根拠）

## 維持の仕組み
Gemini 抽出セッションが、指示書の追加・切替のたびに `docs/specs/line-analysis-tuning/README.md` を更新する。
