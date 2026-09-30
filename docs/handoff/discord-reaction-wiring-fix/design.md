# Discord リアクション配線修正 — design

> 設計: Opus（PO 承認済みプラン）。実装: Sonnet。
> recon: docs/handoff/discord-reaction-wiring-fix/recon.md
> 承認済みKGI: docs/specs/discord-reaction/kgi.md（新KGIは作らず、既存承認KGIの回復とする）
> 対象 ADR: ADR-091

## 目的

#3805 / #3809 で入った受信箱リアクション機能が「アプリから付けても成立しない」状態にある（recon 事実1〜6）。承認済みKGI ⑥（絵柄／個数／自分が押したか／押した人の名前）を満たす配線へ戻す。

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| フロントが渡すID | Discord snowflake（`msg.message_id`） | 内部ID（`msg.id`）。表示ガードは `msg.message_id` のまま |
| カスタム絵文字の取消 | パスに `name:id` を連結 | パスに `emoji_name`、クエリ `?emoji_id=`（Unicode は付けない） |
| リアクション API の DB 書込 | POST/DELETE が DB を書く（存在しない列を参照して失敗） | Discord API を呼ぶだけ。DB は書かない |
| DB の書き手 | REST と Gateway の2つ | Gateway のみ（SSOT） |
| Bot 自身の add | Gateway が無視 | Gateway が `is_bot_reaction=true` で記録 |
| 一覧 API の返却形 | `reactors: string[]`・`is_bot_reaction` | `is_mine`・`reactors: [{user_id, display_name}]` |
| 一覧取得失敗のログ | debug | warning（`reactions=[]` のフォールバックは維持） |
| 送信・取消の失敗 | 握りつぶし | 既存金型 Toast（`inbox.reactionSendFailed` / `reactionDeleteFailed`） |

## 設計判断と代替案

- DB の書き手を Gateway に一本化する。Discord を正本とし、`meta_message_reactions` への書込は Gateway のみ。REST は Discord API 呼び出しだけを行う。migration 不要。
  - 代替案（REST が `/users/@me` で Bot ID を取得して INSERT）: 書き手が2つ残り、UNIQUE が効かない Unicode 絵文字で重複行の恐れがあるため不採用。
  - 影響: 付けた絵文字は POST 直後ではなく、Gateway の書込後の SSE 再取得で表示される（recon 事実8の既存経路）。
- 「自分」の定義は Bot のリアクション（KGI「Bot名義」PO 承認済み）。`is_mine` はそのグループに Bot の行があること。
- 返却形はフロント型（契約）に合わせる。`is_bot_reaction` はフロント未使用のため返さない。
- エラー表示は既存金型 Toast。新規 UI 部品・新規 CSS・色直値・新規 i18n キーなし。

## 触らない範囲

migrations/、deploy.yml、scripts/、Discord 権限設定、カスタム絵文字ピッカーの表示（別便）。

## 受入条件

| 基準 | 検証方法 |
|---|---|
| API が `is_mine`・`reactors[{user_id,display_name}]` を返す | backend 単体テスト（`_group_reactions`） |
| Bot の add を Gateway が `is_bot_reaction=true` で記録 | writer / client 単体テスト |
| REST が DB を書かず `…/messages/{snowflake}/reactions/{enc}/@me` を叩く | httpx モックテスト（POST・DELETE） |
| フロントが `msg.id` で呼ぶ・DELETE の URL 形・失敗時 Toast | 型チェック（tsc）＋ vitest（`reactionPaths.test.ts`）＋コード差分 |
| CI 必須チェック全緑 | `gh pr checks` |
| 本番: 手順書 0〜6 がすべて○（6 は取消成功） | PO が tenant_001 で実施（本 PR の外・完了定義 docs/STANDARD-WORKFLOW.md） |

## 外部・過去事例の参照と我々への応用

該当なし：既存機能の配線不整合の修正であり外部事例に依存しない。

## 影響範囲（呼び出し元の全走査結果）

- `process_reaction` の呼び出し元は backend/app/discord_gateway/client.py の `_process_reaction` のみ（`grep -rn "process_reaction(" backend/`）。
- `sendReaction` / `deleteReaction` の利用は InboxPage.tsx（props 受け渡し）と InboxMessageThread.tsx のみ。
- 返却形の利用は frontend/src/pages/inbox/InboxMessageThread.tsx のリアクション表示バーのみ（既にフロント型どおりに読んでいる）。

## 戻し方

マージコミットを revert する。migration・設定変更を含まないため DB 側の戻し作業はない。

## 維持の仕組み

- 守り手: 新規単体テスト（返却形・Bot記録・REST非書込）が CI の pytest で常時実行される（backend/tests/test_discord_reaction_wiring.py）。URL 形は vitest（frontend/src/pages/inbox/reactionPaths.test.ts）が常時実行される。
- 対象: 本修正の配線。
- 関所なしの場合: 該当なし。
