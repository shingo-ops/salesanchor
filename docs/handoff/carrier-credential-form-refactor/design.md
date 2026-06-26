# design: CarrierCredentialForm 切り出し（第1段）

## 参照

- recon: `docs/handoff/carrier-credential-form-refactor/recon.md`
- ADR-027: `docs/adr/ADR-027-ui-internationalization.md`（i18n 強制）
- ADR-067: `docs/adr/ADR-067-design-token-enforcement.md`（CSS 変数強制）

---

## KGI

「第1段完了」= CarrierIntegrationPage の鍵登録フォームを `CarrierCredentialForm` コンポーネントに切り出した後、**既存ページ（本番 / Sandbox カードの鍵登録フォーム）の挙動が1ミリも変わらない**こと。

| 基準 | 検証方法 |
|---|---|
| フォームの UI・挙動が変わらない | 手動: `/management-center/integrations/fedex` で鍵登録→接続テスト→バッジ更新 |
| lint / TS エラーがない | `cd frontend && npm run lint && npx tsc --noEmit` |
| キャリア全種（fedex/dhl/ups）で動作する | 手動: 各ページで編集モード展開 |
| フロントから tenant_id を送信しない | recon 引継ぎ: API 呼出コードに `tenant_id` を含めない |
| i18n ハードコードなし | `npm run lint` が 0 warnings |

---

## 外部・過去事例の参照と我々への応用

過去 PR での同種のフォーム部品化（`ConfirmModal` の切り出し）と同じパターンを踏襲:
- 親はコンポーネントの内部 state を一切知らない
- 成功・キャンセルだけをコールバックで受け取る
- API 呼出はコンポーネント内部で完結

---

## 設計案

### 新規ファイル

```
frontend/src/pages/integrations/CarrierCredentialForm.tsx   （新規）
frontend/src/pages/integrations/CarrierCredentialForm.css   （新規）
```

コンポーネントは `pages/integrations/` に colocate する（第2段で `components/integrations/` へ昇格予定）。

---

### 移動する定数（CarrierIntegrationPage.tsx から export へ変更）

```typescript
// CarrierIntegrationPage.tsx の先頭付近を export に変更
export const CRED_LABEL: Record<Carrier, { id: string; secret: string }> = { ... }
export const SHOWS_ACCOUNT_NUMBER: ReadonlySet<Carrier> = new Set(["fedex", "ups"])
export const SUPPORTS_ENV_SELECT: ReadonlySet<Carrier> = new Set(["fedex"])
```

`CarrierCredentialForm.tsx` はこれらを import して参照する。型 `Carrier` / `Env` も export に変更する。

---

### Props 設計

```typescript
// CarrierCredentialForm.tsx

interface CarrierCredentialFormProps {
  carrier: Carrier;       // "fedex" | "dhl" | "ups"
  env: Env;               // "production" | "sandbox"
  envLabel: string;       // 翻訳済みラベル（例: "本番環境"）。親が t() して渡す
  onSaved: () => Promise<void>;  // 保存+テスト成功後に呼ぶ。親の loadStatus() を渡す
  onCancel: () => void;   // キャンセル時に呼ぶ。親の setEditingEnv(null) を渡す
}
```

**設計根拠:**
- `carrier` / `env` を受け取ることで、コンポーネント内でキャリア固有ロジック（フィールド表示・API URL 組み立て）を完結できる
- `onSaved` は `async` — 親の `loadStatus()` を await することでビューカードの更新タイミングを親が制御できる
- `envLabel` は翻訳済み文字列として受け取る（コンポーネント内でも `useTranslation` するが、タイトル文字列の組み立ては親の関心事のため）

**渡さない props:**
- `tenant_id` → サーバー側で自動セット（`get_current_tenant`）のためフロントから渡さない（IDOR 対策）
- `showAccountNumber` / `supportsEnvSelect` → コンポーネント内で `SHOWS_ACCOUNT_NUMBER.has(carrier)` 等を参照するため不要

---

### コンポーネント内部 state

```typescript
// CarrierCredentialForm.tsx 内部（親に露出しない）
const [clientId, setClientId] = useState("")
const [clientSecret, setClientSecret] = useState("")
const [accountNumber, setAccountNumber] = useState("")
const [busy, setBusy] = useState(false)
const [error, setError] = useState("")
```

**`busy` / `error` の分離について:**
- 親 `CarrierIntegrationPage` の `busy` / `error` はビューカードの「接続テスト」ボタン・削除ハンドラで使用する
- フォームの `busy` / `error` はコンポーネント内部に閉じる
- 2つの `busy` が共存するが、フォームが展開中はビューカードのボタンは非表示のため UI 上の競合はない

---

### API 呼出ロジック（handleSaveAndTest の移動先）

```typescript
// CarrierCredentialForm.tsx 内
const handleSaveAndTest = async () => {
  setBusy(true)
  setError("")
  try {
    await api.put(`/integrations/carriers/${carrier}/credentials`, {
      client_id: clientId,
      client_secret: clientSecret,
      environment: SUPPORTS_ENV_SELECT.has(carrier) ? env : "production",
      ...(SHOWS_ACCOUNT_NUMBER.has(carrier) && accountNumber ? { account_number: accountNumber } : {}),
    })
    const query = SUPPORTS_ENV_SELECT.has(carrier) ? `?environment=${env}` : ""
    await api.post(`/integrations/carriers/${carrier}/test-connection${query}`, {}).catch(() => null)
    await onSaved()   // ← 親の loadStatus() を呼ぶ
  } catch (e) {
    setError(e instanceof Error ? e.message : t("common.operationError"))
  } finally {
    setBusy(false)
  }
}
```

`onSaved()` 内部で親が `setEditingEnv(null)` を呼ぶ（成功時の編集モード解除を親が制御）か、または onSaved を `onSuccess` として「成功後の後処理も含めて行う」ことも選択肢。どちらでも可。

**推奨**: `onSaved` は `loadStatus` だけを渡し、`setEditingEnv(null)` は onSaved の実行完了後に **コンポーネント内で呼ぶ**（`await onSaved(); onCancel()`）。こうすることで「保存成功 → ステータス更新 → フォームを閉じる」の順序がコンポーネント内で明示される。

---

### 親（CarrierIntegrationPage）の変更後スケルトン

```typescript
// 削除する state
- const [formClientId, setFormClientId] = useState("")
- const [formClientSecret, setFormClientSecret] = useState("")
- const [formAccountNumber, setFormAccountNumber] = useState("")

// 削除するハンドラ
- const handleSaveAndTest = async () => { ... }

// openEdit を簡略化（state クリアが不要になる）
const openEdit = (env: Env) => {
  setError("")
  setEditingEnv(env)
}

// renderCard 内の編集フォーム（215-287）を置換
if (isEditing) {
  return (
    <CarrierCredentialForm
      carrier={carrier}
      env={env}
      envLabel={cardTitle}
      onSaved={async () => { await loadStatus(); setEditingEnv(null) }}
      onCancel={() => { setEditingEnv(null); setError("") }}
    />
  )
}
```

---

### CSS の対応

**新規作成**: `CarrierCredentialForm.css`

移動する CSS（フォーム専用クラスのみ）:
- `.carrier-env-card--editing` の border（CarrierIntegrationPage.css:14）
- `.update-form`（CarrierIntegrationPage.css:103）

残す CSS（`CarrierIntegrationPage.css`）:
- ビューカード・未登録カードのすべてのスタイル
- `.carrier-env-card__header` / `__title` / `__hint`（フォームも使うが共用）

`CarrierCredentialForm.tsx` は:
```typescript
import "./CarrierCredentialForm.css"
import "./CarrierIntegrationPage.css"  // 共用クラス参照のため
```

---

## 影響ファイル一覧（想定）

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx` | 修正 | state 3本削除・handleSaveAndTest 削除・openEdit 簡略化・renderCard 内の 215-287 を `<CarrierCredentialForm>` に置換・型/定数を export に変更 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.css` | 修正 | フォーム専用CSS 2件を CarrierCredentialForm.css へ移動 |
| `frontend/src/pages/integrations/CarrierCredentialForm.tsx` | **新規** | 切り出したフォームコンポーネント |
| `frontend/src/pages/integrations/CarrierCredentialForm.css` | **新規** | フォーム専用スタイル |

**触れないファイル**:
- `backend/` — 不変
- `migrations/` — 不変
- `.github/workflows/` — 不変
- `frontend/tests-e2e/` — 挙動変更なし・新規 UI 要素なし（変更不要）
- `frontend/src/locales/` — i18n キー不変（コンポーネント内で同じキーを参照）

---

## テナント分離不変性の明記

このリファクタはフロントの **表示層の再構成のみ** であり、テナント分離には影響しない。

- `tenant_id` はバックエンドで `Depends(get_current_tenant)` により自動セット（`backend/app/auth/dependencies.py:192-239`）
- `PUT /integrations/carriers/{carrier}/credentials` の request body に `tenant_id` を含めない設計は変更しない
- RLS（`FORCE ROW LEVEL SECURITY`）は DB 側で適用済み（`migrations/20260609_090000_add_carrier_credentials_rls.sql:20-33`）
- コンポーネント化後も API 呼出コードに `tenant_id` フィールドを追加しないこと（設計上の禁止事項として明記）

---

## 手動確認観点（第1段完了条件）

1. `/management-center/integrations/fedex` を開く
2. 本番カード「鍵を登録」→ フォーム展開確認
3. APIキー/シークレット/アカウント番号を入力して「保存してテスト」
4. 接続テストバッジ（成功 or 失敗）がカードに表示されること
5. 「キャンセル」でフォームが閉じること
6. Sandbox カードでも同様に確認
7. DHL / UPS ページでも編集モード展開・キャンセルを確認（アカウント番号フィールドの有無の差異）

---

## 第2段との切り離し

第1段は **部品化のみ**。以下は第1段に含めない:
- FedExEtdSetupGuide への `CarrierCredentialForm` の埋め込み
- ガイド用の UI 調整（ボタンラベル変更・レイアウト調整等）
- 新規 i18n キー追加

第1段の PR が「本番反映・既存挙動不変確認済み」になってから第2段に着手する。
