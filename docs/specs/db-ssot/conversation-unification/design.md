# 会話データの一元化（conversation-unification）— 設計図

> この文書は何か（専門用語なしの1行）:
> 会話の記録が2つのテーブル（conversation_logs / meta_messages）に二重管理されている問題を、1つに統合する理想形の設計。親テーマ「DB設計のSSOT化」の子。

親: ../README.md ／ あるべき姿・KGI: ../ideal-state.md, ../kgi.md

## 1. 現状（調査で確定した事実・2026-07-09 tenant_004実測）
- 会話テーブルが2つ存在し、会話コアの列が10以上重複（raw_payload / analysis / original_language / occurred_at / is_manual / translated_text / channel_identity / direction / lead_id 等）。本文列は content_text ⇔ message_text の同義別名。
- 実運用は meta_messages 側に集中：コード使用391 vs 124、実データ25件 vs 6件。
- meta_messages は名称こそMessenger由来だが、実態はDiscordでも使用中（platform='discord'で保存）。
- 親への結びつき方が矛盾：conversation_logs は lead_id 必須(NOT NULL)だが外部キー0本（参照先を保証しない空約束）。meta_messages は lead_id 任意で、実データに lead 無しが1件。

## 2. あるべき姿（この子の理想形）
- 会話テーブルは1つに統合する。
- 器は全窓口共通（Messenger・Discord・将来のLINE/メール）。
- 中身は実運用されている meta_messages を土台に引き継ぐ。
- 全窓口共通の欄は本体に置く：誰から・宛先・本文・向き・既読・添付・翻訳・分析・言語・発生日時・どの窓口か・送信元メッセージ番号。
- そのプラットフォーム限定の欄は付箋として分離：送信タグ（messaging_type/message_tag＝Meta/IGの24時間・7日ルールの送信資格）・page_id・Meta固有の送信エラー。
- 全ての会話は必ず持ち主（リード）にひもづく。名簿にない相手の会話は保存できない（外部キーで保証。空約束にしない）。

## 3. なぜ（KGIとの対応）
- K1（重複ゼロ）：会話コアの二重定義を解消。
- K2（正本1か所）：会話の正本を統合テーブル1つに定める。
- K5（持ち主にたどり着ける）：全会話をリードに必須ひもづけ。

## 4. 稼働前の前提
- 本番未稼働。既存の会話データ（tenant_004で31件）は捨てて理想形で新規構築してよい。引っ越し（移行）作業は不要。現状のデータ分布に設計を引きずられない。

## 5. まだ決めていない（実装時に詰める）
- 付箋（プラットフォーム限定欄）を、本体テーブルの一区画にするか別テーブルにするか。
- is_manual 欄（使用13回と少ない）を残すかどうか。
- error系の列は会話用と別システム用（erp等）で同名衝突があるため、会話用のみを対象とする切り分け。

## 6. 維持の仕組み
- 本ファイルの変更はPR＋PO承認のみ。process-artifacts gate が管理。
