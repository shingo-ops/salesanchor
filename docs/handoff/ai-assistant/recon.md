<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — AI アシスタント（秘書を まとめ役＋係 へ）

この文書は、今の秘書の仕組みと Hermes Agent の仕組みを、実物で確かめた記録です。

親（仕様書）: [../../specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)
要件のすり合わせ: [requirements.md](requirements.md)

**仕事名**: ai-assistant  
**日付**: 2026-11-25（origin/main `ed9a9f158` 基準）  
**対象ADR**: ADR-1056（今の秘書）・ADR-1058（AI の担当表）・ADR-009・ADR-091・ADR-159（Discord）・ADR-1077/1078/1080/1082/1087（秘書の足しかけ・Proposed）  
**担当**: architect（Opus 自身。同一 AI の調べ）

---

## 既存 ADR の検索

- `git grep -i "secretary\|秘書" docs/adr/` と `docs/specs/README.md` の索引で、上の ADR と仕様書 `docs/specs/secretary-chat/README.md` を確認（2026-11-25）。
- 本件は既存テーマ「アプリ内のチャット秘書」の延長として扱う（STANDARD-WORKFLOW §1.8）。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/assistant.py:85` | 秘書の容器の宛先 `SECRETARY_AGENT_URL`（http://secretary-agent:8090） |
| `backend/app/routers/assistant.py:106` | `agent_url(provider)`: 担当表の provider → 容器の宛先。配線の正本はここ 1 か所。新しい容器はここに 1 行足せば呼べる形 |
| `backend/app/routers/assistant.py:98` | 秘書の口の守り 4 つ（機能の札・super admin・顧客閲覧・請求書作成の権限） |
| `backend/app/services/ai_assignment.py:33` | `get_ai_assignment(db, job_key)`: 仕事ごとの担当（provider・model）を DB から読む |
| `backend/app/services/ai_assignment.py:47` | 画面で付け替えできる仕事は今 `secretary_intent` の 1 つだけ |
| `docker-compose.secretary-agent.yml:19` | 今の秘書の容器は read_only（書き込み不可） |
| `docker-compose.secretary-agent.yml:26` | mem_limit 512m |
| `backend/app/discord_gateway/private_channel.py:51` | 本人・スタッフ・bot だけが見られる非公開の部屋を作る関数が既にある |
| `backend/app/routers/invoices.py:153` | 請求書の列（issued_at・due_date・paid_at など） |
| `backend/app/routers/invoices.py:899` | 入金登録は issued/overdue → paid |
| `backend/app/routers/invoices.py:592` | 見積から作る請求書は `"due_date": None`（支払期日が空） |
| `backend/app/routers/dashboard.py:138` | 「未払い」= status が issued または overdue、と既に数えている |
| `backend/app/services/messaging_window.py:68` | 会話ごとの `last_inbound_at`（お客様の最後のメッセージ時刻） |

## Hermes Agent（外部・公式。Context7 `/nousresearch/hermes-agent` で確認 2026-11-25）

| 確認内容 | 出典 |
|---|---|
| 外から HTTP で話しかける口（OpenAI 互換 `/v1/chat/completions`・`/v1/responses`・`/health`）がある。鍵 `API_SERVER_KEY` 必須、既定は 127.0.0.1 だけで待つ | website/docs/user-guide/features/api-server.md・reference/environment-variables.md・gateway/platforms/api_server.py |
| 部屋（profile）ごとに設定・頭（model）・人格（SOUL.md）・手順書（skills）・覚え書きが別 | user-guide/profiles（2026-11-24 取得の写し） |
| まとめ役が係の部屋へ仕事を振る `profile_routes`（公式の追加部品 advanced-delegation）。振られた係はその部屋の頭・手順書・人格で動く | user-guide/features/delegation.md・tools/delegate_tool_routes.py |
| 振った結果ごとに「どの部屋・どの AI 会社・どの頭で動いたか」（route）が返る | user-guide/features/delegation.md |
| 追加部品が無い・切れているとき、振り分けは失敗として止まる（別の頭で勝手に動かない） | user-guide/configuration.md |
| 覚え書き・手順書の書き込みを人の許可待ちにできる（write_approval） | user-guide/features/memory・skills（2026-11-24 取得の写し） |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 請求書を overdue に変える仕組みの有無 | `grep -rn overdue backend/app` | ✅ 解消: 書き換える所は無い（読むだけ: `backend/app/routers/dashboard.py:138`・`backend/app/routers/invoices.py:1008`）。催促の基準は「issued かつ期日（空なら発行日）から N 日」で数える |
| 2 | Hermes を置くサーバーの容量（prod1 は 4GB で置かない方針） | 小さな試し（便0）で実測 | 未解決 → 設計 §6 の便0 で測る |
| 3 | Hermes の道具（端末・ファイル・ネット）を全部切った状態で、振り分けと下書きが動くか | 便0 で実測 | 未解決 → 便0 |
| 4 | LINE・Discord・メールでも最後の受信時刻が取れるか | 返信係を作るときに調べる | 未解決（最初の係ではないので後回し可） |
| 5 | ChatGPT の容器が本番で動いているか | 本番の読み取りで確かめる | 未解決（本件の判断には影響しない） |

**未解決ゼロ確認**: 未解決 2・3 は「動くかどうか」そのものなので、机の上では消せない。設計の便0（試しの部屋で実測）で消す。4・5 は最初の便に関係しない。
