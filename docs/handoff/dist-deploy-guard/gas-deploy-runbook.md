# GAS 配信 Web アプリ 運用手順書

## 対象プロジェクト

- **コードの正本**: 本番 版12 のソースは、`clasp clone` で取得できるリモートのものが正（2026-10-05 時点）。作業フォルダは `~/tcg-inventory-viewer-prod-1hc/`（`Code.js` / `index.html` / `appsscript.json`）
- **ローカルリポジトリ（旧）**: `~/tcg-client-viewer/`（`shingo-ops/tcg-client-viewer`。下記「コードの正本について」参照）
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

### 更新時: テスト用 GAS で確認してから本番へ（2026-10-05 更新）

順番は「テスト用 GAS で push → create-version → redeploy → 画面確認 → 本番で同じ手順」。
clasp 3.1.3 のコマンド名は `create-version` と `redeploy <deploymentId> -V <版>`（旧手順の `deploy --deploymentId` ではない）。
GAS への push は、PO の `bash scripts/permit-danger.sh` による clasp push 用チケットが毎回必要。

```bash
# 1. 作業フォルダでコードを修正（本番 版12 のソースを clasp clone した場所）
cd ~/tcg-inventory-viewer-prod-1hc
vi Code.js   # または index.html

# 2. テスト用 GAS（scriptId は「配信テスト用 GAS」節）へ push（permit 必要）
npx @google/clasp push --force

# 3. 新しい版を作る（出力された版番号を控える）
npx @google/clasp create-version "変更内容の説明 (YYYY-MM-DD)"

# 4. テスト用デプロイにその版を当てる（URL は変わらない）
npx @google/clasp redeploy <テスト用デプロイID> -V <版番号>

# 5. テスト用 URL で PC・スマホの画面確認
# 6. 問題なければ、本番 GAS の .clasp.json に向けて 2〜4 を同じ手順で実施
#    redeploy 先は本番デプロイ ID: AKfycbyS_kIojvLdi0rmGnttKCWLbS64gvKvI7qfjQOFx76vqRYjUjpPBeR78HOeqgqc_ZWHfw
```

戻し方: 直前の版へ `npx @google/clasp redeploy <デプロイID> -V <前の版>`（例: 本番 12 → 11）。

GAS UI でも同じ操作が可能:
```
スクリプトエディタ → デプロイ → デプロイを管理 → 鉛筆アイコン
→ バージョン: 「新しいバージョン」を選択 → デプロイ
```

**「新しいデプロイ」を選ぶと URL が変わるため絶対に使わないこと。**

## 配信テスト用 GAS

本番に当てる前の確認用。本番と同じコードを先に当てて画面確認する。

- **スクリプト ID**: `1Tb-84Fj39_DBbsJ4b4yywJ6xltBegk4-0VaFSpOAFHbG5avhJ5mEuvfq`
- **バインド先シート**: `1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4`
- **テスト用デプロイ**: `AKfycbxnnFRl5MMsbyWgf3Lc1iV625Xjb9LvVHgODbT5b_tcdW6_K9-iPxeQhFIz4XsB5WnCVQ`（2026-10-05 に 版13 → 版14 へ切り替え）
- **HEAD デプロイ**: `AKfycbwW59I_vFH9fztUvb8AeFIyDrpSkLczhNr2UCuLFptw`（削除不可）

## コードの正本について（2026-10-05 時点）

- 本番 版12「Seriesタブ追加・スマホで提供者表示」のソースは、`clasp clone` で取得できるリモートのものが正。作業フォルダは `~/tcg-inventory-viewer-prod-1hc/`。
- ローカルの `~/tcg-client-viewer/src` は本番より古い（`index.html` は 586 行、本番は 1377 行）。そのまま push すると本番の機能が消えるので使わないこと。
- `shingo-ops/tcg-client-viewer` は、2026-10-05 時点で shingo-cc から見えない（`Repository not found`）。
- リポジトリへの同期は、PO がアクセス権を確認するまで保留とする。

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

## 現在のデプロイ一覧（2026-10-05 時点）

### 本番 GAS（scriptId `1hc-Wn3g…`）

| デプロイ ID（先頭12文字） | バージョン | 用途 |
|---|---|---|
| `AKfycbxu-x-P7` | @HEAD | 開発用・常設（削除不可） |
| `AKfycbyS_kIoj` | @12 | **本番 URL**（クライアントに共有。2026-10-05 PO 確認済み）。2026-10-05 に @11 から切り替え |
| `AKfycbxg9SChn` | @3 | 不要（アーカイブ候補） |

### 配信テスト用 GAS（scriptId `1Tb-84Fj…`）

| デプロイ ID（先頭12文字） | バージョン | 用途 |
|---|---|---|
| `AKfycbwW59I_v` | @HEAD | 常設（削除不可） |
| `AKfycbxnnFRl5` | @14 | テスト用 URL。2026-10-05 に @13 から切り替え |

旧記載（2026-09-04 時点）: 本番 `AKfycbyS_kIoj` は @5（最新）。
