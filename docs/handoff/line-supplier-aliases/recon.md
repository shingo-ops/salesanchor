# PCとAndroidの仕入先名の照合
この文書は、39名が別名なのか未登録なのかを実物で調べる記録です。
親: [商品マスタ](../../specs/product-master/README.md)
設計: docs/handoff/line-supplier-aliases/design.md

2026-09-12、PR #3447をb29698faで本番反映。deploy34678372849と読取専用inspect34678551826成功。対象1134投稿はpending_review、マスタ110件、未照合39名。完全一致0・NFKC＋空白除去後一致0。名簿は端末内で復号し公開Gitには含めない。
backend/app/services/tcg_line_import_svc.py:60 の_split_senderはマスタ名＋空白の前方一致、その後最初の空白で切る。backend/app/services/tcg_line_android_parser.py:37はタブで名前全体を切り出す。未照合のうち12名は既存PC名＋空白の前方一致候補。これだけで人物の同一性は確定しない。
投稿先会社へのメンションは自己紹介とは区別する。同名・類似名・会社名の出現だけで統合しない。
backend/app/line_import_admin.pyの暗号化inspectに保存済みLINE原文の指紋・投稿日時・仕入先コードを追加し、端末原本との同一性を調べる。500件上限の正の一致を証拠にし、未一致を真の未登録とは断定しない。
ADR確認: ADR-072スキーマ明示、ADR-154既存解析維持。ユーザーは元PC経路を壊さず接続することと、都度承認不要での修正・マージ・実テストを明示。列/対応表の製品実装は証拠確認後。
