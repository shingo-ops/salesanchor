# Recon — FedEx Smoke スイッチ ON（ADR-125 Stage 1 完了確認）

**実施日**: 2026-06-10
**対象ADR**: ADR-125
**担当**: Hikky-dev

---

## A. 現状の FedEx live smoke ステップ

| 項目 | file:line | 内容 |
|------|-----------|------|
| smoke ステップ定義 | `.github/workflows/deploy.yml:383` | `FedEx Rates live smoke (ADR-124 D2)` — FEDEX_SMOKE_ENABLED=true で実行 |
| SALESANCHOR_API_URL 欠落 | `.github/workflows/deploy.yml:390` | envs に `SALESANCHOR_API_URL` が含まれていないため smoke スクリプトが `require_env` で失敗する |
| トークン設定 | `.github/workflows/deploy.yml:418` | `SALESANCHOR_API_TOKEN: ${{ secrets.FEDEX_SMOKE_API_TOKEN }}` — Secret 未設定 |
| FEDEX_SMOKE_ENABLED | `.github/workflows/deploy.yml:421` | `${{ secrets.FEDEX_SMOKE_ENABLED }}` — Secret 未設定 |

## B. 認証の課題

| 項目 | file:line | 内容 |
|------|-----------|------|
| Firebase 認証必須 | `backend/app/auth/dependencies.py:29` | `MFA_REQUIRED = os.getenv("MFA_REQUIRED", "true")` — 本番はMFA必須 |
| MFA チェック | `backend/app/auth/dependencies.py:122` | `sign_in_second_factor` クレームが必須 — Firebase ID token は1時間で失効 |
| smoke トークン未定義 | `backend/app/auth/dependencies.py:62` | `get_current_user` にサービスアカウント bypass なし |

**判断**: Firebase ID token はCI/CDに使えない（1時間有効期限 + MFA）。`SMOKE_SERVICE_TOKEN` env var による bypass を実装する。

## C. deploy.yml .env 更新ブロック

| 項目 | file:line | 内容 |
|------|-----------|------|
| .env 更新ブロック | `.github/workflows/deploy.yml:160` | `touch .env → sed 削除 → cat >> .env` パターン |
| 末尾への追記箇所 | `.github/workflows/deploy.yml:184` | heredoc でシークレット値を `.env` に追記 |
| sed 削除リスト | `.github/workflows/deploy.yml:161` | 重複追記を防ぐため append 前に既存行を削除 |
