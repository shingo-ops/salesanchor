# design: FedEx PR-A2（APIキーマスク修正 + CSS標準合わせ）

## 変更概要

| 変更 | ファイル | 種別 |
|---|---|---|
| ① client_id_hint をマスク形式に変更 | `backend/app/services/carrier_credentials.py:108` | バグ修正 |
| ② 未定義 CSS クラスに標準トークンスタイルを追加 | `frontend/src/pages-layout.css` | スタイル追加 |

## ① APIキーマスク

| 基準 | 検証方法 |
|---|---|
| API レスポンスの `client_id_hint` が `l79e...ec3d` 形式であること | `GET /integrations/carriers/fedex/status` のレスポンスを確認 |
| フル値が露出しないこと | 8文字未満の client_id はそのまま返す（短縮不能を防ぐ） |

**外部事例**: FedEx Developer Portal 自身は Client ID をポータル画面で全文表示するが、SaaS CRM で他者テナントの認証情報を保護する場合は hint 形式が標準（Stripe API キー `sk_live_...` と同方針）。

## ② CSS 標準合わせ

追加スタイルの根拠:

| クラス | スタイル | トークン根拠 |
|---|---|---|
| `.carrier-page-tabs` | `margin-bottom: var(--space-4)` | 16px グリッド（tokens.css） |
| `.update-form` | `margin-bottom: var(--space-3)` | 12px グリッド（tokens.css） |
| `.carrier-env-card` | `margin-bottom: var(--space-4)` | カード間隔 |
| `.carrier-env-card--empty` | `background: var(--bg-subtle)` | 空状態の視覚区別（index.css） |
| `.carrier-env-card--editing` | `border-color: var(--accent)` | 編集中フォーカス表示 |

**独自 CSS なし**: 既存の `.card` の border/radius/shadow はそのまま継承。インラインスタイル・ハードコードカラーなし。

## 弊害・リスク

- `carrier-env-card--editing` の `border-color: var(--accent)` は `.card` の既存 border を上書き（詳細度同等・後方宣言で勝つ）。問題なし。
- `carrier-env-card--empty` の `background: var(--bg-subtle)` はダークモード対応済み（`:root.force-dark` で `--bg-subtle: #243046`）。

## スコープ外

- アプリ全体の配色変更
- `form-hint`, `success-message` のグローバルスタイル定義（別PR で統一すべき）
