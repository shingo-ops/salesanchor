# Runbook: Discord Botロール順の設定

> **対象**: Sales Anchor 管理者（Discordサーバーの管理権限を持つ方）  
> **所要時間**: 約5分  
> **関連**: `docs/runbooks/discord-gateway-operations.md` / ADR-091

---

## なぜこの設定が必要か

Discord には**ロール階層**というルールがあります。

> **Botは、自分の最上位ロールより下位にあるロールだけ付与・編集できます。**

そのため、Sales Anchor Bot ロールは、Sales Anchor が自動付与する **Partner / Member** より上に配置する必要があります。

Sales Anchor Bot は顧客のご注文規模に応じて **Partner**（大口）/ **Member**（小口）ロールを自動で付与します。  
Bot ロールがこれらのロールより下に位置していると、Bot がロールを付与しようとしても Discord に拒否されてしまいます。

### 正しいロール順（上が強い）

```
Owner / Admin（サーバー管理者）
Sales Anchor Bot      ← ここに置く（↑ より下・↓ より上）
Sales Anchor Staff
Partner
Member
@everyone
```

---

## 手順

### Step 1: Discordでサーバー設定を開く

1. Discord を開き、Sales Anchor Bot を招待したサーバーをクリックする
2. サーバー名の右にある **▼（下向き矢印）** をクリックする
3. メニューから **「サーバーの設定」** を選ぶ

<!-- スクショ挿入位置 -->
<!-- 実画像配置後に以下のコメントを外す: -->
<!-- ![サーバー設定を開く](images/discord-role-order-01-server-settings.png) -->

> **画像未配置の場合**: サーバー名を右クリックしても同じメニューが表示されます。

---

### Step 2: ロール画面を開く

1. 左サイドバーの **「ロール」** をクリックする

<!-- スクショ挿入位置 -->
<!-- ![ロール画面](images/discord-role-order-02-roles-menu.png) -->

---

### Step 3: Sales Anchor Bot ロールを探す

ロール一覧の中から **「Sales Anchor Bot」** というロールを見つける。

<!-- スクショ挿入位置 -->
<!-- ![Sales Anchor Bot ロールを探す](images/discord-role-order-03-find-bot-role.png) -->

> **見当たらない場合**: Bot を招待した際に Discord が自動作成します。まだ Bot を招待していない場合は先に招待してください。

---

### Step 4: Sales Anchor Bot ロールを上に移動する

1. **「Sales Anchor Bot」** ロールの左端にある **⠿（6点グリップ）** をつかむ
2. **「Partner」** ロールより上の位置にドラッグして離す

**移動後のイメージ（ロール一覧上での並び）:**

```
Sales Anchor Bot    ← ここ
Partner
Member
@everyone
```

<!-- スクショ挿入位置 -->
<!-- ![ロールをドラッグする](images/discord-role-order-04-drag-bot-role.png) -->

---

### Step 5: 変更を保存する

画面下部に **「変更を保存」** ボタンが表示されたらクリックする。

<!-- スクショ挿入位置 -->
<!-- ![変更を保存する](images/discord-role-order-05-save-changes.png) -->

> **保存しないと反映されません**。画面を閉じる前に必ず保存してください。

---

### Step 6: Sales Anchor 側で確認する

1. Sales Anchor にログインし、**設定 → Discord 連携設定** (`/admin/discord-config`) を開く
2. テスト用の顧客リードの **estimated_scale（顧客規模）** を「Small」または「Large」に変更して保存する
3. 顧客の Discord アカウントに **Partner** または **Member** ロールが付与されたことを Discord で確認する

ロール付与に成功すると、リード一覧の Discord 欄に **「同期済み」** と表示されます。

---

## トラブルシュート

| 症状 | 原因 | 対処 |
|------|------|------|
| ロール付与が「同期失敗」になる | Bot ロールがまだ Member より下にある | 本ガイドの Step 3〜5 を再実施 |
| 「Sales Anchor Bot」ロールが見当たらない | Bot 未招待 / Bot がサーバーから退出している | Bot をサーバーに再招待する |
| ロールをドラッグできない | Discordサーバーの管理権限がない | サーバーオーナー / 管理者に依頼する |
| 保存ボタンが出ない | 変更が検出されていない | ロール順をもう一度並べ替えてみる |

---

## 自動セットアップ導線からの参照

将来 `discord-setup/bootstrap` 完了画面を実装する際は、以下の文言と本ガイドへのリンクをステップとして追加する:

```
✅ Bot 招待完了
✅ Guild ID 登録完了
⚠️ Bot ロールを Partner / Member より上に移動してください
   → 手順書: docs/runbooks/discord-role-order-guide.md
```

---

---

## Bot 権限チェックリスト

Developer Portal の Bot Permissions および Discord サーバーの "Sales Anchor" ロールに付与すべき権限の一覧。
権限の意図は `docs/adr/ADR-091-discord-bot-scope-definition.md` の「Bot 権限定義」セクションを参照。

### チェックする権限（必須）

Developer Portal（`https://discord.com/developers/applications` → 対象アプリ → Bot）と
Discord サーバーの "Sales Anchor" ロール、両方に設定する。

| # | 権限（英語） | 権限（日本語） |
|---|---|---|
| ☐ | Manage Roles | ロールの管理 |
| ☐ | Manage Channels | チャンネルの管理 |
| ☐ | View Channels | チャンネルを表示 |
| ☐ | Send Messages | メッセージを送る |
| ☐ | Read Message History | メッセージ履歴を読む |
| ☐ | Kick Members | メンバーをキック |
| ☐ | Ban Members | メンバーをBAN |

> **View Channels が特に重要**: Bot が対象カテゴリ・チャンネルを見えない状態だと、
> auto-setup で作成したチャンネルの削除・操作時に `403 Missing Access (50001)` が発生する。

### チェックしてよい権限（将来機能・任意）

実装前に別途 ADR・PO 承認が必要。現時点では API 呼び出しが存在しないため動作に影響しない。

| # | 権限（英語） | 権限（日本語） | 注意 |
|---|---|---|---|
| ☐ | Manage Webhooks | ウェブフックを管理 | 実装時は ADR 起案必要 |
| ☐ | Manage Messages | メッセージを管理 | **実装時は監査ログ・確認画面・権限制御を必須とする** |
| ☐ | Embed Links | リンクを埋め込み | |
| ☐ | Attach Files | ファイルを添付 | |
| ☐ | Add Reactions | リアクションを付ける | |

### チェックしない権限

| 権限（英語） | 権限（日本語） | 理由 |
|---|---|---|
| ✗ Administrator | 管理者 | 最小権限原則違反・チャンネル権限上書きをバイパスしてしまう |
| ✗ Manage Guild | サーバー管理 | Bot 業務範囲外 |
| ✗ Create Public/Private Threads | スレッド作成系 | ADR-091 でスレッド機能不使用と定義済み |
| ✗ Connect / Speak | 音声系 | Bot 業務範囲外 |

---

## auto-setup 実行前チェック

`/admin/discord-config` → 自動セットアップ を実行する前に確認する:

- [ ] 上記「チェックする権限（必須）」がすべて付与されている
- [ ] "Sales Anchor" ロールが `@everyone` より上位にある（本ガイドの Step 1〜5 参照）
- [ ] 旧セットアップ失敗分の "Sales Anchor" カテゴリが Discord サーバーに残っていない
  - 残っている場合は Discord サーバー設定 → チャンネルから手動削除してから実行する
  - Bot は `@everyone deny VIEW_CHANNEL` が設定されたカテゴリを削除できないため、必ず**手動**で削除する

---

## Developer Portal 未使用項目（触らなくてよい項目）

以下の項目は Developer Portal に存在するが、現時点では操作・設定不要。
詳細は `docs/adr/ADR-091-discord-bot-scope-definition.md` の「Developer Portal 未使用項目」セクションを参照。

| タブ / 項目 | 現状 | 将来対応 |
|---|---|---|
| Webhooks | 未使用。Bot 接続は OAuth2 フロー経由のため不要 | Webhook イベント受信が必要になった時点で ADR 起案 |
| Application Testers | 未使用。自社サーバーで検証中のため不要 | 複数テナントへのテスト配布フェーズで追加検討 |
| App Verification | 未申請。100 サーバー未満のため不要 | 100 サーバー展開前に申請（利用規約・PP URL・本人確認が必要） |

---

## 関連ドキュメント

- [discord-gateway-operations.md](discord-gateway-operations.md) — Gateway 運用・DM受信箱トラブルシュート
- [ADR-091](../adr/ADR-091-discord-bot-scope-definition.md) — Discord Bot 担当業務スコープ定義・権限意図の正本
- Discord 公式: ロール管理 — <https://support.discord.com/hc/ja/articles/214836687>
