# ADR-091: Discord Bot 担当業務スコープ定義・実装記録

## Status

Accepted

## Date

2026-06-02（起案） / 2026-06-03（実装完了・記録更新） / 2026-06-16（権限定義追記）

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

## Bot 権限定義（Developer Portal / サーバーロール）

Developer Portal の Bot Permissions および Discord サーバーの "Sales Anchor" ロールに付与すべき権限の正本。
運用手順は `docs/runbooks/discord-role-order-guide.md` を参照。

### 必須・既存実装あり

| 権限（英語） | 権限（日本語） | 意図 |
|---|---|---|
| Manage Roles | ロールの管理 | auto-setup で Sales Anchor Staff / Partner / Member ロールを作成・利用するため |
| Manage Channels | チャンネルの管理 | カテゴリ作成・チャンネル作成・権限上書き設定に必要。Discord ではカテゴリもチャンネル種別として扱われる |
| View Channels | チャンネルを表示 | Bot が対象カテゴリ・チャンネルを見えないと作成後の操作や削除ができないため |
| Send Messages | メッセージを送る | ticket-start チャンネルにチケット開始ボタンを投稿するため |
| Read Message History | メッセージ履歴を読む | 既存チャンネル確認・運用確認に必要 |
| Kick Members | メンバーをキック | 顧客削除時に Discord サーバーからも削除する既存 API（`discord_remove.py`）があるため |
| Ban Members | メンバーをBAN | 悪質顧客・スパムをアプリ側から BAN する既存 API があるため |

### 将来機能として許容

実装前に別途 ADR・PO 承認が必要。現時点では Developer Portal のチェックを入れてよいが、
API 呼び出し実装は承認後に行うこと。

| 権限（英語） | 権限（日本語） | 意図・注意 |
|---|---|---|
| Manage Webhooks | ウェブフックを管理 | 営業担当・スタッフがアプリ側で Webhook 設定できるようにする構想のため |
| Manage Messages | メッセージを管理 | アプリ側から Discord メッセージ削除を行う構想のため。**強い権限のため、実装時は監査ログ・確認画面・権限制御を必須とする** |
| Embed Links | リンクを埋め込み | 追跡番号 URL・請求書リンク等のプレビュー表示に必要 |
| Attach Files | ファイルを添付 | 請求書 PDF・写真共有を Bot 経由で行う構想のため |
| Add Reactions | リアクションを付ける | アプリ側リアクションを Discord へ同期する構想のため |

### チェックしない権限

| 権限（英語） | 権限（日本語） | 理由 |
|---|---|---|
| Administrator | 管理者 | 強すぎるため不要。チャンネル権限上書きをバイパスするため最小権限原則に反する |
| Manage Guild | サーバー管理 | 現状の Bot 業務範囲外 |
| スレッド系権限 | （Create Threads 等） | ADR-091 で「スレッド機能は使わない」と定義済み |
| 音声系権限 | （Connect, Speak 等） | 現状の Bot 業務範囲外 |

---

## Developer Portal 未使用項目（2026-06-16 現在）

Developer Portal に存在する以下の項目は、現時点では使用しない。
将来対応が必要になった時点で別途 ADR を起案する。

### Webhooks

**現状: 未使用**

- Sales Anchor の Bot 接続フローは `/discord/oauth/start` → `/discord/oauth/callback` の OAuth2 フローを使用する
- Discord Webhook Events（Discord → Sales Anchor への公開エンドポイント）は現時点で用意していない
- Developer Portal の "Webhooks" タブ（Bot がサーバー内に Webhook を作成するための設定画面）も現時点では使用しない
- **注意**: 「将来機能として許容」に記載の Manage Webhooks 権限（Bot がサーバー内 Webhook を作成・管理する）は Developer Portal の Webhooks タブとは**別物**である

### Application Testers

**現状: 未使用**

- 現在は自社 Discord サーバーで Bot 連携を検証する段階であり、公開前アプリを複数 Discord ユーザーにテスト配布するフェーズではない
- 将来、テナント担当者が Bot 招待フローをテストする段階になった場合に追加を検討する

### App Verification

**現状: 未申請**

- 100 サーバーを超えて Bot を展開する前に Discord から求められる審査
- 審査通過には以下が必要になる:
  - 利用規約 URL
  - プライバシーポリシー URL
  - チームオーナーの本人確認
- 現時点の auto-setup 動作確認・自社テナント運用には不要
- 将来 100 サーバー展開が見えた段階で別途対応する

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
- `backend/app/routers/discord_auto_setup.py` — auto-setup（カテゴリ・チャンネル自動作成）
- `frontend/src/pages/channels/ChannelsPage.tsx` — Channels ページ UI
- `docs/runbooks/discord-role-order-guide.md` — Bot 権限設定の実際のチェックリスト手順
- memory: `project_discord_bot_kgi_kpi.md`
