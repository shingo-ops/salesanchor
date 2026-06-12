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

関連 ADR: ADR-125（FedEx Rates Stage1 — client_id_hint フィールド仕様定義元）

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

## 外部・過去事例の参照と我々への応用

- **Stripe API キー**: `sk_live_xxxx...yyyy` 形式（先頭プレフィックス+末尾4桁）— SaaS CRM での認証情報表示の業界標準。我々も同方針で先頭4桁+末尾4桁を採用。
- **FedEx Developer Portal**: Client ID をポータル画面では全文表示するが、マルチテナント CRM でテナント間の認証情報漏洩リスクを下げるため hint 形式に制限（ADR-125 の hint 設計根拠）。
- **account_number_hint 実績**: 同ファイル内で `******{suffix[-3:]}` 方式が既に稼働中 — 統一ルールとして先頭4+末尾4方式を client_id にも適用。

## スコープ外

- アプリ全体の配色変更
- `form-hint`, `success-message` のグローバルスタイル定義（別PR で統一すべき）
