# recon — PayPal請求書発行インシデント 現在地把握

対応 brief: 本インシデント対策ADR（ADR-1000）の R1〜R6。
読み取り専用 / 変更・修復なし。

実コードを **フルパス:行番号** で引用（短縮禁止）。
確認できないものは各項目に「不明」と明記。

---

## R1. PayPal Invoicing統合の実装箇所

### サービス層（backend/app/services/paypal_payments.py）

| 関数 | 行番号 | 役割 |
|---|---|---|
| create_and_send_invoice | :549-629 | PayPal Invoice 作成（DRAFT）→ 送付（SEND）→ GET で URL 取得 |
| get_invoice_status | :632-668 | PayPal Invoice ステータス取得（PAID 判定） |
| register_webhook | :434-470 | INVOICING.INVOICE.PAID + DISPUTE 系購読 |
| verify_webhook | :473-513 | 受信 webhook 署名検証 |
| create_order（旧・dormant） | :213-291 | 旧 Orders API（温存中・既存テスト維持のため削除しない） |
| capture_order（旧・dormant） | :303-354 | 旧 Orders API capture（同上） |

### ルーター層

| エンドポイント | ファイル:行 | 役割 |
|---|---|---|
| POST /invoices/{id}/paypal-link | backend/app/routers/invoices.py:602-707 | 請求書から PayPal Invoice 作成・送付・DB 保存（issue_paypal_link） |
| POST /invoices/{id}/paypal-confirm | backend/app/routers/invoices.py（同ファイル中） | get_invoice_status で手動入金確認 |
| POST /integrations/{id}/paypal/register-webhook | backend/app/routers/integrations.py:523 | webhook 自動登録 |
| POST /integrations/{id}/paypal/test-invoice | backend/app/routers/integrations.py:584 | テスト請求書発行（sandbox 用） |
| POST /api/v1/paypal-webhook（公開） | backend/app/routers/integrations.py:802 | INVOICING.INVOICE.PAID 受信・入金反映 |

### フロント呼び出し元

| ファイル | 役割 |
|---|---|
| frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx | 「PayPal請求書を送付」ボタン → /invoices/{id}/paypal-link |
| frontend/src/pages/integrations/PaypalIntegrationPage.tsx | 決済テスト UI → /test-invoice |

### PayPal Invoicing 3ステップの実行場所

1. **作成（DRAFT）**: backend/app/services/paypal_payments.py:591-607
   — POST /v2/invoicing/invoices
2. **送付（SEND）**: backend/app/services/paypal_payments.py:610-623
   — POST /v2/invoicing/invoices/{id}/send
3. **URL取得（GET）**: backend/app/services/paypal_payments.py:521-546（_fetch_view_urls）
   — GET /v2/invoicing/invoices/{id} で recipient_view_url 取得

---

## R2. 既存のスモーク/統合テストの有無

### PayPal 関連テストファイル一覧

| ファイル | 種別 | CI 実行 | 実 Sandbox 呼び出し |
|---|---|---|---|
| backend/tests/test_paypal_invoicing.py | モック（httpx.post/get をすべて patch） | YES | **なし** |
| backend/tests/test_paypal_payment_link.py | モック | YES | なし |
| backend/tests/test_paypal_return.py | モック | YES | なし |
| backend/tests/test_paypal_webhook.py | モック | YES | なし |
| backend/tests/test_paypal_integration.py | モック | YES | なし |
| backend/tests/test_paypal_test_invoice.py | モック | YES | なし |

### 確認事項の回答

- **実 Sandbox を叩くテストは存在するか**: **存在しない**
  - test_paypal_invoicing.py:34-36（patch.object(svc, "_get_token", ...)、patch.object(svc.httpx, "post", ...)、patch.object(svc.httpx, "get", ...)）— 全 httpx 呼び出しをモック
- **CIで実際に実行されているか**: YES（.github/workflows/test.yml:206 pytest でフルスイート実行）
- **今回なぜ落ちなかったか**: モックがすべての httpx 呼び出しをインターセプトするため、実 PayPal API が壊れていてもテストは緑になる（構造的）

---

## R3. 完了報告がマージ/納品まで到達した経路

### 対象 PR

- **PR #1980**: feat(paypal): 決済を PayPal Invoicing 方式へ移行（ADR-101 改訂・案Y 併存）
- ブランチ: feature/morimoto/paypal-invoicing → develop
- マージ日時: 2026-06-11T23:43:29Z
- マージコミット: e08131d6（git log より）

### CI チェック一覧（全件の結果）

| チェック | 結論 |
|---|---|
| pytest (SQLite + PostgreSQL RLS) | **SUCCESS** |
| process-artifacts gate | **SUCCESS** |
| Karte Visual Gate (chromium) | **SUCCESS**（ビジュアル差分） |
| Chromatic Snapshot | **SUCCESS** |
| Frontend lint & custom checks | **SUCCESS** |
| ADR index is up to date | **SUCCESS** |
| ADR-072 tenant schema lint | **SUCCESS** |
| Migration Guard | **SUCCESS** |
| Secret Scan | **SUCCESS** |
| evaluator（Claude pipeline） | **SKIPPED**（→ R5 参照） |
| reviewer（Claude pipeline） | **SKIPPED** |
| Governance Check（Claude pipeline） | **SKIPPED** |

### 人間レビュー

- **PR Approve**: "reviews":[] — **ゼロ件**
- 承認した人間レビュアーなし

### 完了報告の根拠（PR 本文より）

> 検証: backend: test_paypal_invoicing.py(10) + paypal 系全 46 green、test_invoices.py/test_deals.py 62 green（Python 3.11 + pinned deps の clean venv で実行）。

→ テスト結果はすべてモックによる green。実 PayPal Sandbox への疎通確認は行われていなかった（PR 本文に sandbox 実機確認の記録なし）。

---

## R4. process-artifacts gate がなぜ止めなかったか

### gate の判定ロジック（scripts/check-process-artifacts.js:237-302）

gate が検証するのは以下の **形式的要件** のみ:

| 検証内容 | 確認方法 |
|---|---|
| ### 標準ワークフロー確認 セクション存在 | PR 本文の正規表現マッチ（:83） |
| 対象 ADR が docs/adr/ に存在 | ファイル存在確認（:253-261） |
| recon.md が存在し path:N 形式の引用がある | ファイル存在 + FILE_LINE_RE マッチ（:105-130） |
| 設計 doc が存在し「基準/検証方法」表がある | \|\s*基準\s*\| マッチ（:137-152） |
| ADR 参照・recon 相互参照 | 文字列包含（:153-161） |

### 今回の通過理由

- docs/handoff/paypal-invoicing/recon.md → **存在し、file:line 引用あり**（→ R1で確認）
- docs/handoff/paypal-invoicing/design.md → **存在し、基準表あり**（design.md:33-44 の | # | 基準 | 検証方法 | 表）
- ADR-1000 参照 → **あり**（新ADR）
- PR 本文 ### 標準ワークフロー確認 → **あり**

### gate が止められなかった構造的理由

gate は「成果物が揃っているか」の形式確認のみ。**「PayPal API の実機確認が完了しているか」を検証する仕組みはない**。

design.md:39 の受け入れ基準 #4 に「sandbox 実機(Evaluator)」とあるが、gate はこの Evaluator 結果を参照しない。gate は Evaluator の前に独立して動作するため、Evaluator が SKIPPED でも gate は PASS する。

---

## R5. Evaluatorは緑を出したのか、実行されていなかったのか

### ログで確定した事実

- "name":"evaluator","conclusion":"SKIPPED" — **Evaluator は実行されなかった**（緑を出したのではない）

### SKIPPED の原因（claude-pipeline.yml:63-70）

yaml
context:
  if: |
    github.event_name == 'workflow_dispatch' ||
    (
      github.event_name == 'pull_request' &&
      startsWith(github.event.pull_request.head.ref, 'claude-impl/') &&
      github.event.pull_request.base.ref == 'develop'
    )


claude-pipeline の全ジョブは context ジョブの成功を needs に持つ。context が起動しないと後続は全 SKIPPED になる。

context が起動する pull_request 条件: **claude-impl/ で始まるブランチ**のみ。

PR #1980 のブランチ名 feature/morimoto/paypal-invoicing は claude-impl/ ではないため、context が SKIPPED → evaluator も SKIPPED。

### F3 の確証

ドラフト F3「ビジュアル差分 Evaluator はこの不具合を検知しなかった」については:

- **「実行された上で緑を出した」ではなく「そもそも実行されていなかった」が正確な事実**
- feature/morimoto/* ブランチで作成した PR は claude-pipeline が一切起動しない
- Evaluator が「守備範囲外で構造的に検知不能」という結論は、この PR に対しては前提が崩れている（実行の有無以前の問題）

---

## R6. 他の外部API連携に同じ穴がないか（横展開）

| 外部API連携 | スモーク/統合テスト有無 | テストの path:line | CI実行 | 備考 |
|---|---|---|---|---|
| PayPal Invoicing | モックのみ | backend/tests/test_paypal_invoicing.py:28-54 | YES（モック） | 実 Sandbox テスト **なし** |
| FedEx | **実 Sandbox テストあり（スキップ）** | backend/tests/test_fedex_sandbox.py:1-50 | **SKIP**（env var 未設定） | FEDEX_SANDBOX_CLIENT_ID が CI secrets に未登録 → 常時スキップ |
| Meta/Facebook Graph | モックのみ | backend/tests/test_meta_graph.py（patch 11件） | YES（モック） | 実 Graph API テスト **なし** |
| Firebase Auth | テストファイル見当たらず | — | 不明 | フロント側認証のみの可能性 |
| Discord Bot | モックのみ | backend/tests/test_discord_bot_receiver.py（patch 13件） | YES（モック） | 実 Discord API テスト **なし** |

### 注目点

- **FedEx のみ** 実 Sandbox テストファイル（test_fedex_sandbox.py）が存在するが、CI secrets に環境変数が未登録のため **常時 SKIP**。今回の PayPal と同じ構造的穴が存在する。
- その他（Meta・Discord・Firebase）は実 API テストが存在せず、モックのみ。

---

## 付帯メモ（scope外・調査しない）

- fix PR #2237〜#2244 の連発（2026-06-12 に4本）から、#1980 マージ後に実 sandbox 試行でエラーが連続発生したことが推測される（invoicer email 欠落・重複 invoice 番号・ID 取得失敗）。これは R1〜R6 の範囲外につき、別件として調査する場合は独立タスクを切ること。
- backend/tests/test_paypal_test_invoice.py の内容（R2 で「モック」と分類したが詳細未読）は、本 recon の範囲外。
- frontend/src/pages/integrations/PaypalIntegrationPage.tsx に「决済テスト」ボタン（sandbox 用）があり、手動 sandbox 疎通の経路は UI上存在していた。ただし今回の完了報告でこのボタンを使ったかは不明（PR 本文に記録なし）。
