# 段階4 の試し — まとめ役が担当を起こせるか（A1）・クラウドから本番を安全に読めるか（A2）

状態: 設計案作成済み／PO 承認済み（2026-11-09「1」＝先に小さく試す、2026-11-10「1」＝今登録できる 2 つの合言葉で A2 を試し、記録を書く窓は別に設計する、「1」＝手順書を 1 枚にまとめる、2026-11-11「1」＝調べ係は置き場を付けずに起動する形で A2 を閉じる）／A1 実施済み（○）／A2 実施済み（条件つき ○、§3-6）／実装なし（書類のみ）

親: S docs/handoff/ai-ops-247/stage4-requirements.md、S docs/adr/ADR-1012-ai-ops-247.md

## 1. なぜ試すか

PO 2026-11-09 の望む流れ（原文）:
「prod2とgit hubが見張る→以上が発生したらOpusに報告→クラウドの調査係が現状把握と原因を回帰分析で調査、→調査結果からOpusが改修方の要件定義と設計→許可が出たらクラウドの実行係が実施→不具合の解消が出来たか確認→Opusが恒久的な対策を要件定義と設計→クラウドの実行係が実施→予約タブ絵効果確認のための点検を予約→期間内にPDCAを回して解消したか効果確認」

この流れに要件を書き直す前に、まだ確かめていない 2 点を先に試す（PO 2026-11-09「1」）。

| 記号 | 確かめること | 結果 |
|---|---|---|
| A1 | クラウドのまとめ役（Opus）が、調べ係（Sonnet）を自分で起こせるか | ○（§2） |
| A2 | クラウドの調べ係が、本番の中身とグラフを読むだけで読めるか（書けないか・鍵が見えないか） | 置き場を付けない起動なら ○（§3-6） |

## 2. A1 の結果（2026-11-09 実施）

- 起動: routine を `run` で 1 回。クラウドの会話 cse_01HHUUpRd84DmQmbNzRrucnG。開始 09:08:50Z、終了 09:09:22Z（23 秒・3 往復・結果 success）。
- モデル: まとめ役 claude-opus-5-5（起動記録の init 行）。調べ係は Agent 道具に model sonnet を指定して起こし、自分のモデル名を claude-sonnet-5-5 と返した。
- 調べ係の答え: S docs/adr/ADR-1012-ai-ops-247.md の総行数 51、42 行目の本文。手元の origin/main と同じ。
- まとめ役の道具: Agent・Bash・Read など。RemoteTrigger（別の routine を起こす道具）は ×。CronCreate は ○（読み込みが要る道具）。
- 分かったこと:
  - 調べ係から実行係までは、1 回のクラウドの会話の中で担当を順に起こす形になる。1 件の通知で起こす routine は 1 回で済む（今の要件の約 7 回から減る。上限 B3 は 1 日 20 回）。
  - 調べ係の完了報告は、リポジトリの見張り（DONE / BLOCKED / NEEDS_DECISION の行が要る）に 1 回止められ、書き直して通った。クラウドでもリポジトリの見張りが効く。
- 次に直すこと（A2 で入れる）:
  - A1 の routine は allowed_tools だけで道具を絞っていたため、まとめ役から GitHub の道具や通知の道具が見えた。まとめ役は結果の通知を 1 件、自分で送った（PushNotification）。allowed_tools では道具が絞れないことは前例どおり（S docs/handoff/cloud-case-ai/design.md:195）。A2 は builtin_tools で絞り、コネクタを外す（§3-4）。

## 3. A2 の設計

### 3-1. 事実

- クラウドの network secret は、1 つのホストに 1 つ・ヘッダ 1 行（S docs/adr/ADR-1052-cloud-case-ai.md:39、S docs/handoff/cloud-case-ai/design.md:188）。
- 本番の読む窓は `api.salesanchor.jp` の `/api/v1/ops/read-window/query`（S nginx/nginx.conf:642）。ヘッダ `X-Read-Window-Token`（S docs/adr/ADR-1042-cloud-read-window.md:19）。
- 不具合の記録を書く窓（保守 API）も `api.salesanchor.jp`。ヘッダ `Authorization: Bearer <OPS_API_TOKEN>`（S backend/app/routers/ops.py:36,102-103,117-123）。読む窓と同じホストで値が違うため、1 つの環境に両方は登録できない。
- グラフの画面は `app.salesanchor.jp/grafana/`（S nginx/nginx.conf:309、S docker-compose.monitoring.yml:44）。読み取り専用の担当 `claude-code-reader`（Viewer）がある（S docs/adr/ADR-079-claude-code-monitoring-access.md:26）。鍵は `Authorization: Bearer <トークン>` で使う（Grafana 公式: grafana.com/docs/grafana-cloud/learn-and-build/developer-resources/api-reference/http-api/authentication/、Context7 で 2026-11-10 確認）。
- データ元の識別名: Prometheus `PBFA97CFB590B2093`、Loki `P8E80F9AEF21F6940`（S monitoring/grafana/provisioning/datasources/datasources.yml:9,17）。

### 3-2. 手元での事前の確かめ（2026-11-10、値は画面・記録に出していない）

| 確かめたこと | 結果 |
|---|---|
| 読む窓に鍵なしで `SELECT 1 AS ok` | 401 |
| 読む窓に PO の手元の控えの値を付けて同じ問い合わせ | 200・`ok` `1` が返った（控えは本物） |
| 読む窓で `SELECT count(*) FROM ops_incidents`（元の表） | 400・権限なし（pgcode 42501）。読む窓は元の表を読めない |
| 読む窓で `SELECT count(*) FROM ai_ro.public__ops_incidents`（読むための写し。S migrations/20261017_130100_create_ai_ro_views.sql:79） | 200・`682`（2026-11-09T16:15:32Z ごろ） |
| グラフの画面 `/grafana/api/health` | 200 |
| 手元の Viewer トークンで Prometheus に `count(up)` | 200・`9` が返った |
| 手元の Viewer トークンでフォルダを作る（書き込み） | 403（folders:create が無い） |

### 3-3. PO 判断（2026-11-10）

- A2 は、今登録できる 2 つ（読む窓とグラフ）で試す。
- 記録を書く窓は、相談係と同じやり方（専用の宛先 1 つ・鍵 1 つ。S docs/adr/ADR-1052-cloud-case-ai.md:39）で別に設計する。A2 では扱わない。

### 3-4. 形

- 専用の環境を新しく作る。ほかのクラウドの作業では使わない。
  - ネットワーク: None（相談係の前例。secret のホストは None でも届く: S docs/handoff/cloud-case-ai/design.md:184）。親の S docs/handoff/ai-ops-247/design.md:126 は Custom（2 ホスト）だが、None の方が狭い。届かなければ止めて相談する。
  - 環境変数に鍵を置かない。
- network secret は 2 つ:
  - `api.salesanchor.jp` に `X-Read-Window-Token`（前置きなし）＝ PO の手元の控えの値（今の読む窓の値。新しく作らない）。
  - `app.salesanchor.jp` に `Authorization`（前置き `Bearer `）＝ 新しく作るグラフ用のトークン（手元用と分け、別に取り消せるようにする）。
- routine（今の試し用 1 つを使い回す）:
  - 環境を新しい環境に替える。
  - builtin_tools は `["Bash","Read","Glob","Grep","Agent"]`（Agent は調べ係を起こすため）。コネクタは clear_mcp_connections:true で外し、get で session_context と session_request.config の両方の builtin_tools がこの 5 つだけ・mcp_connections が `[]` と確かめてから run（S docs/handoff/cloud-case-ai/design.md:196 の手順）。
  - 指示: 読むだけ。ファイルを変えない・commit・push・通知を送らない。

### 3-5. 成功条件

| 基準 | 検証方法 |
|---|---|
| K1 クラウドの調べ係が読む窓で本番の件数を読める | クラウドで `SELECT count(*) FROM ai_ro.public__ops_incidents` を流し 200。同じ時刻帯に手元で同じ問い合わせをして件数が一致 |
| K2 読む窓で書けない | クラウドで `UPDATE` 1 文を流し、成功しない（200 以外、または読み取り専用のエラー） |
| K3 グラフで数を読める | クラウドで Prometheus に `count(up)` を問い合わせ 200・数が返る |
| K4 グラフで書けない | クラウドでフォルダ作成を試し 403 |
| K5 鍵が AI から見えない | クラウドで `env` の項目名に TOKEN・GRAFANA・READ_WINDOW を含むものが 0 件。会話記録を手元で控えの先頭 8 文字で探して 0 件（値は出さない） |
| K6 調べ係が動く | まとめ役が Agent で sonnet の調べ係を起こし、K1〜K4 を調べ係が行う |
| K7 余計な道具が無い | まとめ役が見える道具の一覧に PushNotification・mcp__ が無い |

1 つでも × なら、その場で止めて PO に報告する。

### 3-6. A2 の結果（2026-11-11 実施）

PO の画面操作で環境 `ops-investigate`（ネットワーク None・network secret 2 つ）を作り、routine を `run` で 1 回ずつ動かした。どの回も routine の設定は builtin_tools 5 つ（session_context と session_request.config の両方）・mcp_connections `[]`・clear_mcp_connections:true を get で確かめてから動かした。

| 回 | 開始 (UTC) | 置き場 | 確かめたこと | 結果 |
|---|---|---|---|---|
| A2 | 03:51:44 | salesanchor を付ける | K1〜K7 | K1 ○（200・728 件。手元で 03:52:06Z に同じ問い合わせ 200・728 件）、K2 ○（`UPDATE` は 400「only SELECT / WITH / SHOW / EXPLAIN are allowed」）、K3 ○（`count(up)` 200・9）、K4 ○（フォルダ作成 403・folders:create なし）、K5 ×（`env` の項目名に TOKEN 等を含むもの 6 件）、K6 ○（調べ係が claude-sonnet-5-5 と返した）、K7 ×（`mcp__github__` の道具 約 50 個。merge_pull_request・push_files・create_or_update_file・delete_file を含む。ほかに `mcp__claude-code-remote__` 3 個。PushNotification は無い） |
| A2b | 03:57:16 | 付けない（sources `[]`） | 道具と `env` の項目名 | 道具は Agent・Bash・Glob・Grep・Read だけ、`mcp__` 0 個（K7 ○）。項目名は CLAUDE_CODE_MESSAGING_TOKEN・CLAUDE_SESSION_INGRESS_TOKEN_FILE・CLOUDSDK_AUTH_ACCESS_TOKEN・GH_TOKEN・GITHUB_TOKEN・MAX_THINKING_TOKENS。読む窓とグラフの鍵の項目は無い。K1 も再度 200・728 件 |
| A2c | 04:00:23 | 付けない | GitHub の鍵が使えるか（状態番号だけ） | `GH_TOKEN`・`GITHUB_TOKEN` とも api.github.com/user に 200。2 つは同じ値 |
| A2d | 04:06:48 | 付けない | その鍵で salesanchor を開けるか（読むだけ） | 403・permissions 欄なし・x-oauth-scopes の見出しなし |

- 鍵の漏れの確かめ: 手元に保存した実行記録を、読む窓とグラフの控えの先頭 8 文字で探して 0 件。ただし手元で読める実行記録は要約されたもので、会話の全文ではない。
- GitHub の設定（PO が画面で確認、2026-11-11）: Installed GitHub Apps の Claude は「All repositories」。Claude は 1 つ。別に「Claude Design Import」がある。
- 置き場を付けない起動で、salesanchor 以外の置き場に入れるかは未確認。一覧を取る操作は手元の自動の安全チェックに 2 回止められた（言い換えて送り直していない）。

判定（PO 2026-11-11「1」）:
- 調べ係は置き場を付けずに起動する。この形で K1〜K4・K6・K7 は ○。K5 は「鍵の項目名が 0 件」の基準では × だが、読む窓とグラフの鍵の項目は無く、ある鍵（GH_TOKEN）は salesanchor を開けない。
- 置き場を付けた起動は、実行係（コードを直す担当）用とする。PR を作る道具が付くため、調べ係には使わない。
- 流れ: 見張り → Opus に知らせる → Opus が置き場なしの調べ係を起こす → Opus が設計し PO の許可をとる → Opus が置き場ありの実行係を起こす → Opus が確かめ、再発防止と効果の点検を予約する。
- 残り: 夜中など手元の Opus が動いていないときに誰が知らせを受けるか、GitHub の許可が「All repositories」のままでよいかは、S docs/handoff/ai-ops-247/stage4-requirements.md の書き直しで決める。

## 4. PO の画面操作（順番どおり。値はチャットに貼らない。2026-11-11 実施済み）

（１）グラフ用のトークンを作る
- https://app.salesanchor.jp/grafana/ に管理者で入る → Administration → Users and access → Service accounts → `claude-code-reader` → Add service account token。
- 名前 `cloud-ops-trial`、期限 90 日（B-11 と同じ）。表示された値をコピーする（この画面でしか見られない）。

（２）専用の環境を作る
- https://claude.ai/code の環境の設定 → 新しい環境。名前 `ops-investigate`。ネットワークは None。

（３）合言葉を 2 つ登録する（新しい環境の network secret）
- 1 つ目: ホスト `api.salesanchor.jp`、ヘッダー `X-Read-Window-Token`、プレフィックスなし、トークンは手元の読む窓の控えの値。
- 2 つ目: ホスト `app.salesanchor.jp`、ヘッダー `Authorization`、プレフィックス `Bearer `、トークンは（１）でコピーした値。

（４）Opus に「登録した」とだけ伝える。環境の id は Opus が routine の一覧から確かめる（確かめられなければ PO に画面の id を聞く）。

## 5. 止め方・戻し方

- すぐ止める: 環境の network secret 2 つを消す。
- グラフ用のトークンを取り消す: Service accounts → `claude-code-reader` → `cloud-ops-trial` を削除。手元用のトークンには影響しない。
- 読む窓の値は今の値のままなので、消しても正答率の測定などは止まらない（その環境に登録した写しが消えるだけ）。
- DB・本番の設定は何も変えない。

## 6. 外部・過去事例

- 前例（社内）: 相談係のクラウド環境（S docs/adr/ADR-1052-cloud-case-ai.md）で、None・secret のホストだけ届く・builtin_tools で絞る形を実測済み。数値つきの外部事例は使わない（この試しの成功は K1〜K7 の実測で判定する）。

## 7. 維持の仕組み

- 結果は本書 §3 に追記し、S docs/handoff/ai-ops-247/stage4-requirements.md の書き直し（PO の流れ）で使う。
- グラフ用トークンの更新は 90 日（S docs/B-11_credential_management_policy.md:71 の行に含める）。
