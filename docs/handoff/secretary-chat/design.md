# 設計（第2版）— アプリ内のチャット秘書

この文書は、右下のチャットで頼んだ内容を AI が決まった形に直し、利用者が下書きを確かめて「作る」を押したときだけ今の機能で請求書・予定を作る仕組みの設計です。

親: [../../specs/secretary-chat/README.md](../../specs/secretary-chat/README.md)
現状の調べ: [recon.md](recon.md)（origin/main dc99a062e 基準）・[recon2.md](recon2.md)（origin/main 508e86036 基準。以下「r2 §X」）
KGI: [../../specs/secretary-chat/kgi.md](../../specs/secretary-chat/kgi.md)（PO 承認済み 2026-11-01）
ADR: [../../adr/ADR-1056-secretary-chat.md](../../adr/ADR-1056-secretary-chat.md)（案）

状態: 設計案作成済み・設計審査済み（APPROVE は §13）・PO 承認済みの前提（KGI と §2 の方針は PO 決定）・実装未着手。

## 1. 目的
- 利用者がチャットに普通の言葉で頼むだけで、請求書と予定を作れるようにする（PO 2026-11-01）。
- 004 の AI は 004 以外、001 の AI は 001 以外の情報に触れない（PO 決定）。

## 2. 方針の芯（第1版からの変更点）
**AI には会社のデータを一切渡さず、道具も持たせない。AI の仕事は「利用者の文 → 決まった形の頼み（JSON）」の書き換えだけ。名前を会社のデータから探すのは backend。書き込みは利用者が「作る」を押したときに、画面が今の口を利用者本人のログインで呼ぶ。**

- 第1版の「読む札」と「読む道具」（自己審査 R1・R3）はやめる。AI が読める会社のデータが無いので、K4（ほかの会社の値が出ない）は作りの上で成り立つ。
- 理由1: 会社の判定は今の `get_current_tenant`（`backend/app/auth/dependencies.py:262-277`。r2 §D）がそのまま効く。名前探しも同じ会社の範囲で動く。
- 理由2: 請求書の権限確認・監査ログ・変わった合図（ADR-1016）が今のまま効く。新しい書き込みの道を作らない。請求書・予定の写しを持たない（SSOT）。
- 理由3: 頼みの文に紛れた命令に AI が従っても、AI には道具もデータも無い。返す JSON は backend が型で検査する。

## 3. 変更前と変更後

| | 変更前 | 変更後 |
|---|---|---|
| 画面 | 右下の印・チャットの窓は無い | 001・004 の PO にだけ右下の印。押すと Drawer でチャット。下書きを確かめて「作る」 |
| AI | 本番サーバーに AI の道具は無い（recon §6） | 本番サーバーに専用の容器 `secretary-agent` を 1 つ。中で Claude Code を月額契約で `-p` 実行 |
| 書き込み | 利用者が各画面で入力 | 同じ口（`POST /invoices`・`POST /calendar/events`）を、利用者が「作る」で呼ぶ |

## 4. 使える人（PO 本人だけ）の決め方
本番の読み取りで確かめた事実（2026-11-01 08:12 JST、reader 鍵の道、AUDIT sha c22a83fdf611・c69f125f8532・cb1af5429f0a。メールは伏せる）:
- テナント 1 = 「テスト株式会社」、テナント 4 = 「HIGH LIFE JPN」。
- 有効な利用者は、テナント 1 に 2 人（id 1・87）、テナント 4 に 4 人（id 3・6・83・84）。
- アプリ全体の管理者の印（`users.is_super_admin`）を持つのは id 1（テナント 1）と id 3（テナント 4）の 2 人だけ。この印は PO と担当エンジニアだけに付ける決まり（PO 2026-10-07）。

決め: 次の 2 つが両方そろった人だけ使える。画面の印の出し分けと backend の許可の両方に同じ条件を入れる（画面だけでは守りにならない。r2 §D）。
1. 会社の入口: `public.tenant_features` に `(1,'secretary_chat',true)` と `(4,'secretary_chat',true)` の行がある（`require_feature`、`dependencies.py:652-682`）。
2. 人の入口: `is_super_admin` が true（`require_super_admin`、`dependencies.py:516-545`）。

- 使う人を広げるときは、2 を新しい権限キーに置き換える（第2段の判断）。今は新しい権限キーを作らない（変更を小さくするため）。

## 5. 仕組みの流れ
1. 画面: 利用者がチャットに書く → `POST /api/v1/assistant/messages`（本文 `{text}`）。
2. backend（新しい router `assistant.py`）:
   - 守り: `get_current_tenant`、`require_feature("secretary_chat")`、`require_super_admin`。
   - `secretary-agent` に `{text, now}` を送る。`now` は日本時間の今の日時。会社の名前やデータは送らない。
3. 容器 `secretary-agent`: Claude Code を次の形で 1 回だけ動かし、決まった形の JSON を返す（公式の根拠は r2 §A）。
   - `claude -p --output-format json --json-schema <固定の形> --tools "" --disallowedTools "mcp__*" --strict-mcp-config --no-session-persistence --permission-mode dontAsk --model sonnet`
   - 作業ディレクトリは空のディレクトリ（プロジェクトの設定を読ませない。r2 §A「Without `--bare` ... runs the hooks」）。
   - `--bare` は使わない（月額契約のログインを読まないため。r2 §A）。
   - 返る形（どちらか 1 つ）:
     - 請求書: `{"kind":"invoice","company_name","contact_name","items":[{"product_name","quantity","unit_price|null"}],"due_date|null","notes|null"}`
     - 予定: `{"kind":"event","title","start","end|null","is_all_day","location|null","description|null"}`（日時は `+09:00` 付きの ISO 8601）
     - わからない頼み: `{"kind":"unknown","reply"}`
   - `structured_output` 欄が無いときは `result` 欄の文字を JSON として読む。どちらでも、backend 側で型の検査（pydantic）に通らなければ「うまく読めませんでした」と返す（r2 §A の注意）。
4. backend: 名前を、今の会社のデータから読み取りだけで探す（新しい service `secretary_resolve.py`。今のログインの会社の範囲だけを読む）。
   - 会社: 会社名で探す（`companies.py:291-319` と同じ列）。候補を最大 5 件。
   - 担当者: 決まった会社の中で名前で探す（`contacts.py:258-283` と同じ列）。候補を最大 5 件。
   - 品物: 品物の名前は文字のまま使う（`InvoiceItemInput` は `product_id` が無くても作れる。r2 §E）。
   - 単価: AI に決めさせない。利用者の文に値段があればその数、無ければ空欄。空欄があると「作る」を押せない。
   - 予定の終わりが無いときは、始まりの 1 時間後にする（下書きに見せる）。
5. 画面: 下書きを窓に出す。会社と担当者は名前で見せ、候補が複数なら選ぶ。単価・日時・題名は窓の中で直せる。「作る」を押すと、画面が今の `POST /invoices` か `POST /calendar/events` を利用者本人のログインで呼ぶ。押さなければ何も起きない。
6. 記録: 1 回ごとに backend のログに 1 行（利用者 id・会社 id・かかった秒・成否・CLI が返す `total_cost_usd`）。頼みの文はログに書かない。

## 6. 容器の囲い
- ネットワーク: 新しいネットワーク `secretarynet` に `secretary-agent` と backend だけを置く。`secretary-agent` は backnet（postgres・redis がいる。`docker-compose.yml:567-569`）に入れない。→ 容器からデータベースに届かない（K4）。
- 外への通信: `secretarynet` は外に出られるふつうのネットワークにする。AI 会社（`api.anthropic.com`・`claude.ai`・`platform.claude.com`。r2 §A）に届く必要があるため。道具が無いので、AI が自分で外へ通信する手段は無い。
- 秘密: 月額契約のログイン情報は `CLAUDE_CODE_OAUTH_TOKEN` だけ。容器にだけ渡し、backend には渡さない。`ANTHROPIC_API_KEY` は容器に入れない（`-p` では API キーが優先されるため。r2 §A）。
- 容器の作り: `read_only: true`・`tmpfs: /tmp`・`cap_drop: ALL`・`no-new-privileges`・`mem_limit: 512m`（前例 `docker-compose.ai-reader-cloud-http.yml:42` ほか。r2 §G）。Claude Code の設定置き場は `CLAUDE_CONFIG_DIR=/tmp/claude`（tmpfs）。
- 同時に動かすのは 1 本。動いている間に次が来たら「いま考え中です」と返す。1 回 80 秒で打ち切る。
- 不要な通信を止める: `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`、`DISABLE_AUTOUPDATER=1`。
- ログイン情報が無いとき（PO がまだ入れていないとき）: 容器は「準備ができていません」を返し、画面はその文を出す。請求書・予定の機能はそのまま動く。

## 7. 代替案と選んだ理由

| 案 | 採らない理由 |
|---|---|
| 第1版: AI に読む道具と「読む札」を持たせる | AI が会社のデータを読むので、K4 を守る仕組み（札の照合・置き場）を新しく作ることになる（自己審査 R1・R3） |
| AI に書き込みの道具を持たせる | 「作る前に下書きを見せる」（PO 決定）に合わない。紛れた命令で書き込まれるおそれ |
| `--bare` で動かす | 月額契約のログインを読まない（r2 §A） |
| 使用量を `llm_usage_events` に書く | 台帳は Gemini 用（ADR-1004 §決定 1）。purpose・sdk は DB の CHECK で固定（r2 §B）で、足すには制約を作り直す migration が要る。月額契約は回ごとのお金がかからないため、第1段はログの 1 行で足りる |
| 新しい権限キーで「PO だけ」を作る | 今ある `is_super_admin` で、使える人が 001・004 の PO の 2 人にちょうど決まる（§4）。変更を小さくする |
| 3 社の AI を同時に入れる | 変更は一度に 1 つ |

## 8. リスクと対処

| リスク | 対処 |
|---|---|
| 月額契約の約束に反していて、契約を止められる（調査は PO 禁止） | 止められたらチャットが「準備ができていません」になるだけ。請求書・予定の機能は今のまま。見つからないように使い方をごまかす作りはしない（PO 決定） |
| 頼みの文が AI 会社に送られる | 送るのは利用者が書いた文と今の日時だけ。会社のデータは送らない。これを ADR に書く |
| `--tools ""` と `--json-schema` を一緒に使ったときの動き（実機で未確認） | `structured_output` が無いときは `result` を JSON として読む。backend が型で検査するので、どちらでも壊れない |
| 1 回のメモリ（公式は「4 GB+ RAM」の記載だけ。r2 §A） | 上限 512MiB・同時 1 本。K6 を 10 秒ごとに測る |
| 予定の口に権限確認が無い・予定の表に RLS の記述が無い（recon §2・§3） | 第1段は PO だけで、書き込みは今の口のまま。広げる前に確かめる |
| 単価を AI が作ってしまう | 単価は利用者の文の数か、利用者の入力だけ。空欄なら「作る」を押せない |
| 予定を作ると Google カレンダーにも映る（今の同期の設定次第） | 手で作るときと同じ動き。新しい動きは足さない |

## 9. 未確認と扱い
- U1（CLI の道具の絞り方・決まった形の答え）: 公式資料で確かめた（r2 §A）。実機の動きは、ログイン情報を入れたあとの試し（K2・K3）で確かめる。
- U2（ログインの保ち方）: `claude setup-token` で 1 年のトークン → `CLAUDE_CODE_OAUTH_TOKEN`（r2 §A）。トークンを作れるのは PO の契約のブラウザだけ。AI は作らない・値を見ない。
- U3（ネットワーク）: §6 で決めた。
- U4（予定の表の RLS）: 第1段では塞がない（§8）。

## 10. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 印は 001・004 の PO にだけ出る | backend の試験（会社の入口なし・管理者の印なしで 403）。本番で PO の画面と別の人の画面を目視。`tenant_features` の行が 2 行だけ |
| K2 請求書の下書き→「作る」で 1 件・押さねば 0 件 | 試し 5 回の件数の前後と中身の照合（ログイン情報を入れたあと） |
| K3 予定の下書き→「作る」で 1 件・押さねば 0 件 | 試し 5 回の照合（同上） |
| K4 ほかの会社の値が出た件数 0 | 試験 20 問の記録。容器が backnet に入っていないことの試験（compose を読む試験）。名前探しが今のログインの会社だけを読む試験 |
| K5 AI が書き込んだ件数 0 | `/assistant/messages` を呼んでも請求書・予定の件数が変わらない試験。監査ログの作成者が利用者本人 |
| K6 空きメモリ 0.4GB 以上 | 試し中 10 秒ごとの記録の最小値 |

## 11. 進め方（1 段ずつ・反映→測定→次）
- 段1（PR A・画面の部品だけ）: 右下の印 `FloatingActionButton` と吹き出し `ChatBubble` の金型を `components/` に登録する（`Xxx.tsx`・`Xxx.css`（`var()` だけ）・`Xxx.stories.tsx`。`docs/CC_UI_GOVERNANCE.md:5-19`）。PO の許可は 2026-11-01 の「必要な権限は全て」による。
- 段2（PR B・危険な変更を含むので GO が要る）: backend の口・名前探し・容器・compose・deploy.yml・`tenant_features` の行を入れる migration・画面のチャットの窓・i18n（ja/en 同じキー）・試験。
- 段3: 本番反映を 4 点で確かめる（届いた・動いた・形・指標）。ログイン情報が無い間は「準備ができていません」が出ることを確かめる。
- 段4（PO がログイン情報を入れたあと）: K2〜K6 の試し。合格したら、Codex・Grok を 1 つずつ、または使う人を広げる判断を PO に聞く。

## 12. 外部事例
- 使わない。この形（月額契約の CLI をアプリの中の秘書に使う）の、数字の付いた直接の事例を確かめていないため。数字は作らない。

## 維持の仕組み
- 守り手: .github/workflows/test.yml（段2 で backend の試験を足す。試験は (1) 会社の入口・管理者の印が無いと 403 (2) `/assistant/messages` で請求書・予定の件数が変わらない (3) `docker-compose.yml` の `secretary-agent` が backnet に入らず、データベースの接続先の環境変数を持たない、を確かめる）。画面の部品は .github/workflows/ui-governance-gate.yml が金型外の部品を止める
- 対象: AI が書き込めないこと（K5）と、データベースに届かないこと（K4）。使える人の条件（K1）。

## 13. 審査（同じ AI による自己審査・独立した第二者の審査ではない。2026-11-01）
- 判定: APPROVE（設計合格）。
- 第1版の指摘の行き先:
  - R1（AI 会社へ届く道と囲いのぶつかり）: AI がデータに届かない形にしたので、外へ出る道は AI 会社だけで足りる（§6）。
  - R2（下書きを名前で見せる）: §5-5 に入れた。
  - R3（読む札）: 札そのものをやめた（§2）。
- 合っている点: 書き込みは今の口だけ（recon §1・§2）。会社の判定は今のまま（r2 §D）。使える人は本番の事実で 2 人に決まる（§4）。秘密は容器にだけ（r2 §A の優先順位の罠も避けた）。危険な変更の区分（r2 §H）に沿って PR を 2 つに分けた。
- 残る未確認（実装可を止めない理由つき）: CLI の実機の動きとメモリ（ログイン情報が入るまで測れない。壊れても請求書・予定は今のまま動く作り）。
- PO 本人に残る作業: 月額契約のトークンを作り、GitHub の秘密 `CLAUDE_CODE_OAUTH_TOKEN` に入れる（ADR-1003 の例外「secrets の変更」は PO 本人。AI は値を見ない）。
