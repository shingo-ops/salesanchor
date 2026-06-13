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

## 関連ドキュメント

- [discord-gateway-operations.md](discord-gateway-operations.md) — Gateway 運用・DM受信箱トラブルシュート
- [ADR-091](../adr/ADR-091-discord-bot-scope-definition.md) — Discord Bot 担当業務スコープ定義
- Discord 公式: ロール管理 — <https://support.discord.com/hc/ja/articles/214836687>
