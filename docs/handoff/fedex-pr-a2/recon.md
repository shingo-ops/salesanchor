# recon: FedEx PR-A2（APIキーマスク修正 + CSS標準合わせ）

## 既存 ADR 検索

- `docs/adr/ADR-125` — FedEx/UPS Account Number追加、Hint表示仕様
- `docs/adr/ADR-129` — FedEx 環境セレクタ追加（本番/Sandbox 分離）
- `docs/adr/ADR-067` — デザイントークン強制ルール（color token必須）

## ① APIキーマスク不具合

### 根拠箇所

- `backend/app/services/carrier_credentials.py:108` — `"client_id_hint": client_id` → rawフル値を返していた
- `backend/app/services/carrier_credentials.py:76` — docstring「client_id 全体（秘密度低）」→ 仕様と不一致

### フロント側

- `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:357-358` — `data.status?.client_id_hint` をそのまま表示
- フロント側の変更不要（バックエンドで正しい hint を返せばよい）

### 修正内容

`carrier_credentials.py:108`:
```python
# 修正前
"client_id_hint": client_id,
# 修正後
"client_id_hint": f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) >= 8 else client_id,
```

## ② CSS 標準合わせ

### develop ブランチの最新 TSX（PR-A 適用済み）

`CarrierIntegrationPage.tsx` で使われているクラス一覧:

| クラス | 定義状況 |
|---|---|
| `card` | `components.css:346` ✅ |
| `btn-primary`, `btn-secondary`, `btn-ghost` | `components.css:54,68,81` ✅ |
| `form-group`, `form-actions`, `error-message` | `components.css` ✅ |
| `carrier-env-card__*` (BEM 子要素) | `pages-layout.css:606〜` ✅ |
| `carrier-env-card` (ベース) | **未定義** ❌ |
| `carrier-env-card--empty` (modifier) | **未定義** ❌ |
| `carrier-env-card--editing` (modifier) | **未定義** ❌ |
| `carrier-page-tabs` | **未定義** ❌ |
| `update-form` | **未定義** ❌ |

### 標準トークン使用根拠

- `var(--space-4)` — `tokens.css:72`（16px グリッド準拠）
- `var(--bg-subtle)` — `index.css:11`（#f7fafc / dark: #243046）
- `var(--accent)` — `index.css` アクセントカラー
- ADR-067: 色トークンは `:root` と `:root.force-dark` 両方定義済み
