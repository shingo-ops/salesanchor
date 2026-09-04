# GAS 配信 Web アプリ 運用手順書

## 対象プロジェクト

- **ローカルリポジトリ**: `~/tcg-client-viewer/`
- **スクリプト ID**: `1hc-Wn3gKMigD8MSsXFLfKAeybN8MUEAGkPoIoaThfJaOlWilLDb3edKT`
- **バインド先スプレッドシート**: `1jODIuD81RG9itlMrr1-nj4Yrtbc9MqywYliemLvQWC0`（Shingo 所有）
- **本番 URL**: `https://script.google.com/macros/s/AKfycbyS_kIojvLdi0rmGnttKCWLbS64gvKvI7qfjQOFx76vqRYjUjpPBeR78HOeqgqc_ZWHfw/exec`

---

## デプロイ手順

### 初回のみ: 「新しいデプロイ」

新しいクライアント向けに全く新規の Web アプリを立てる場合のみ使う。
**既存の URL を更新する場合は使わない。**

```
スクリプトエディタ → デプロイ → 新しいデプロイ → ウェブアプリ → デプロイ
```

→ 新しいデプロイ ID（= 新しい URL）が払い出される。

### 更新時: 「デプロイを管理」から新バージョン

コードを修正して既存 URL のまま反映する場合:

```bash
# 1. コード修正
cd ~/tcg-client-viewer
vi src/Code.js   # または src/index.html

# 2. GAS へ push（permit 必要）
npx @google/clasp push --force

# 3. 既存デプロイに新バージョンを当てる（URL は変わらない）
npx @google/clasp deploy \
  --deploymentId "AKfycbyS_kIojvLdi0rmGnttKCWLbS64gvKvI7qfjQOFx76vqRYjUjpPBeR78HOeqgqc_ZWHfw" \
  --description "vN 変更内容の説明 (YYYY-MM-DD)"
```

GAS UI でも同じ操作が可能:
```
スクリプトエディタ → デプロイ → デプロイを管理 → 鉛筆アイコン
→ バージョン: 「新しいバージョン」を選択 → デプロイ
```

**「新しいデプロイ」を選ぶと URL が変わるため絶対に使わないこと。**

---

## デプロイが増えてしまった場合

「新しいデプロイ」を誤って複数回押すと、デプロイ ID（= URL）が増える。

### 確認

```bash
cd ~/tcg-client-viewer
npx @google/clasp deployments
```

### 不要デプロイをアーカイブ（削除）

```bash
npx @google/clasp undeploy --deploymentId "<不要なID>"
```

注意:
- `@HEAD` のデプロイ ID は削除不可（常設）
- 本番 URL のデプロイ ID（`AKfycbyS_...`）は削除しないこと

---

## シート所有権ポリシー

### 公式ドキュメントで確定した事実

出典: https://developers.google.com/apps-script/guides/bound  
出典: https://developers.google.com/apps-script/guides/collaborating

| 事実 | 内容 |
|---|---|
| コンテナ所有者 = スクリプト所有者 | スプレッドシートの所有者がスクリプトプロジェクトの所有者になる（作成者に関わらず） |
| アクセスリスト継承 | 編集権限を持つ人はスクリプトを実行でき、閲覧者はコードを見られる |
| clasp の制約 | バインドスクリプトを新規作成できない（clone と edit のみ） |

### 方針（2026-09-04 PO 確定）

**配信先スプレッドシートは Shingo が所有し、クライアントには渡さない。**

- Web アプリは認証なし（ANYONE_ANONYMOUS）のため、URL を渡すだけで閲覧可能
- スプレッドシート自体をクライアントと共有する必要はない
- クライアントへはアプリ URL のみ提供する

これにより:
- スクリプトの所有権が Shingo に固定される
- クライアントがコード（`Code.js` / `index.html`）を閲覧できない
- デプロイ権限が Shingo に集中し、意図しない変更を防止できる

---

## 現在のデプロイ一覧（2026-09-04 時点）

| デプロイ ID（先頭12文字） | バージョン | 用途 |
|---|---|---|
| `AKfycbxu-x-P7` | @HEAD | 開発用・常設（削除不可） |
| `AKfycbyS_kIoj` | @5（最新） | **本番 URL**（クライアントに共有） |
| `AKfycbxg9SChn` | @3 | 不要（アーカイブ候補） |
