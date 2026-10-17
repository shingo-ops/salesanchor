# recon: products.type_master_id の削除（ADR-1026）

基準: `git fetch` 後の origin/main 1e7a68980（2026-10-17 20:24 JST）。本番は ADR-1024 の読み取り専用の道（ai_ro ビュー・カタログ）で読んだ。生出力は /tmp/CC報告ファイル/work-id-mismatch/（r2/ r3/ を含む）と /tmp/CC報告ファイル/drop-products-type-master-id/recon/。

## 既存 ADR の検索
- `git grep -n -i -E "work_id|type_master_id|tcg_type" origin/main -- docs/adr docs/specs` と docs/adr/FEATURE-INDEX.md を見た（01-adr-grep.txt）。
- 作品の正本: docs/specs/master-ssot-migration/design.md:13（作品単位で type_master に紐付ける）、:22（products.work_id は INTEGER で type_master.id を参照）。
- 列を足した根拠: docs/handoff/product-format-kind-fk/design.md:9,13,26（「商品は6分類を全て直接持つ」「products に type_master_id FK 追加」）。ADR-156 本文（docs/adr/ADR-156-product-classification-tree-and-master-separation.md:26-28）に "products.type_master_id" の語は無い。
- products.type_master_id の役割を決めた ADR は無い。

## 1. 本番の値（共用 tenant_id IS NULL 1420 行）
| 組 | 件数 |
|---|---|
| work_id と type_master_id が一致 | 1338 |
| 両方あって不一致 | 9 |
| type_master_id だけ空 | 73（id 465990〜466088、2026-10-07〜10-17 の登録。tcg_type が空の 73 行と同じ行） |
| tcg_type が指す作品と work_id が不一致 | 0 |

不一致 9 行（work_id → 作品 / type_master_id → 作品）: 8 Lose&Whisp ヴァイス/その他、27 異種族レビュアーズ ヴァイス/ユニオンアリーナ、48 魔法少女にあこがれて ヴァイス/ユニオンアリーナ、53 神速の拳 ワンピース/ポケモン、125081 30th CELEBRATION FUTURISTIC BOX ポケモン/遊戯王、440363 25th Anniversary Golden Box ポケモン/遊戯王、440561 FB-09 ドラゴンボール/ポケモン、440576 レトロカード バルク ポケモン/その他、458213 世界最強の戦士 ワンピース/ドラゴンボール（04a-mismatch9.txt）。
外部の情報で work_id の作品と一致: 8 件（r2/A-table.md、出典 URL 付き）。440576 は外部に情報が無い。docs/handoff/master-ssot-migration/design.md:70-88 に PO 判断（2026-09-19）でポケモンに分類した記録がある。

## 2. 読み書きしている場所
- products.type_master_id を読む・書く・返すコード: 0 件（backend・frontend・scripts・テスト・fixture・Pydantic・SQLAlchemy・openapi。drop.../recon/grep_all.txt）。
- 在庫一覧 GAS（~/tcg-viewer-1hc-release、~/tcg-viewer-1tb-head、~/tcg-client-viewer）: type_master・work_id・tcg_type の文字列 0 件（r2/b3-gas-grep.txt）。
- 中分類マスタの画面（/super-admin/analysis-rules?section=type-master）は type_master だけを編集し、products に触らない（backend/app/routers/super_admin_tcg.py:40,166,185,224）。
- 作品で products と type_master を結ぶ処理は work_id を使う（例 backend/app/routers/buyback_prices.py:416,428、backend/app/services/tcg_analysis_review_svc.py:75）。
- 同じ名前の別の列（対象外）: product_formats.type_master_id（backend/app/routers/super_admin_product_formats.py:30,93）、product_format_game_links.type_master_id（backend/app/services/tcg_product_master_svc.py:109,134-135）。
- 列が出てくる場所は migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql:19-22 と scripts/run_all_migrations.sh:794 の登録行だけ。
- 値を入れた UPDATE/INSERT は migrations・scripts・docs/handoff・~/CC報告ファイル-keep に見つからない（r2/b4-*.txt）。

## 3. DB の依存（本番 pg_depend ほか、drop.../recon/q1〜q5）
- 外部キー products_type_master_id_fkey（→type_master(id) ON DELETE SET NULL）、索引 idx_products_type_master_id、ビュー ai_ro.public__products。
- RLS ポリシー・トリガー・関数本文・拡張統計に type_master_id は無い。

## 4. 列の数の上限
- 本番 public.products: attnum 最大 1600、生きている列 57、消した列 1543。type_master_id は attnum 1007（q3.out）。
- 20260922_010000 の `ADD COLUMN IF NOT EXISTS type_master_id` は毎デプロイ流れる（scripts/run_all_migrations.sh:794、適用済み記録の表は無い・ADR-1005）。列が在る今は何もしないが、列を消すと次から ADD が走り、上限で失敗する。

## 5. migration の仕組み
- ai_ro ビュー: 先頭で `DROP SCHEMA IF EXISTS ai_ro CASCADE`（migrations/20261017_125900_drop_ai_ro_views.sql:7、scripts/run_all_migrations.sh:80）。最後に EXIT trap で作成（run_all_migrations.sh:86-106、列は pg_attribute から自動列挙 create_ai_ro_views.sql:34-41）。
- runner: ファイルごとに `psql -v ON_ERROR_STOP=1`、set -e（run_all_migrations.sh:20,25,61-66）。
- 列を消した前例: migrations/20260916_120000_phase_c_drop_tcg_uuid.sql（DROP CONSTRAINT IF EXISTS → DROP INDEX IF EXISTS → DROP COLUMN IF EXISTS）。
- CI: migration-guard.yml Check 6（DROP COLUMN は PR 本文に ADR 番号が必要 :335-392）、Check 10（同じ列の ADD→後で DROP を失敗にする scripts/check-migration-column-churn.js、:512-546）、Check 2（run_all_migrations.sh への登録）。
- バックアップ: deploy.yml:195-216 が migrations の変更時にデプロイ前の pg_dump を取る（scripts/backup.sh の場所 /home/ubuntu/backups/postgres/）。
- GO: DROP COLUMN を含む migration は PO 本人の GO が必要（docs/STANDARD-WORKFLOW.md「PO 本人の GO が必須の例外」）。backend/CLAUDE.md の additive-only 原則は「destructive 変更は PO 確認＆ADR 起案必須」。

## 6. 同時作業
- open PR で products・type_master_id・ai_ro を直接変えるものは無い（drop.../recon/open_prs.txt）。

## 外部事例
- 不要と判断。自分の DB の列の参照ゼロと上限の事実で決まり、外の事例で判断が変わらない。PostgreSQL の DROP COLUMN が attnum を戻さないことは本番の実測（消した列 1543・最大 1600）で確かめた。
