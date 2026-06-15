# recon — FedEx ETD / Stampステップ障害調査

**仕事名**: fedex-etd-stamp-recon  
**日付**: 2026-06-15  
**担当**: Hikky-dev  
**目的**: (1) FedExレターヘッド・署名登録（ETD）の現状把握、(2) Stampステップが毎回失敗する原因の特定  
**制約**: 実装変更なし・recon のみ

---

## ADR 検索結果

```
git grep -i "fedex\|etd\|letterhead\|stamp" docs/adr/
```

| キーワード | 該当 ADR |
|-----------|---------|
| FedEx Integrator Provider / キャリア連携 | **ADR-123** |
| FedEx Rates / OAuth / アカウント番号 | **ADR-125** |
| FedEx Label Validation ウィザード / 環境セレクタ | **ADR-129** |
| main デプロイ成功スタンプ | **ADR-116** |
| ETD / letterhead / signature / 電子貿易書類 | **該当なし**（grep 済み・ADR 未起案） |
| FedEx Ship 専用 ADR | **不整合あり**（詳細↓） |

### ADR 番号不整合（要確認）

- `backend/app/services/fedex_ship.py:1`: `FedEx Ship API / Pickup API クライアント（ADR-128）` と記載
- `docs/adr/ADR-128-audit-log-coverage-high.md:1`: 実際は「監査ログ カバレッジ補完（高重要度2系統）」
- `docs/adr/FEATURE-INDEX.md:17`: `FedEx / DHL → ADR-103 ／ ADR-123 ／ ADR-128` と記載
- **事実**: FedEx Ship 専用の ADR は存在しない（fedex_ship.py は ADR-123 の実装拡張として作られたが、ADR-128 番号をコメントに誤記した可能性）

---

## Topic 1: FedEx ETD / レターヘッド・署名登録

### 現状（事実）

ETD（Electronic Trade Documents / 電子貿易書類）の実装は **存在しない**。

| 調査箇所 | 確認内容 |
|---------|---------|
| `backend/app/services/fedex_ship.py:112-133` | `create_shipment()` の payload 構築。`customsClearanceDetail` あり。`etdDetail`・`requestedDocumentCopies` なし |
| `backend/app/services/fedex_ship.py:57-195` | ラベル発行・サービスタイプ・寸法・関税情報を処理。レターヘッド/署名フィールドなし |
| `backend/tests/test_fedex_ship.py` | mock test。ETD フィールドのテストケースなし |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:55-57` | スコープは Label Validation ウィザード 5 スプリント（3.1〜3.5）。ETD/レターヘッド/署名は対象外 |
| `docs/adr/ADR-123-carrier-integrator-provider.md` | Validation 必須項目に「インボイス」を記載。ETD の具体的な実装要件は未定義 |
| `docs/research/fedex-integrator-provider-application-2026-06-09.md:123` | Validation 提出リストに「Ship トランザクション 3形式（PDF/PNG/ZPL）」「インボイス」あり。ETD 専用登録は言及なし |

### FedEx ETD の全体像（外部調査）

FedEx ETD（Paperless Trade）を有効にするには、Ship API リクエストに以下が必要:

```json
{
  "requestedShipment": {
    "customsClearanceDetail": {
      "importerOfRecord": {...},
      "customsValue": {...},
      "commodities": [...]
    },
    "shippingDocumentSpecification": {
      "stampType": "INCLUSIVE",
      "generalAgencyAgreementDetail": {...},
      "etdDetail": {
        "requestedDocumentCopies": ["COMMERCIAL_INVOICE"],
        "uploadedDocuments": [
          {
            "id": "LETTERHEAD_IMAGE_ID",
            "documentType": "LETTER_HEAD",
            "referenceIndex": "LETTER_HEAD"
          },
          {
            "id": "SIGNATURE_IMAGE_ID",
            "documentType": "SIGNATURE",
            "referenceIndex": "SIGNATURE"
          }
        ]
      }
    }
  }
}
```

事前準備（アップロードステップ）:
- `POST /ship/v1/shipments/images` で LETTER_HEAD（会社レターヘッド画像）をアップロード
- `POST /ship/v1/shipments/images` で SIGNATURE（署名画像）をアップロード
- 返却される `docId` を DB に保存し、以後の Ship リクエストで参照

### 不明点（ETD）

| # | 不明点 | 解消方法 |
|---|-------|---------|
| 1 | ETD を Validation（PIW/Cover Sheet）提出の必須項目として FedEx が要求するか | APAC FedEx API チーム（apacfedexapi@fedex.com）確認 |
| 2 | レターヘッド・署名は FedEx テナントごと（会社ごと）に1枚保存するか、出荷のたびにアップロードするか | FedEx API ドキュメント精読 + APAC 確認 |
| 3 | 画像 ID の有効期限（FedEx 側で削除されるか） | FedEx API ドキュメント確認 |
| 4 | `stampType: "INCLUSIVE"` vs `"EXCLUSIVE"` の使い分け要件 | FedEx API ドキュメント確認 |

### 危険変更の判定（ETD 実装時）

| 変更 | 危険区分 | PO GO 要否 |
|-----|---------|------------|
| `migrations/YYYYMMDD_HHMMSS_add_fedex_etd_docs.sql` — テナント用画像 ID 保存列/テーブル追加 | DB migration（additive） | **PO GO 必須** |
| `deploy.yml` への migration ステップ追記 | deploy.yml 変更 | **PO GO 必須** |
| `backend/app/services/fedex_ship.py` — ETD フィールド追加 | コード変更（危険なし） | 通常 PR |
| FedEx 側でのアカウント設定（Paperless Trade 有効化） | 外部 GUI 操作 | **Shingo 直接操作** |

---

## Topic 2: Stamp ステップが毎回失敗する原因

### 対象

`.github/workflows/deploy.yml:730` の「Stamp main deploy date in active-work.md」ステップ（ADR-116）

### 根本原因（事実・ログ証拠あり）

**Branch Protection が PIPELINE_PAT による direct push to develop を拒否している。**

GH Run 27532347653（2026-06-15 成功デプロイ）での Stamp ステップ出力:

```
remote: error: GH013: Repository rule violations found for refs/heads/develop.
remote: - 11 of 11 required status checks are expected.
remote: - 2 of 2 required status checks are expected.
! [remote rejected]   HEAD -> develop (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/shingo-ops/salesanchor.git'
##[error]Process completed with exit code 1.
```

`.github/workflows/deploy.yml:730-779` に記載されたステップの処理フロー:

1. `deploy.yml:739`: `git checkout -b "stamp-develop-<run_id>" origin/develop`
2. `deploy.yml:740-767`: Python で active-work.md の DONE 行に main 日付を書き込む
3. `deploy.yml:774-775`: `git add` → `git commit`
4. `deploy.yml:776`: `git pull --rebase origin develop`
5. `deploy.yml:777-779`: `git push ... HEAD:refs/heads/develop` ← **ここで拒否される**

### ステップが「成功に見える」理由

`deploy.yml:732`: `continue-on-error: true`  
→ Stamp が exit 1 でも deploy job 全体は SUCCESS として終わる  
→ GitHub Actions 上では deploy=success、Stamp 内部=failed（ログを見ないと気づかない）

### 追加の失敗パターン（Stamp 到達前の deploy 失敗）

最近の deploy 失敗ラン（スタンプ以前に失敗）:

| Run ID | 失敗理由 | Stamp 実行可否 |
|--------|---------|--------------|
| 27547628994 | Workflow file issue（deploy.yml 構文/内容エラー） | 実行されない（workflow 起動失敗） |
| 27523866836 | `feat: active-work.md ライフサイクル全自動化` 変更関連 | `if: success()` でスキップ |
| 27523855750 | PR #2213 マージ起因の deploy 失敗 | スキップ |
| 27523068133 | `/home/***/salesanchor/.env: line 44: syntax error near unexpected token 'newline'` → VPS .env ファイル破損 | スキップ |

### 成功した直近のスタンプ実行

| Run ID | 日時 | Stamp 結果 |
|--------|------|-----------|
| 27532347653 | 2026-06-15 08:00 JST | **STAMPED 75 rows with main:2026-06-15** — ただし push が Branch Protection で拒否 |

**注意**: STAMPED 75 rows は active-work.md 上の DONE 行ほぼ全件に日付を打った。この「全件スタンプ」は本来の意図（その deploy で本番に出た PR のみ）とずれている可能性がある。

### 関連 PR

| PR | 内容 |
|----|------|
| #1712 (MERGED) | ADR-116 main デプロイ成功スタンプ 初期実装 |
| #2219 (OPEN) | `feat: active-work.md ライフサイクル全自動化`（deploy.yml の Stamp ステップを manifest ベースに差し替える提案） |

### 修正候補（設計は別途）

| 案 | 内容 | 危険区分 |
|----|------|---------|
| A. PIPELINE_PAT に Branch Protection bypass 権限を付与 | GitHub Repository Ruleset 変更（`gh api` による Ruleset Bypass actor 追加） | **不可逆操作に準ずる・Shingo 確認必須** |
| B. 直接 push 廃止 → PR 経由で develop に stamp を反映 | deploy.yml 変更 | **PO GO 必須（deploy.yml 変更）** |
| C. PR #2219 の manifest-based stamp を採用 | deploy.yml の全件スタンプを廃止し、release PR manifest 対象のみに限定 | **PO GO 必須（deploy.yml 変更）** |

---

## 不明点まとめ（Shingo 判断が必要なもの）

| # | 不明点 | 判断が必要な理由 |
|---|-------|----------------|
| 1 | PIPELINE_PAT の現在の権限スコープと Ruleset bypass の有無 | GitHub Ruleset 設定は PO のみ確認可能 |
| 2 | Stamp 修正の優先度と採用案（A/B/C） | deploy.yml 変更は PO GO 必須 |
| 3 | PR #2219 の GO/NOGO（FedEx 以外の変更も含む） | PO GO コメント待ち |
| 4 | ETD/レターヘッド登録が FedEx Validation の必須要件か | APAC FedEx API チーム（apacfedexapi@fedex.com）への確認が必要 |
| 5 | ETD 実装を ADR として起案するか・タイミング | PO 判断（Validation 申請前か後か） |

---

## 調査したファイルと file:line 一覧

| ファイル | 行 | 確認内容 |
|---------|---|---------|
| `backend/app/services/fedex_ship.py:1` | — | ADR-128 コメント（番号不整合）|
| `backend/app/services/fedex_ship.py:57-195` | — | `create_shipment()` 全体。ETD フィールドなし |
| `backend/app/services/fedex_ship.py:112-133` | — | `requested_shipment` 構築。`customsClearanceDetail` あり・`etdDetail` なし |
| `backend/tests/test_fedex_ship.py` | — | ユニットテスト。ETD テストケースなし |
| `backend/tests/test_fedex_sandbox.py` | — | Rates API 疎通テスト。ETD なし |
| `docs/adr/ADR-116-main-deploy-stamp.md:1-27` | — | Stamp ステップ仕様（continue-on-error: true・PIPELINE_PAT・develop push） |
| `docs/adr/ADR-123-carrier-integrator-provider.md` | — | Validation 必須項目にインボイス記載。ETD 未定義 |
| `docs/adr/ADR-125-fedex-rates-stage1.md` | — | OAuth/Rates 実装。ETD 言及なし |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:49-57` | — | ウィザード 5 スプリント。ETD スコープ外 |
| `docs/adr/ADR-128-audit-log-coverage-high.md:1` | — | 実体は監査ログ ADR（FedEx 専用 ADR ではない） |
| `docs/research/fedex-integrator-provider-application-2026-06-09.md:123` | — | Validation 提出リスト。ETD 専用手順なし |
| `.github/workflows/deploy.yml:730-779` | — | Stamp ステップ全体 |
| `.github/workflows/deploy.yml:731` | `731` | `if: success()` — deploy 成功時のみ実行 |
| `.github/workflows/deploy.yml:732` | `732` | `continue-on-error: true` — Stamp 失敗がデプロイをブロックしない |
| `.github/workflows/deploy.yml:754-755` | `754-755` | 7列・DONE・main空欄の行のみ stamp 対象（現行ロジック） |
| `.github/workflows/deploy.yml:777-779` | `777-779` | `git push HEAD:refs/heads/develop` — Branch Protection で拒否される箇所 |
| `.claude-pipeline/active-work.md:228` | `228` | `feature/morimoto/main-deploy-stamp | IN_PROGRESS | #1712` — 実際は MERGED |

---

## 触っていない領域の確認

- SA-02 / QA Smoke / mobile shell / dashboard: 未参照
- 実装変更・migration 変更・deploy.yml 変更: 行っていない
- 本番 DB 操作・secrets 変更・FedEx 外部設定変更: 行っていない
- 危険操作: ゼロ
