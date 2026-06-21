# ADR-1000: 外部API連携の実Sandboxスモーク必須化と本番デプロイ安全化の区切り

## Status
Accepted（GO: Shingo 2026-06-18）

## 背景

PayPal 請求書発行の虚偽完了報告インシデントを受け、外部API連携の変更を実Sandboxスモークと人の確認まで含めて扱う方針を固めた。
その後の recon で、本番デプロイ側にはすでに `deploy.yml` による health check と auto-rollback が実装済みであることが分かった。

## 決定

本 ADR では、PayPal 対策の多層防御を次のように区切る。

- **PR-A / PR-B**: 実Sandboxスモークの必須化
- **PR-C**: 外部API変更の自動検出
- **PR-D**: 完了の定義を人の実動作確認まで含める
- **PR-E**: ユーザー影響変更の Shingo GO 必須化
- **PR-F**: 本番デプロイ安全化

### PR-F の扱い

- `deploy.yml` には **Pre-deploy DB backup**、**backend 健康チェック**、**失敗時の自動ロールバック**、**blue-green 切替** が既に入っている。
- よって PR-F のうち、**deploy 後の health check + auto-rollback は既達** とする。
- ただし **別環境での事前リハーサル** は、現時点ではステージング環境がなく、本番以外での確認基盤が未整備である。
- この事前リハーサルは、ローンチ後にステージング環境を構築したうえで実施するバックログとする。
- 外部 health の `Verify deployment` は現状は警告表示のみで、auto-rollback とは連動していない。ここは将来、誤検知リスクを評価してから扱う。

## 根拠

- `.github/workflows/deploy.yml:127-139` Pre-deploy DB backup
- `.github/workflows/deploy.yml:546-634` backend health check + auto-rollback
- `.github/workflows/deploy.yml:318-333` blue-green backend cutover / force-recreate
- `.github/workflows/deploy.yml:666-678` 外部 health は警告のみ
- `.github/workflows/qa-smoke.yml:37-65` qa-smoke は本番相当の重い総合スモーク
- `tests/qa-smoke/utils/db-assert.ts:35-42` DATABASE_URL 必須で、軽量 health probe ではない

## バックログ

1. ステージング環境の構築
2. PR-F の事前リハーサルをステージング上で実施
3. 外部 health の auto-rollback 連動を誤検知リスク込みで再評価

## 関連

- `docs/handoff/incident-paypal-invoicing-false-complete/design.md`
- `docs/handoff/incident-paypal-invoicing-false-complete/recon.md`
- `docs/STANDARD-WORKFLOW.md`
