# design.md — ④ status SSOT化（ADR-109）残作業 ／ Generator 実装指示

- 対応ADR: ADR-109（Accepted）
- 対応recon: `docs/handoff/status-ssot/recon.md`（2026-06-12）
- 前提: コード側（enum・直書き撤廃・旧値マップ撤去・statusPresentation 統合）は PR #1726 で実装済み。
  本書は**残作業のみ**を扱う。

## ゴール
本番DBの `leads.status` を日本語値から不変コードへ移行し、ADR-109 の受け入れ条件を完全達成する。

## 実装順（厳守）

### Step 1 — 表示の保険（先に入れる）
- `InboxConversationList.tsx:228` の status ラベル解決に fallback を追加
  （i18n キー欠落・未移行値の場合に生キー `leads.statusCode.〇〇` を表示しない。
  ADR-120 の安全フォールバック方針に合わせ、neutral 表示等にフォールバック）。
- 同型の「fallback 無し参照」が他に無いか、`leads.statusCode` の参照箇所を grep して確認。
- これを先に入れる理由: migration 適用前後のどの瞬間でも画面が壊れないようにするため。

### Step 2 — migration 本体
- 既存の `scripts/migrate_adr109_status_codes.py`（PR #1726 で追加済み）を活かすか、
  リポジトリの migration 標準（migrations/*.sql + deploy.yml の適用機構）に載せ替えるかは、
  **deploy.yml の既存 migration 適用機構に従う**（標準から外れる独自経路を作らない）。
- 内容:
  1. 全テナントの `leads.status` を 1対1 マッピングで日本語値 → 不変コードへ UPDATE
     （対象7値。マッピングは PR #1726 の enum 定義と完全一致させる）。
  2. `leads.status` の DB DEFAULT を `'新規'` → リード相当の新コードへ ALTER
     （migrations/003_add_phase1_tenant_tables.sql:85 由来の既存テナント残存分）。
- 冪等性: 再実行しても安全（既にコードの行は対象外になる WHERE 条件）であること。
- 事前検証: 実行前に値分布を SELECT し、7つの旧値＋新コード以外の想定外値が存在しないことを確認。
  想定外値があれば**移行を中断して報告**（勝手にマッピングを発明しない）。

### Step 3 — 検証
- migration 適用後（まず develop / 本番相当環境で素振り）:
  - 旧日本語値の行が 0 件（SELECT で確認）
  - DB DEFAULT が新コード
  - 受信箱・リード一覧・ダッシュボードで全7段階が正しい日本語ラベルで表示
  - Discord DM 受信での新規 lead がリード相当コードで作成される
- 過去の audit log の旧値はそのまま（書き換えない＝ADR-109 Scope外）。

## 危険カテゴリの扱い（必須）
- 本タスクは migrations（本番DB全行書き換え）を含む＝**危険カテゴリ**。
- develop へのマージは CI 緑で進めてよいが、**本番への適用（main マージ→デプロイ）は
  Shingo の明示 GO が出るまで行わない**。素振り結果を添えて GO を依頼すること。

## 受け入れ条件（ADR-109 の残り）
- [ ] 既存の全 leads 行が新コードへ移行済み・旧値の行ゼロ
- [ ] DB DEFAULT が新コード
- [ ] migration が deploy.yml 経由で自動適用される（手動VPS作業なし）
- [ ] 未移行値・キー欠落時も生キーが画面に出ない（Step 1 の保険）
