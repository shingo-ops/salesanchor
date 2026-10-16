# 設計審査 — S3 db-error-detail

**日付**: 2026-10-16　**審査者**: Claude Opus（設計者と同一 AI による自己審査。独立した第二者レビューではない）
**対象**: [design.md](design.md)、[recon.md](recon.md)、[../../specs/db-error-detail/kgi.md](../../specs/db-error-detail/kgi.md)

## 判定: APPROVE（設計合格）

設計合格は実装開始・マージ・本番反映の承認を兼ねない。

## 確認したこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存仕様・ADR との整合 | ○ 該当 ADR なし。既存の正本 handle_db_exceptions・main.py の全体ハンドラと同じ方式（中身はログ・応答は固定文言） | recon 冒頭、§3 |
| SSOT | ○ ログに残す処理を _utils.py の 1 関数に集め、写しを作らない | design §2 |
| 根拠の十分さ | ○ 応答に SQL 文・入力値が入ることを本番と同じ版で実物確認。対象 59 件を AST で全件抽出し、except 節の形を全件読んだ | recon §1、§2、§4、付録 |
| 文言への依存 | ○ frontend・gas・scripts・tests に detail の文言で分岐する箇所 0 | recon §5 |
| 受入条件の検証可能性 | ○ K1・K2 は CI の試験、K3 は反映前後の件数比較 | design §6 |
| 実装範囲の明確さ | ○ 書き換えの型と例外（buyback_prices.py・erp.py）を明記。触らない範囲を明記 | design §2、§3 |
| 区分 | B（backend/app/routers を触るため PR に GO 記録が要る。migrations・deploy.yml・本番 scripts は無い） | design §3 |

## 未解決事項（実装・PR で確かめる）

- T3 が CI で skip されずに走るか（recon §6 で未確認）。skip なら K2 未達として止まる。
- T1 は「detail の式の中に except の変数が直接現れる」形だけを検出する。例外を別の変数に入れてから detail に渡す形は検出しない（recon §1 の抽出も同じ限界で、該当は【未確認】）。実装時に対象 28 ファイルの差分を全件読み、該当が無いことを確かめる。
- 本番 PG のロケール（K 判定には影響しない）。
