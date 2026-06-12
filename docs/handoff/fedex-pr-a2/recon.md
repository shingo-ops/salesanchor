# recon: FedEx PR-A2（APIキーマスク修正 + CSS標準合わせ）

## 既存 ADR 検索

- `docs/adr/ADR-125-fedex-rates-stage1.md` — FedEx credentials hint フィールド仕様定義元
- `docs/adr/ADR-129-fedex-label-validation-wizard.md` — FedEx 環境セレクタ追加
- `docs/adr/ADR-067-design-token-enforcement.md` — デザイントークン強制ルール

## ① APIキーマスク不具合

### 根拠箇所

- `backend/app/services/carrier_credentials.py:108` — `"client_id_hint": client_id` → rawフル値を返していた
- `backend/app/services/carrier_credentials.py:76` — docstring「client_id 全体（秘密度低）」→ 仕様と不一致

### フロント側

- `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:357` — `data.status?.client_id_hint` をそのまま表示
- フロント側の変更不要（バックエンドで正しい hint を返せばよい）

### 修正内容

`backend/app/services/carrier_credentials.py:108`:
```python
# 修正前
"client_id_hint": client_id,
# 修正後
"client_id_hint": f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) >= 8 else client_id,
```

## ② CSS 標準合わせ

### develop ブランチの最新 TSX（PR-A 適用済み）

`frontend/src/pages/integrations/CarrierIntegrationPage.tsx` で使われているクラス一覧:

| クラス | 定義状況 |
|---|---|
| `card` | `frontend/src/components.css:346` ✅ |
| `btn-primary`, `btn-secondary`, `btn-ghost` | `frontend/src/components.css:54` ✅ |
| `form-group`, `form-actions`, `error-message` | `frontend/src/components.css:7` ✅ |
| `carrier-env-card__*` (BEM 子要素) | `frontend/src/pages-layout.css:608` ✅ |
| `carrier-env-card` (ベース) | **未定義** ❌ |
| `carrier-env-card--empty` (modifier) | **未定義** ❌ |
| `carrier-env-card--editing` (modifier) | **未定義** ❌ |
| `carrier-page-tabs` | **未定義** ❌ |
| `update-form` | **未定義** ❌ |

### 標準トークン使用根拠

- `var(--space-4)` — `frontend/src/tokens.css:72`（16px グリッド準拠）
- `var(--bg-subtle)` — `frontend/src/index.css:11`（#f7fafc / dark: #243046）
- `var(--accent)` — `frontend/src/index.css:27` アクセントカラー
- ADR-067: 色トークンは `:root` と `:root.force-dark` 両方定義済み
