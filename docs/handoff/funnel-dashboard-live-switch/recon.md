# recon: VITE_FUNNEL_DASHBOARD live 切替前チェック

調査日時: 2026-06-16  
目的: ファネルダッシュボードを live モードに切り替える前の変更範囲・リスク特定

---

## 1. VITE_FUNNEL_DASHBOARD の読み取り箇所

### フラグ評価（ビルド時埋め込み）

| ファイル | 行番号 | 内容 |
|---|---|---|
| `frontend/src/api/funnel.ts` | 22 | `import.meta.env.VITE_FUNNEL_DASHBOARD` を評価して `FUNNEL_MODE` を決定 |
| `frontend/src/api/funnel.ts` | 20–24 | `v === "mock"` / `v === "live"` → それ以外は `"off"` |

```ts
// frontend/src/api/funnel.ts:20-24
export const FUNNEL_MODE: FunnelMode = (() => {
  const v = import.meta.env.VITE_FUNNEL_DASHBOARD;
  if (v === "mock" || v === "live") return v;
  return "off";
})();
```

**Vite はビルド時に埋め込む**（ランタイム変更不可）。再ビルド＋デプロイが必須。

---

## 2. FunnelSection が DashboardPage に出る条件

| ファイル | 行番号 | 条件 |
|---|---|---|
| `frontend/src/pages/dashboard/DashboardPage.tsx` | 36–37 | `FunnelSection` と `FUNNEL_MODE` を import |
| `frontend/src/pages/dashboard/DashboardPage.tsx` | 433 | `FUNNEL_MODE !== "off"` → ヘッダーに月セレクタ＋ビュー切替タブが表示 |
| `frontend/src/pages/dashboard/DashboardPage.tsx` | 485–487 | `FUNNEL_MODE !== "off"` → `<FunnelSection month={...} viewMode={...} />` をレンダリング |

```tsx
// DashboardPage.tsx:485-487
{FUNNEL_MODE !== "off" && (
  <FunnelSection month={funnelMonth} viewMode={viewMode} />
)}
```

**現在の本番**: `FUNNEL_MODE = "off"` → FunnelSection は一切レンダリングされない。

---

## 3. 本番環境変数の設定場所と伝播経路

### 現在の伝播経路（既存3変数）

```
GitHub Secrets (VITE_FIREBASE_API_KEY 等)
    ↓（deploy.yml Step 2: sed 削除 → append）
VPS /home/ubuntu/salesanchor/.env
    ↓（docker compose build --build-arg）
docker-compose.yml:147-149 build.args
    ↓
frontend/Dockerfile:7-12 ARG/ENV
    ↓
npm run build（Vite がビルド時に埋め込み）
    ↓
dist/assets/*.js に値が焼き込まれる
```

### 現在の frontend build-args

`docker-compose.yml:144-149`:
```yaml
frontend:
  build:
    context: ./frontend
    args:
      VITE_FIREBASE_API_KEY: ${VITE_FIREBASE_API_KEY}
      VITE_FIREBASE_AUTH_DOMAIN: ${VITE_FIREBASE_AUTH_DOMAIN}
      VITE_GCP_PROJECT_ID: ${VITE_GCP_PROJECT_ID}
```

`frontend/Dockerfile:7-12`:
```dockerfile
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_GCP_PROJECT_ID
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_GCP_PROJECT_ID=$VITE_GCP_PROJECT_ID
```

**`VITE_FUNNEL_DASHBOARD` は上記3ファイルすべてに存在しない。**

---

## 4. 現在の本番値

| 確認箇所 | 値 |
|---|---|
| GitHub Secrets | **存在しない**（`gh secret list` で確認済み） |
| GitHub Actions Variables | **存在しない**（`gh api actions/variables` で確認済み） |
| `frontend/Dockerfile` ARG | **定義なし** |
| `docker-compose.yml` build.args | **定義なし** |
| `deploy.yml` Step 2 inject | **inject なし** |
| 結果（`FUNNEL_MODE`） | **`"off"`** → FunnelSection 非表示 |

---

## 5. live 切替に必要な変更方法

### 変更ファイル一覧（3ファイル）

| ファイル | 変更内容 | 危険度 |
|---|---|---|
| `frontend/Dockerfile` | `ARG VITE_FUNNEL_DASHBOARD` + `ENV` 追加 | 低（既存パターンと同一） |
| `docker-compose.yml` | `VITE_FUNNEL_DASHBOARD: ${VITE_FUNNEL_DASHBOARD}` を build.args に追加 | 低 |
| `.github/workflows/deploy.yml` | Step 2 の sed 削除 + append に `VITE_FUNNEL_DASHBOARD` を追加 | **⚠️ 要PO確認（CLAUDE.md: deploy.yml変更は不可逆操作リスト）** |

### Step 2 deploy.yml への追加差分（参考）

```diff
# sed -i.bak の行に追加:
+  -e '/^VITE_FUNNEL_DASHBOARD=/d' \

# heredoc の末尾に追加:
+VITE_FUNNEL_DASHBOARD=${{ secrets.VITE_FUNNEL_DASHBOARD }}
```

### 必要な外部操作（Shingo が実施）

| 操作 | 方法 | タイミング |
|---|---|---|
| GitHub Secret 追加 | `gh secret set VITE_FUNNEL_DASHBOARD` で値を `live` に設定 | PR マージ前 |
| PR マージ | main への merge trigger → deploy.yml → docker build → live 本番反映 | Shingo GO 後 |

### 切替の方法サマリ

- **PRで完結**: `Dockerfile` + `docker-compose.yml` + `deploy.yml` の3ファイル変更を1PRに含める
- **外部操作も必要**: GitHub Secret `VITE_FUNNEL_DASHBOARD=live` を Shingo が設定
- **再ビルド必須**: 切替は deploy → `docker compose build` → `docker compose up frontend` で完了

---

## 6. live 切替で変更される画面範囲

### 追加表示（OFF → LIVE）

1. **ダッシュボードヘッダー**: 月セレクタ（`<select>`）＋「管理視点」「プレイヤー視点」タブ追加
2. **コンテンツ最上部**: FunnelSection（8カード）
   - リード流入カード（目標/実績/達成率バー）
   - 商談転換率カード
   - 商談金額カード
   - 成約カード
   - 売上サマリ（大カード）
   - 新規顧客獲得カード
   - アクティブ既存顧客カード
   - フォローアップカード（order_stopped / no_repeat / won_no_order）

### 既存ダッシュボード表示への影響

| 既存要素 | 影響 |
|---|---|
| 期間セレクタ（1w/1m/3m/6m/12m） | **変更なし**（ヘッダー右に共存） |
| フォローアップリマインド（既存） | **変更なし**（FunnelSection の後に続く） |
| その他既存エリア | **変更なし** |

---

## 7. エラー・空データ時の挙動確認

| ケース | 挙動 |
|---|---|
| API エラー | `fn-error` クラスの `<div>` で `common.errorLoad` を表示（白落ちなし） |
| ローディング中 | `fn-loading` クラスの `<div>` で `common.loading` 表示 |
| `items: []`（follow-ups 空） | `FollowUpsSummaryCard` が `total=0, orderStopped=0, ...` を表示（クラッシュなし） |
| 目標値ゼロ | `achievementRate(0, 0) = 0`（`target===0` ガード付き） → 0% 表示（クラッシュなし） |

根拠: `frontend/src/pages/dashboard/FunnelSection.tsx:282-295`（error/loading分岐）、`frontend/src/pages/dashboard/FunnelSection.tsx:45-49`（achievementRate ゼロ除算ガード）

---

## 8. 切替前に必要な smoke 項目

| # | 確認項目 | 確認方法 | 期待結果 |
|---|---|---|---|
| S1 | ログイン後ダッシュボード表示 | 本番ブラウザで `https://app.salesanchor.jp/` にアクセス | 既存表示が壊れていない |
| S2 | GET /analytics/funnel 200 | `curl` + SMOKE_SERVICE_TOKEN | `{"month":..., "leads":...}` |
| S3 | GET /analytics/revenue-summary 200 | `curl` + SMOKE_SERVICE_TOKEN | `{"revenue":...}` |
| S4 | GET /analytics/follow-ups 200 | `curl` + SMOKE_SERVICE_TOKEN | `{"items":[]}` ← 確認済み ✅ |
| S5 | GET /analytics/channels 200 | `curl` + SMOKE_SERVICE_TOKEN | `{"items":...}` |
| S6 | GET /analytics/reasons 200 | `curl` + SMOKE_SERVICE_TOKEN | `{"won":[], "lost":[]}` |
| S7 | FunnelSection 表示（white 落ちなし） | live切替後ブラウザ確認 | 8カード表示 or エラー表示（クラッシュなし） |
| S8 | 目標ゼロでも崩れない | 本番データで目標未設定月を確認 | 0% 表示、レイアウト正常 |
| S9 | follow-ups 空配列でも崩れない | items=[] 状態で確認 | `0件` 表示、クラッシュなし |

---

## 9. 危険変更の有無

| 項目 | 有無 | 備考 |
|---|---|---|
| DB migration | **なし** | |
| deploy.yml 変更 | **あり** ⚠️ | CLAUDE.md: 不可逆操作リスト。PO確認必須 |
| 本番データ書き換え | **なし** | |
| 既存機能削除/変更 | **なし** | FunnelSection 追加のみ |
| 既存 VITE_ vars への影響 | **なし** | Firebase/GCP vars は手を触れない |

---

## 10. Shingo GO が必要な箇所

| GO ポイント | 理由 |
|---|---|
| **deploy.yml 変更を含む PR の main マージ** | CLAUDE.md 不可逆操作リスト（`workflow-lint.yml` 変更禁止条項も準拠） |
| **GitHub Secret `VITE_FUNNEL_DASHBOARD=live` の設定** | Secret は Claude が設定不可（Shingo 実施） |
| **live 切替 PR の main マージ** | 本番ユーザーへの画面変更 |

---

## 11. 調査ベース

| ファイル | 調査内容 |
|---|---|
| `frontend/src/api/funnel.ts:20-24` | `FUNNEL_MODE` 評価ロジック |
| `frontend/src/pages/dashboard/DashboardPage.tsx:36-37,433,485-487` | FunnelSection 表示条件 |
| `frontend/src/pages/dashboard/FunnelSection.tsx:282-295,330-395` | エラー・空データ時挙動 |
| `frontend/Dockerfile:7-12` | 現在の ARG/ENV（3変数のみ） |
| `docker-compose.yml:144-149` | 現在の frontend build args |
| `.github/workflows/deploy.yml:200-262` | Step 2 secrets inject パターン |
| `gh secret list` | VITE_FUNNEL_DASHBOARD 不在確認 |
| `gh api actions/variables` | GitHub Variables 不在確認 |
