# recon: 新テナントのひな形と、移行で保つ既存テナントの形をそろえる（段5・段階1、2026-10-07）

基準: origin/main に、#4012（所有者・管理者の権限の計算）と、その下の #3986 を積んだ状態。値（件数・表名・列名）だけを記載する。元の調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- 検索語: tenant template / create_tenant_schema / ADR-1005 / ADR-1007。関係する ADR: docs/adr/ADR-1005-migration-run-once-ledger.md（段階1：テナントの正本を 1 つに。方向性は Accepted）。ADR-1007（構造だけ・一度だけの方針）は別ブランチで起案中。

## 1. 事実：なぜ食い違うか
1. 新テナントは backend/app/services/tenant.py の create_tenant_schema が、ひな形（_TENANT_TABLES_SQL。41 表・506 列）から作る（tenant.py:1620 以降）。
2. 既存テナントの構造は、scripts/run_all_migrations.sh に登録された migration を、毎デプロイ流して保つ（scripts/run_all_migrations.sh:12-15、.github/workflows/deploy.yml の migration の step）。
3. 後から足した列・表は、ひな形に反映されず、migration にだけある。新テナントは、次のデプロイで migration が全テナントを走査するまで、古い形のままになる。移行の再実行を止める計画（ADR-1005 段階2）の前に、ひな形を正本にしておく必要がある。
4. 静的な照合（手元）の結果: テナント全体に繰り返す migration の列の追加のうち、ひな形の既知の表に列が無いものが 42 列（15 ファイル。例: staff.phone、staff.avatar_token、invoices・leads・meta_messages の列）、ひな形に表が無いものが 17〜20 表。静的な照合は下限で、正確な差は PG で流して比べるまで確定しない（deals は tenant.py:425-426 で意図して除去済み。tenant_004 だけの鎖に属するものも混ざりうる）。

## 2. この PR の第 1 コミット（試験だけ。赤で出す）
- backend/tests/test_tenant_template_parity_pg.py: 使い捨ての DB を作り、共有の public 表を用意し、create_tenant_schema で新テナントを作り、形（表・列の型・既定値・索引）を撮る。登録された migration のうち全テナントを走査するもの（103 本、登録順）を、1 本ごとに別のトランザクションで流し、もう一度撮って、変わっていないことを確かめる。変わったものが、ひな形に足りない（または余る）一覧になる。
- ゲートは CI が設定する RLS_ADMIN_DATABASE_URL（backend/tests/test_rls_bootstrap_ordering.py と同じ形）。別の DB を使うのは、migration のループが全テナントのスキーマを走査するので、並列の他の試験のスキーマに触れないため。流せなかった migration は、形を変えないので、一覧の末尾に報告する（差には数えない）。
- 今の main では赤になる見込み（上の 4）。CI の失敗の出力が、直す一覧の正本。ローカルに PG は使わない。DB 不要の 2 本（差の整形と、対象 migration の抽出）はローカルで通る。

## 3. 次のコミット（この PR では、まだしない）
- 赤の一覧を設計担当が見てから、tenant.py のひな形を一覧どおりに直す。意図して外す列・表（例: deals）は、決めて、試験の許可に書く。既存テナントは変わらない（新テナントの作成だけ）。戻し方: PR の revert。

## 4. 未確認・実施していないこと
- PG での実行結果（赤の一覧）: CI の最初の実行が最初の確認。
- 新しい空の DB で、共有の public 表の用意（_bootstrap_public_shared）が通るか: 既存の試験と同じ手順だが、空の DB での実行は CI が最初。
- 手元で SQL を流しての確認はしていない（書き込みを防ぐフックが手元の DB 実行も止める）。
