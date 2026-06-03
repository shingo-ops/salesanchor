# ADR-091: Discord Bot 担当業務スコープ定義・実装記録

## Status

Accepted

## Date

2026-06-02（起案） / 2026-06-03（実装完了・記録更新）

## Context

Sales Anchor は B2B SaaS CRM として、顧客とのコミュニケーション基盤に Discord を活用している。
現状、担当者・顧客ともに Discord アプリを直接操作する必要があり、Sales Anchor アプリとの往復が発生している。

この非効率を解消するため、Discord Bot を Sales Anchor に統合し、
**担当者も顧客も Discord を直接操作しなくても Sales Anchor アプリ上で全てが完結する**
状態を目指す。

## KGI

> Discord サーバーに入らなくても、Sales Anchor アプリで同等の使用感を実現し、アプリ内で全て完結させる

## KPI（Bot の担当業務 7 項目）

| # | KPI | 状態 | PR |
|---|-----|------|-----|
| 1 | プライベートチャンネルでの顧客コミュニケーション・受発注 | 実装済み | #1404, #1406 |
| 2 | アナウンス情報の発信 | 実装済み | #1408 |
| 3 | チケットツールによる顧客専用チャンネル自動発行 | 実装済み | #1404, #1406 |
| 4 | 顧客規模別専用チャンネルの管理・情報発信 | 実装済み | #1411 |
| 5 | チャンネル招待メッセージの送信 | 実装済み | #1404 |
| 6 | アプリからの顧客削除操作 | 実装済み | #1413 |
| 7 | 顧客規模と連動したロール自動付与 | 実装済み | #1416 |

## Decision

### Bot 担当業務の定義

Discord Bot の担当業務を上記 7 項目と定義する。

#### 設計方針

- **チャンネル内のスレッド機能は使わない**
  - 理由: 顧客（発注者）が Discord を直接操作するため、スレッドは手順が増えて混乱を招く
  - 代替: チャンネルに直接書くだけ。受注ごとの整理は Sales Anchor アプリ側で行う
- **顧客は Discord を直接操作、担当者は Sales Anchor アプリで完結**

---

## 実装記録（2026-06-02〜06-03）

### Bot 招待フロー（OAuth2）の技術的知見

#### 問題: `scope=bot` 単体では callback が呼ばれない

Discord の Bot Invite に `scope=bot` のみを使用した場合、
`redirect_uri` へのリダイレクトが発生しない（Discord の "callback-less flow" 仕様、2017年から不変）。

当初の実装では `scope=bot` のみで `guild_id` の自動取得を試みたが、
Discord が `redirect_uri` を呼ばずに `discord.com/oauth2/authorized` 画面に遷移するだけだった。

途中で `integration_type=0`（新アプリインストール方式）の除外も試みたが（PR #1481）、
これも根本原因ではなかった。

#### 解決策: `scope=bot applications.commands` + `response_type=code`

```python
params = {
    "client_id": _DISCORD_CLIENT_ID,
    "permissions": _DISCORD_PERMISSIONS,
    "scope": "bot applications.commands",
    "response_type": "code",
    "redirect_uri": _DISCORD_CALLBACK_URL,
    "state": state,
}
```

`applications.commands` を追加し `response_type=code` を明示することで
フル OAuth2 Authorization Code フローが実行され、
`redirect_uri?guild_id=GUILD_ID&code=CODE&state=STATE` にリダイレクトされる。

**外部エビデンス**: MEE6（1,950万サーバー）・Carl-bot（1,332万サーバー）が同一パターンを採用している。

#### 失敗した試み: `integration_type=0` の除外（PR #1481）

`scope=bot` で callback が来ない問題に対し、
Discord の新アプリインストール方式パラメータ `integration_type=0` が原因ではないかと仮説を立て除外を試みた。

```python
# 試みた変更（PR #1481）— 効果なし
params = {
    "client_id": _DISCORD_CLIENT_ID,
    "permissions": _DISCORD_PERMISSIONS,
    "scope": "bot",              # integration_type=0 を除外
    "redirect_uri": _DISCORD_CALLBACK_URL,
    "state": state,
}
```

結果: `integration_type=0` の有無に関わらず `scope=bot` 単体では callback が呼ばれなかった。
根本原因は `integration_type=0` ではなく、`scope=bot` 単体が callback-less flow である Discord の仕様そのものだった。
正解は上記の `scope=bot applications.commands` + `response_type=code` への変更（PR #1483）。

#### FRONTEND_BASE_URL 空文字バグ（PR #1469）

環境変数に `FRONTEND_BASE_URL=""` が設定されている場合、
`os.getenv("KEY", "default")` は `""` を返す（Python の仕様）。

```python
# NG: 空文字が返る
_FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "https://app.salesanchor.jp")

# OK: 空文字を False として扱う
_FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL") or "https://app.salesanchor.jp"
```

#### セキュリティ: guild_id バリデーション

Discord Snowflake ID（17〜19 桁の数字）以外は多層防御として拒否する。

```python
if not re.fullmatch(r"\d{17,19}", guild_id):
    return RedirectResponse(f"{channels_url}?discord_status=error&reason=invalid_guild_id")
```

#### CSRF 対策: Redis one-time state

`oauth_state.issue_state()` で Redis に保存した state を
`oauth_state.consume_state()` で検証後即削除（one-time use）。
tenant_id は state ペイロードから取得し、JWT 認証なしのコールバックを安全に処理する。

---

### Channels ページ UI 設計（PR #1501）

#### Discord 接続カードのデザイン決定

接続済み Discord カードを Facebook ページ連携カードと同スタイルに統一した。

**表示内容（接続済み時）**:
```
[ Discord Bot ]  [ Bot接続済み ]              [ 切断 ]
サーバーID: 1288437029213835356
接続日時: 06/03/2026, 12:00 / 接続者: 谷澤 伸吾
```

**決定理由**:
- Facebook カードと表示形式を統一することでユーザーの学習コストを下げる
- `Guild ID` という Discord 内部用語を `サーバーID` に変更（ユーザー向け表記）
- 接続日時・接続者名を表示することで「誰がいつ設定したか」をアプリ内で確認できる
- 「BotをDiscordサーバーに追加」ボタンは接続済み時に表示しない（切断ボタンに一本化）

#### 切断機能の追加

`DELETE /api/v1/admin/discord-config` を新規実装。
ConfirmModal で確認後に `tenant_discord_config` 行を削除する。

#### 接続者記録のための DB 変更

```sql
ALTER TABLE public.tenant_discord_config
    ADD COLUMN IF NOT EXISTS connected_by_staff_id INTEGER
    REFERENCES public.staff(id) ON DELETE SET NULL;
```

OAuth callback 時に `state` ペイロードの `staff_id` を保存し、
GET API で `staff` テーブルを JOIN して接続者名を返す。

---

## Scope（対象外）

- Discord サーバーの初期構築・チャンネル設計（人手で行う）
- Bot を介さない Discord 上での直接操作（担当者が行う場合は対象外）
- 音声チャンネルの管理

## Consequences

- 担当者の Discord 直接操作が不要になり、Sales Anchor アプリ上で顧客管理が完結する
- `scope=bot applications.commands` + `response_type=code` が Bot Invite の正しいパターンであることが実証された
- `connected_by_staff_id` により接続操作の監査証跡がアプリ内で確認できる
- 切断機能により誤設定の回復が UI から可能になった

## Related

- ADR-009: Discord Gateway（在庫解析・DM受信箱の基盤）
- ADR-072: write endpoint の `reset_tenant_context()` 必須ルール
- `backend/app/routers/discord_oauth.py` — Bot Invite OAuth2 フロー
- `backend/app/routers/discord_guild_config.py` — Guild 設定 CRUD + 切断
- `frontend/src/pages/channels/ChannelsPage.tsx` — Channels ページ UI
- memory: `project_discord_bot_kgi_kpi.md`
