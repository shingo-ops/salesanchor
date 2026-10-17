# Opus 独立審査記録 — 受信箱「新規」バッジ

**審査対象**: ブランチ `release/inbox-new-assignment-badge`（`origin/main` 取り込み後）／設計 `docs/handoff/inbox-new-assignment-badge/design.md`
**審査日**: 2026-10-15（第1回）・2026-10-17（第2回・main 取り込み後）
**審査者**: 独立 Opus エージェント（立場＝反証を探す。コードの修正権限なし）
**設計担当（本記録の作成者）による再検証**: 2026-10-17。指摘はすべて**自分で一次情報（実ファイル・deploy.yml の実行順）を読み直して**裏を取った。

---

## 第1回（2026-10-15）＝ REVISE。3件すべて修正済み

| # | 指摘 | 対応 |
|---|---|---|
| 1 | マイグレーションの再実行でバッジが全消え（`scripts/run_all_migrations.sh` は毎デプロイ全件再実行） | 列の有無を `information_schema.columns` で見て、**列が無いときだけ** ADD + UPDATE。以降は `CONTINUE`。コミット `1cf44927d` |
| 2 | `markRead` ラッパーが第2引数を捨てていた（`opened` が届かない・型検査が落ちる） | signature を広げて `apiMarkRead` へ通す。コミット `1cf44927d` |
| 3 | PC の自動選択でバッジが勝手に消える | `autoSelectRef` で経路を区別（PO 決定「案ア」）。コミット `1cf44927d` |

## 第2回（2026-10-17・main 取り込み後）＝ REVISE。本記録で裁定する

### 採用（マージ前に直す）

| # | 指摘 | 一次情報での裏取り（設計担当が自分で確認） | 裁定 |
|---|---|---|---|
| **D1** | **本番反映の最中、`/api/v1/conversations` が全員 500**。新コードが客を受け始めてから、マイグレーションで列が増えるまでの窓 | `.github/workflows/deploy.yml:212` `- name: Deploy to VPS (code + env + docker compose)` の中で `bash scripts/blue-green-cutover.sh`（同ファイル :398 付近）＝**新コードが客を受け始める**。`- name: Run database migrations` は **:527**＝**後**。`backend/app/routers/meta_inbox.py:963-965` が `l.assignment_opened_at` を無条件に SELECT し、例外は `:980-985` で潰れて HTTP 500 | **採用**。読む側だけでなく**書く側**（`leads.py:1226` の mark-read・`:584` の担当変更リセット）も同じ窓で 500 になるため、フォールバックを3箇所に入れるより**2段出し（expand/contract）**が正しい。先例 `docs/handoff/llm-usage-ledger/design.md:89-103`（同じ deploy 順序を根拠に A1=表のみ → A2=コードへ分割）。本件も **PR-A（列だけ）→ PR-B（読み書き＋画面）** に分ける |
| **D2** | PC で自動選択された先頭会話は、**その行をクリックしてもバッジが消えない** | `useInboxState.ts:580-581` `selectLead` は `setSelectedLeadId(leadId)` のみ＝**同じ id では state が変わらない** → `:627-662` の効果（依存 `[selectedLeadId, loadMessages, markRead, loadLeadDetail]`。`markRead` は `:451` `}, []`、`loadLeadDetail` は `:427` `}, []`、`loadMessages` は `:406` `}, [t]` ＝実質 `[selectedLeadId]`）が再実行されず `markRead(id, true)` が飛ばない。行クリックは `InboxConversationRows.tsx:98` が `selectLead(conv.lead_id)` を無条件に呼ぶだけ | **採用**。KGI K2「開くと消える」に正面から反する |
| **D3** | 自動選択が URL に `lead_id` を書くため、**再読込すると開いていない会話のバッジが消える** | `useInboxState.ts:600-602` が `params.set("lead_id", ...)` ＝自動選択経路も通る。再マウント時は `:210-213` → `:240` で `selectedLeadId` が URL から復元され、`autoSelectRef` は false ＝ `markRead(id, true)` が飛ぶ | **採用**。「URL に lead_id がある＝利用者の明示操作」という前提（design.md:222-223）は、その URL を自動選択自身が書いているため成立しない |
| **D4** | design.md ④R7（:297）と「維持の仕組み」（:384）が、**撤回済みの方式**（`IF NOT EXISTS` ＋ `WHERE ... IS NULL`）をいまだ対策として掲げている | 現物 `migrations/20261015_090000_*.sql:47-63` は列の有無で守る形。テスト `backend/tests/test_inbox_new_assignment_badge.py:357` は逆に `IS NULL` の不在を assert | **採用**（次の担当者が欠陥を復活させる） |
| **D5** | recon/design の `file:line` 引用が実ファイルと不一致（11箇所） | 設計担当が全件、実ファイルで再確認した | **採用**。行番号は引用のたびに実ファイルから取り直す |
| **D6** | 本 PR 自身がコードに書いた行番号コメント（`useInboxState.ts:294-295` `:430-431`）が既に外れている | `:693-699` は検索絞り込み。自動選択は `:714-721` | **採用**。行番号ではなく識別子名で書く |
| **D7** | 「すべて既読」でバッジが画面から消えないことの**画面側テストが無い**（KGI K5 の半分） | `useInboxState.ts:435-446` の `...(opened ? { is_new_assignment: false } : {})` を外しても赤くならない | **採用** |
| **D8** | `toHaveBeenCalledWith` は「どれか1回が一致」で通るため assert が弱い（`useInboxState.autoSelectBadge.test.tsx:94`） | — | **採用**。`mock.calls` 全件を固定する |
| **D9** | A1/A2 のテストはマイグレーション本体の SQL を実行せず、分岐を Python で書き写している（`test_inbox_new_assignment_badge.py:367-375`） | CI `.github/workflows/migration-test.yml` は実 Postgres に2回流すが「2回目で NULL のままの行が壊れない」ことは見ていない | **採用**（PR-A で実 SQL を2回流す試験にする） |
| **D10** | design.md:319 の A13 が存在しないスクリプト名（`npm run check:i18n`）。実名は `check:i18n-missing-keys` | 実行して `npm ERR! Missing script` を確認 | **採用**。併せて A14 に「`check:all` は型検査を含まない」と明記する |

### 却下・保留

| # | 指摘 | 裁定 |
|---|---|---|
| **D11** | バッジ消去（`assignment_opened_at` 更新）が監査記録に残らない（`leads.py:1238` は `marked > 0` のときだけ記録、`table_name` も `meta_messages`） | **本便の対象外**（design.md ⑪ に継続として記録）。既存の mark-read の監査の形をこの便で変えると影響範囲が広がる。実害＝「誰がいつバッジを消したか」が追えないことのみ |

### 反証が見つからなかった点（＝正しいと確認された骨格）

- 他人が担当の会話を開いても**他人のバッジは消えない**（`leads.py:1229` の `AND assigned_to = :me`）
- **他人の担当者 ID は応答に出ない**（`meta_inbox.py:1008-1027` の dict に `assigned_to` なし）
- **同じ担当者への再保存ではリセットされない**（`leads.py:575-578`）／担当を外す（NULL）遷移も試験済み
- `leads.assigned_to` を書く経路の全数確認でリセット漏れなし（作成時の INSERT は NULL＝バッジが出る、が正しい）
- `assignment_opened_at` への書き込みは**2箇所だけ**（担当変更リセット・`opened=True`）。`_UPDATABLE_COLUMNS` に無いので API から直接書けない
- マイグレーション5観点（初回・2回目以降・`leads` 表が無いスキーマ・`assigned_to` が無いスキーマ・担当なしの行）すべて安全。新規テナント定義 `backend/app/services/tenant.py:377` と同期済み
- ADR-072（テナント文脈）・ADR-1016（書き込みルート台帳）・ADR-155（マイグレーションでの値の書き込み）に抵触なし
- 既存の `mark-read` 呼び出し（body なし）は壊れない

### 設計担当が別途確認した安全性（PR-A を単独で先に出してよい根拠）

- **訂正（2026-10-17・再審査の指摘1）**: 当初ここに「`leads` に VIEW も TRIGGER も無い」と書いたが**事実誤り**だった。`leads` を参照する VIEW は `migrations/20260612_120000_fix_company_stats_ssot.sql:44-70` の `v_company_stats` が**1本実在する**（`LEFT JOIN %I.leads l`）。ただし①列を明示しており `SELECT *` ではない ②同ファイル `:42` が `DROP VIEW IF EXISTS %I.v_company_stats CASCADE` してから作り直す、ため**列の追加に反応しない**。したがって結論（PR-A 単独投入は安全）は変わらない。**将来 `SELECT * FROM leads` の VIEW を足すと、この安全論は崩れる**（`CREATE OR REPLACE VIEW` は列の位置が変わると失敗する）。
- `leads` 上の **TRIGGER は0件**（`migrations/` の `CREATE TRIGGER` 全件を走査）。`ai_ro` の読み取り専用ビュー（ADR-1024）は `scripts/run_all_migrations.sh` が実行の先頭で全削除し EXIT trap で最後に作り直すため、依存が `ALTER` を止めることはない。RLS ポリシーは `migrations/003_add_phase1_tenant_tables.sql:190-193` のテナント分離1本のみで、列の追加に反応しない
- 追加列は **NULL 許容**（`NOT NULL` ではない）。旧コードは列名を明示して SELECT するため、列が増えても動作に影響しない
