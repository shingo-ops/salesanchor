# recon: CarrierCredentialForm 切り出し（第1段）

## 対象ファイル

- `frontend/src/pages/integrations/CarrierIntegrationPage.tsx`（429行）
- `frontend/src/pages/integrations/CarrierIntegrationPage.css`（127行）

---

## 現状の state 一覧と使用箇所

| state | 宣言行 | フォーム内 | フォーム外（ビューカード等） |
|---|---|---|---|
| `editingEnv` | :83 | :208（判定のみ） | :303 :374（openEdit 呼出） |
| `formClientId` | :84 | :230 :281 :128 | なし |
| `formClientSecret` | :85 | :241 :280 :281 :129 | なし |
| `formAccountNumber` | :86 | :255 :131 | なし |
| `busy` | :88 | :270 :280 :283 | :303 :369 :374 :379（ビューカードのボタン） |
| `error` | :89 | :266（フォーム内表示） | :426（グローバル表示 `!editingEnv` 時） |

**結論**:
- `formClientId/Secret/AccountNumber` → フォーム内だけで使用。新コンポーネントへ移動可能
- `busy` / `error` → ビューカード側でも使用（`handleTest`, `handleDeleteConfirmed`）。フォームとビューカードで **別々のローカル state** に分離する

---

## ハンドラ一覧と依存関係

| ハンドラ | 行 | フォームとの関係 |
|---|---|---|
| `openEdit(env)` | :114 | フォーム state をクリアして editingEnv をセット |
| `handleSaveAndTest()` | :122 | フォームの値を読んで PUT + test-connection + loadStatus |
| `handleTest(env)` | :147 | ビューカードの「接続テスト」ボタン。フォーム state 不使用 |
| `handleDeleteConfirmed()` | :165 | delete API。フォーム state 不使用 |

**結論**:
- `handleSaveAndTest` → フォーム専用。新コンポーネント内に移動
- `openEdit` → フォーム state のクリアが不要になるため、`setEditingEnv(env)` 呼出のみに簡略化
- `handleTest` / `handleDeleteConfirmed` → 親に残す

---

## フォーム UI の JSX 範囲

`renderCard()` 内、`if (isEditing)` ブロック:

- `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:215-287`（`<section>` タグ全体）

フォーム内で参照している親スコープの変数:
- `env`（引数として渡される）
- `cardTitle`（`t(...)` で生成・env ラベル）
- `carrier`（外側 props）
- `labels`（`CRED_LABEL[carrier]`）
- `SHOWS_ACCOUNT_NUMBER.has(carrier)` → `showAccountNumber` として渡す

---

## キャリア固有定数の所在

| 定数 | 行 | 使用目的 |
|---|---|---|
| `CRED_LABEL` | :38 | フィールドラベルの i18n キー（キャリアごとに差異） |
| `SHOWS_ACCOUNT_NUMBER` | :70 | アカウント番号フィールドの表示有無（fedex/ups） |
| `SUPPORTS_ENV_SELECT` | :73 | 環境セレクタ対応有無（fedex のみ） |

3定数は現在 `frontend/src/pages/integrations/CarrierIntegrationPage.tsx` 内の非エクスポート定数。新コンポーネントが参照するには export が必要。

---

## CSS の使用箇所マッピング

フォーム内（215-287）が使用する CSS クラス:

| クラス | CSS 行 | フォーム専用か |
|---|---|---|
| `.carrier-env-card` | :8 | **共用**（ビューカードも使用） |
| `.carrier-env-card--editing` | :14 | **フォーム専用**（border 変更のみ） |
| `.carrier-env-card__header` | :24 | **共用** |
| `.carrier-env-card__title` | :29 | **共用** |
| `.carrier-env-card__hint` | :36 | **共用** |
| `.update-form` | :103 | **フォーム専用** |
| `.form-group` | global | **共用** |
| `.error-message` | global | **共用** |
| `.form-actions` | global | **共用** |

→ フォーム専用は `.carrier-env-card--editing` と `.update-form` のみ。他はページ全体と共用。

---

## 既存 E2E テストの有無

`frontend/tests-e2e/` に carrier integration 専用 spec なし（`grep` で未検出）。手動確認が主な検証手段。

---

## バックエンド・migration・CI 影響

- `backend/` → 触れない（API エンドポイント不変）
- `migrations/` → 触れない（DB スキーマ不変）
- `.github/workflows/` → 触れない
- `frontend/tests-e2e/` → 新規 UI 要素なし・既存挙動のみ → spec 変更不要
