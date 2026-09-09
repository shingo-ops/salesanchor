# インポート関連・進捗APIの実物確認

この文書は、引き継ぎ内容と今回確認したコードの事実を分けて記録する。
親: [商品マスタ](../../specs/product-master/README.md)
design: docs/handoff/pmg-import-delivery-ssot/design.md
対象ADR: ADR-113, ADR-154, ADR-072（索引を検索・本文参照）
確認日: 2026-09-10
HEAD/origin/main: 8206ba2844921c1efb3ca4fd647230e76bb0c5c6（fetch後差分0）

## 今回確認した事実

- backend/app/services/tcg_line_import_svc.py:299-302 は最新本文と先頭日時を組み合わせる。
- 同ファイル:324-429 は投稿を毎回新設し、旧投稿をsupersedeする。再利用分岐なし。
- 同ファイル:476-495 はファイルSHAの重複のみ防止する。
- backend/app/routers/tcg_line_import.py:560-644 は保留確定時の投稿作成とcommit後queue起動。
- backend/app/tcg_config.py:17-31 はTCG_SCHEMAをtenant_NNNに検証し、既定tenant_004。
- backend/app/auth/dependencies.py:453-482 は中央super-admin権限。一般テナントadminは403。
- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:223-325 は既存投稿・抽出・解析表とanalysis_results.extraction_item_idのUNIQUE。
- backend/app/services/tenant.py のTCG表名検索: 新規TCG表作成処理なし。TCG初期表は専用migrationで作成。
- 作業場所・台帳検査はexit 0。UUIDは4aa45d5a-7c65-4150-bd2e-ac0f45255edc。作業場所再作成なし。
- 競合候補の旧台帳release/tcg-import-fk-order-fixはgh pr listでPR #3296 MERGED確認。

## 引き継がれた観測（今回の本番実測ではない）

仕様v1の観測表をdesign.mdに原文保存。抽出done966/empty72/error57、商品・結果各23456、errorに結果166、NOTE_JA1234/2855を現在値や保証に読み替えない。
元報告の指定パス4本は本セッションで内容を再確認していない。生の本番データをコミットしない。
本番・Gemini・実配信は操作しない。APIコンテナ実コード・外部シート・NOTE_JA空欄原因・全件再解析済みかは未確認。
