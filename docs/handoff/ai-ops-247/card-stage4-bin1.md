# 実装カード 段階4 便1 — 作る前の確かめ 3 つ（コードの変更なし）

> この文書は何か: AI 保守運用 24 時間化 段階4 の、最初の便の段取り表です。段階4 の設計（`docs/handoff/ai-ops-247/stage4-design.md`）で「実装カードで確かめる」とした 3 つ（X4 の鍵・X1 の /fire・組織側の App の範囲）を、コードを作る前に確かめます。結果しだいで後の便の作り方が変わるため、最初に置きます。

- 設計: `docs/handoff/ai-ops-247/stage4-design.md` §1 X1・X4、§2 弊害、§8、§13
- 対象ADR: ADR-1012
- 状態: 設計審査済み（Opus 審査役 APPROVE on 44ac6c22a）。PO 承認済み（2026-11-13「1」= 確かめの作業を始める）。2026-11-13 に K1・K2・K3 とも ○（結果は設計 §13「実装の最初の便の確かめ」）。残りは K1 の routine（無効）の片付け（PO の画面）。環境 ops-investigate-3 は調べ係の環境として残す
- 危険便: いいえ（コード・表・本番の設定・`deploy.yml`・本番 `scripts/` を変えない）。ただし K1 で本番の読み取りの窓へ 1 回だけ問い（`SELECT 1`）を送る。本番の表は読まないが、窓の監査の記録に 1 行残る。クラウドの環境と secret を PO の画面で作るので、PO の承認を得てから始める
- 担当: Opus（段取り・クラウドへの依頼・結果の確かめ・記録）／PO（画面の操作・`!` の命令・Mac の「ターミナル」の窓で 1 回）。実装役（Sonnet）は使わない

## 0. 段階4 全体の便の分け方（案）

便ごとにカードを出し、それぞれ作る前に PO の承認を得る（設計 :3）。この便は便1 だけを扱う。便2 以降のカードは便1 の結果を見てから書く。

| 便 | 中身 | 表の変更（migration・GO #番号） | secret の変更 | 先に要るもの |
|---|---|---|---|---|
| 1（この便） | 確かめ 3 つ（§2）。コードなし | なし | 新しい調べ係の環境に相談係の鍵を入れる（PO の画面）。試しの routine の /fire の鍵を作る（PO の画面） | なし |
| 2 | C3-0（報告が届いた出来事を id だけで 1 行）と C3-1（報告を 1 件に複数通） | あり | なし | 便1 の K1 が ○ |
| 3 | C3-2（alertname・severity を伏せる対象から外す。PO 決定 D3） | あり（伏せたビューの作り直し） | なし | なし |
| 4 | C1-1（注記の round に「許可」を足す。PO の言葉を detail に） | なし（コードだけ） | なし | 便2 で出来事の見分け方が決まっていること |
| 5 | サーバーが札を作り、routine を /fire で起こす（U1・U3）。回数の上限 B2・B3、R5、全停止 R6 | なし（予定。カードで確かめる） | あり（routine ごとの /fire の鍵を本番に置く。PO の承認） | 便1 の K2 と K3 が ○、便2・便4 |
| 6 | F9 を 1 日 1 回まとめる・GitHub の App の範囲を毎週読む（P5） | なし（予定） | 未定 | 便5 |
| 予備 | C1-2（実行係が報告を読む GET の窓） | なし | なし | K2 で 8000 字が届かなかったときだけ |

- 便2 と便3 を分ける理由: どちらも表の変更で、1 回に 1 つだけ変える（変更→反映→測定→次）。便2 は報告の表と出来事の表、便3 は伏せたビューで、戻し方が別になる。
- 便2 のカードで決めること（設計 §8 の残り）: 報告が届いた出来事の kind と actor。案は §7。

## 1. 範囲

入れる:
1. K1: 新しい調べ係の環境から相談係の窓口へ 1 回だけ送り、鍵が通るかを見る（X4）
2. K2: 試しの routine に /fire の口を付け、P1 と同じ 8000 字の文を /fire で 1 回送り、欠けずに届くかを見る（X1）
3. K3: 組織（GEN-RYU-System）の Claude の App が、どのリポジトリを許されているかを PO の画面で 1 回読む
4. 結果を設計書 §13 に追記する（書類だけの PR）

入れない:
- コード・表・本番サーバー・`deploy.yml`・本番 `scripts/` の変更
- 本番の secret（GitHub secret・サーバーの .env）の変更
- 相談係の環境と、その鍵の変更
- 試し用の環境 ops-trial-p2・古い環境 ops-investigate・ops-investigate-2 の片付け（設計 §13「試しから設計に足すこと」のとおり、別に PO と行う）。3 つの名前は、2026-11-12 に Opus が RemoteTrigger で読んだ claude.ai の環境一覧にあるもの
- App の範囲を変えること（K3 は読むだけ。広ければ止めて PO に聞く）

## 2. 確かめ 3 つ

### K1 相談係の鍵の控えが、本番の鍵と同じ値か（X4）

前提の事実:
- 鍵の正本は GitHub secret CASE_AGENT_TOKEN（`docs/handoff/cloud-case-ai/design.md:103`）。控えは Mac の Keychain（service salesanchor-case-agent-token・acct case）にある（設計 §13 P4）。
- 相談係の窓口は case-api.salesanchor.jp の `POST /api/v1/ops/read-window/query` で、ヘッダ `Authorization: Bearer <鍵>` を受ける（`docs/handoff/cloud-case-ai/design.md:187`・`nginx/nginx.conf:725-733`）。
- 窓口の返し方（`backend/app/ops/read_window_http.py:64-95`）:
  - 401（本文 `unauthorized`）: :68-73。ヘッダの名前・前置き `Bearer ` が違うときも、鍵の値が違うときも同じ 401 になる。401 だけでは、どれが違うかは分からない。
  - 鍵が通ったあと: 413（本文が大きすぎる :75-77）・429（本文 `busy`。同時に 1 本だけ :79-80）・200（:86-87）・400（:88-91）・503（:92）。200・400・503 には、窓が付けるヘッダ `X-Read-Window-Rc` が付く（:39-41）。
- 窓の手前の nginx と、クラウドの中継も数を返す。nginx: 421（名前違い `nginx/nginx.conf:715-716`）・429（回数の上限 :728-729）・503（窓が落ちている :741）。中継: 403（許されていないホスト。設計 §13 P2 の example.com）。これらは鍵を見る前に返るので、鍵の合否は分からない。
- network secret は 1 つのホストに 1 つ・ヘッダ 1 行（`docs/handoff/ai-ops-247/stage4-trials.md:35`）。None のネットワークでも secret のホストには届く（`docs/handoff/cloud-case-ai/design.md:184`）。

手順:
（１）PO が画面で新しい環境 ops-investigate-3 を作る。ネットワーク None。network secret 3 つ:
  - case-api.salesanchor.jp: ヘッダ `Authorization`・前置き `Bearer `・値は Keychain の控え
  - raw.githubusercontent.com・codeload.github.com: ダミーの値（P2 と同じ形。設計 §13 P2）
  この環境を段階4 の調べ係の環境として使い続ける（試しのためだけの環境ではない）。
（２）控えの値は、PO が `!` で写しの命令を流してクリップボードに入れ、画面に貼る。命令は値を画面に出さず、文字数だけを出す。貼ったあとクリップボードを空にする。Opus は値を見ない・チャットに貼らせない。
  命令（PO が流す）: `security find-generic-password -s salesanchor-case-agent-token -a case -w | tr -d '\n' | tee >(wc -c | sed 's/^/文字数: /' >&2) | pbcopy`
  貼り終えたら: `pbcopy < /dev/null`
（３）Opus が、リポジトリなし・コネクタなしの routine を ops-investigate-3 に作り、`run` で 1 回動かす。中身は curl 1 回だけ:
  `curl -sS -D /tmp/k1.h -o /tmp/k1.txt -w '%{http_code}\n' -X POST https://case-api.salesanchor.jp/api/v1/ops/read-window/query --data-binary 'SELECT 1'`
  続けて `grep -i '^x-read-window-rc' /tmp/k1.h` と `head -5 /tmp/k1.txt` を出させる。`-v` は使わない（送ったヘッダ＝鍵が出るため）。鍵は環境の secret が付ける。依頼文には鍵を書かない。
（４）Opus が get_run_log で、HTTP の数・`X-Read-Window-Rc` の有無・本文の先頭を読む。
（５）終わったら Opus がこの routine を無効にする（RemoteTrigger の update で enabled を false。消すのは PO の画面）。

合否（設計 §13 P4 は「200 を見る」。`SELECT 1` が通れば 200 になるので、200 が本来の ○。窓が鍵を通したあとにしか返さない形も ○ に数える）:
- 200 → ○。鍵が合っている。作り直しは要らない。
- 400 か 503 で `X-Read-Window-Rc` がある → ○（鍵は通った）。問いが通らなかった理由は別に記録し、PO に伝える。
- 429 で本文が `busy` → ○（鍵は通った。窓の同時 1 本に当たった）。
- 401 → ×。ただし、すぐに「控えの値が違う」とは決めない（ヘッダの名前・前置きの違いでも 401 になるため）。PO が環境を作り直し（`docs/handoff/ai-ops-247/stage4-trials.md:137`。画面で secret を直せないため）、ヘッダ `Authorization`・前置き `Bearer `（後ろに空白 1 つ）を見直して 1 回だけやり直す。2 回目も 401 なら止め、設計 §2 弊害（:75）の作り直しの道と、相談係が止まる時間を含めて PO に聞く。
- 000（届かない）→ 判定できない。PO が環境を作り直し、secret のホスト名を見直して 1 回だけやり直す。2 回目も 000 なら止めて PO に聞く。
- それ以外（`X-Read-Window-Rc` の無い 503・`busy` でない 429・403・421・413 など）→ 判定できない（鍵を見る前に返った、または想定外）。止めて PO に聞く。

### K2 /fire で 8000 字が欠けずに届くか（X1）

前提の事実:
- /fire は routine ごとの鍵（Authorization: Bearer）と、ヘッダ `anthropic-beta: experimental-cc-routine-2026-04-01`・`anthropic-version: 2023-06-01` を付けた POST。本文の text は任意で、そのまま文として渡る（Context7 `/websites/code_claude` の routines。2026-11-13 に確かめた）。
- 文の長さの上限は公式資料に書かれていない（同上）。
- P1 は RemoteTrigger の run で、8227 字（17207 バイト）が欠けずに届いた（設計 §13 P1）。送った文は Opus の作業用のフォルダ（この会話の scratchpad の `p1/payload_8k.txt`。リポジトリの外）に残っている。手元にしか無いので、K2 の前に Opus がその sha256 を P1 の記録と照らし、違えば止める。
- P1 では、届いた文の各行の頭に 4 字の字下げが付いていた。クラウド側が字下げを外して比べ、sha256 が一致した（P1 の結果の記録 注記1。送った文は 162 行・8227 字・sha256 f5138068…で始まる値）。/fire の道で、文が別の印（たとえば `<routine-fire-payload>`）に包まれるかは確かめていない。
- 無効にした routine に /fire が届くかは、まだ確かめていない（公式資料に書かれていない）。

手順:
（１）PO が画面で、P1 の試しの routine に API の口を足し、鍵を作る。鍵は 1 回だけ画面に出る。routine の名前は「ops trial P1: fire text size (sonnet, no repo)」（2026-11-12 に Opus が RemoteTrigger で読んだ routine 一覧の名前）。リポジトリなし・コネクタなし。
（２）PO が画面の「コピー」で鍵をクリップボードに入れ、Mac の「ターミナル」の窓（この会話の `!` ではない。入力を求める画面が要るため）で次を流す。`-w` を最後に置くと、値を引数に置かずに入力を求める（`man security` の add-generic-password「Put at end of command to be prompted (recommended)」）。「password data for new item:」と求められたら貼り付けて Enter を押す。もう一度「retype password for new item:」と求められたら、同じく貼り付けて Enter を押す（`/usr/bin/security` の中にこの 2 つの文言がある。2 回目が出るかは試していない）。打った値は画面に出ない。
  `security add-generic-password -s salesanchor-ops-trial-fire -a trial -w`
  入れ終えてから `pbcopy < /dev/null`（クリップボードを空にする）。Opus は値を見ない。
（３）PO が `!` で、Opus が用意した送る台本（作業用のフォルダに置き、中身を会話で見せてから）を流す。台本の決まり:
  - 鍵は `security find-generic-password -s salesanchor-ops-trial-fire -a trial -w` で変数に読み、シェルの組み込みの `printf 'Authorization: Bearer %s\n' "$tok"` から curl の `-H @-` へ標準入力で渡す（curl の引数に値を置かない）。
  - `set -x` と curl の `-v` は使わない。
  - 本文は P1 と同じ文を JSON の text に入れたファイル（P1 の `body_8k.json` と同じ作り）を `--data-binary @` で送る。
  - 出すのは HTTP の数と、返事の中の会話の id だけ。返事の全文はファイルに残し、鍵が入っていないことを件数で確かめる。探す文字は引数に置かず、`grep -cF -f <(printf '%s\n' "$tok") <ファイル>` のように標準入力の側から渡す。
（４）Opus が list_runs と get_run_log で、届いた文を読む。比べる前の外し方は 2 つだけに決めておく: ①P1 と同じく、各行の頭の 4 字の字下げを 1 回だけ外す ②文の前後に包みの印の行（`<routine-fire-payload>` など、送った文に無い行）があれば、その開きと閉じの行だけを外す。外した行は全部記録する。そのうえで行数・最後の行・wc -m・sha256 を出し、P1 の値と比べる。この 2 つ以外の違いは外さず、× の材料として記録する。
（５）終わったら PO が画面で API の口の鍵を消す（試しの鍵を残さない）。Keychain の項目も PO が `!` で `security delete-generic-password -s salesanchor-ops-trial-fire -a trial` を流して消す。
- 注記（2026-11-13）: 実際には、（４）で英語の前置き 1 文（仕組みが足す決まり文句）も外して比べた。①②の外になり、PO「1」で ○ とした。今後は③として加える。（５）の API の鍵は Opus が画面で消した。どちらも設計 §13 に書いた

無効の routine に /fire が届かなかったとき（2xx 以外、または実行記録が増えない）: 試しの routine を、PO の承認を得て 1 回だけ有効にしてから送り直す。送り終えたら Opus が無効に戻す。有効にする前に、Opus が RemoteTrigger の get で、この routine に先の予定（cron・まだ来ていない run_once_at）が無いことを確かめる。予定があれば有効にせず止める。

合否:
- 外したあとの行数・最後の行・sha256 が P1 と一致 → ○。設計を /fire の文で渡せる。予備の C1-2 は作らない。
- 一致しない・切れた印がある → ×。便5 の前に予備の C1-2（報告を読む GET の窓）のカードを書く。
- 有効にしたあとも /fire が 2xx 以外 → 判定できない。HTTP の数を記録し、止めて PO に聞く。

### K3 組織の Claude の App の範囲（設計 §8・§13 P3）

前提の事実:
- 個人の導入先は 2026-11-12 に「Only select repositories」に戻した（設計 §13 P3）。
- 組織の導入先は shingo-cc の鍵では読めない（admin:org が無く 404。設計 §13 P3）。

手順: PO が画面で GitHub の組織 GEN-RYU-System → Settings → GitHub Apps → Claude → Repository access を開き、「All repositories」か「Only select repositories」か、選ばれたリポジトリの名前を会話で伝える。Opus は答えを記録する（非公開のリポジトリ名は公開の書類に書かず「非公開の記録」と書く）。

合否:
- Only select repositories で、一覧が相談係で PO が決めた一覧（`docs/handoff/cloud-case-ai/design.md:322`）と同じ、かつ salesanchor が一覧に入っている → ○（設計 :125。実行係は salesanchor を読むため）
- 一覧が PO の一覧と同じだが salesanchor が入っていない → 止めて、足すかを PO に聞く（設計 :125。足すまで実行係は動かさない）
- All repositories、または一覧が違う → 止めて PO に聞く（直すかは PO が決める。直すまで実行係は動かさない）
- 組織に Claude の App が入っていない → 範囲が広がる道は無いと記録する。ただし実行係が組織側の App を通らないことを便5 のカードで確かめる
- 注記（2026-11-13）: 上の「一覧に salesanchor が入っている」は導入先を分けて書いていなかった。salesanchor は個人の持ち物なので、組織の導入先には入れられない。PO「1」で、組織 = PO の決めた一覧と同じ・salesanchor は個人の導入先の一覧にある、として ○ にした（設計 §13）

## 3. PO にお願いする操作（全部で 6 つ）

| # | 場所 | 操作 | 戻し方 |
|---|---|---|---|
| 1 | claude.ai の環境の画面 | ops-investigate-3 を作る（§2 K1（１）） | 環境を消す |
| 2 | 端末の `!` | 控えをクリップボードへ写し、画面に貼り、クリップボードを空にする（K1（２）） | なし（値は画面に出ない） |
| 3 | claude.ai の routine の画面 | 試しの routine に API の口を足し、鍵を作る（K2（１）） | 鍵を消す（K2（５）） |
| 4 | Mac の「ターミナル」の窓 | 鍵を Keychain に入れる（K2（２）） | Keychain の項目を消す |
| 5 | 端末の `!` | 送る台本を流す（K2（３）） | なし（1 回送るだけ） |
| 6 | GitHub の組織の画面 | App の範囲を読む（K3） | なし（読むだけ） |

`!` の命令と台本は、PO の承認のあと Opus が作業用のフォルダに置き、中身を会話で見せてから流してもらう。

## 4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| K1 の HTTP の数が分かり、○ か × かが決まっている | 調べ係の routine の実行記録（get_run_log）に curl の出した 3 桁の数がある |
| K2 の届いた文が P1 と同じか分かっている | 実行記録の wc -m・sha256・最後の行を、P1 の値（設計 §13 P1）と並べて記録した |
| K3 の範囲が分かっている | PO の答えを記録した（非公開のリポジトリ名は書かない） |
| 試しの /fire の鍵が残っていない | PO の画面で API の口に鍵が無い。Keychain に service salesanchor-ops-trial-fire が無い（属性だけ読む） |
| 鍵の値がどこにも書かれていない | 設計書・この文書・PR・会話に鍵の値が 0 件 |
| 結果が設計書に残っている | 設計書 §13 に K1〜K3 の行がある（書類だけの PR・審査役の APPROVE） |
| コード・表・本番に変更が無い | PR の差分が `docs/` と `.claude-pipeline/` だけ |

## 5. 止まるとき

- K1 が、環境を 1 回作り直したあとも 401（鍵の作り直しになり、相談係が止まる時間が出るため）
- K1 が「判定できない」形（§2 K1 の合否の最後の行）、または 2 回目も 000
- K2 の /fire が、routine を有効にしたあとも 2xx 以外
- K2 の P1 の送った文の sha256 が、P1 の記録と違う
- K3 で範囲が広い
- 画面の欄が、この文書の書き方と違う（推測で埋めない）
- 鍵の値が画面・ファイル・会話のどこかに出た（すぐ止め、その鍵の作り直しを PO に聞く）

止まったら、何をしていたか・何が起きたか（生の出力の場所）・次に何を決めてほしいかの 3 つを PO に伝える。

## 6. 戻し方

- K1 の routine を無効にする（Opus。RemoteTrigger の update）。消すのは PO の画面。
- 環境 ops-investigate-3 を消す（PO の画面）。相談係の環境と本番の設定は変えていない。K1 の 1 回の問いは本番の窓の監査の記録に残るが、記録は消さない（読んだ事実を残すための記録のため）。
- 試しの routine の API の口と鍵を消す。Keychain の試しの項目を消す。K2 で試しの routine を有効にした場合は無効に戻す。

## 7. 便2 のカードで決めること（今は決めない）

報告が届いた出来事の kind と actor（設計 §2 C3-0・§8）。今の事実:
- 出来事の表の kind は 6 つ・actor は 3 つに限られる（`migrations/20261016_100000_create_ops_incident_tables.sql:54-57`）。
- 報告の口は相談係の鍵で通る（`backend/app/routers/ops_case.py:496-499`）。相談係の鍵は ops_token（保守の鍵）とは別の鍵（相談係の鍵: `backend/app/routers/ops_case.py:72-73`。保守の鍵は OPS_INGEST_TOKEN・OPS_API_TOKEN: `backend/app/routers/ops.py:4,99,103`）。
- 便2 は C3-1 で表を変えるので、同じ migration で kind と actor を足せる。

案（便2 のカードで審査を通してから PO に出す）:
- 案 A: kind に `case_report`、actor に `case_agent` を足す。誰が書いたかを偽らない。表の決まりを変える。
- 案 B: 今の `ai`・`ops_token` を使い、detail の形で見分ける。表の決まりは変わらないが、actor が実際の鍵と違う。
- Opus の今の考え: 案 A。理由は、記録が「誰が書いたか」を正しく持つことが障害記録の目的だから。決めるのは便2 のカード。

## 8. 外部・過去事例

この便は確かめだけで、作り方を選ばないため、外部の事例は使わない。過去の事例として、同じ形の確かめ（P1・P2・P4）の結果（設計 §13）を前提に使う。

## 9. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

- 設計 §8 の残り（X4・X1・組織の App）が、それぞれ K1・K2・K3 に割り当てられている。
- K1 の合否は、窓が鍵を通したあとにしか返さない形（200、`X-Read-Window-Rc` 付きの 400・503、本文 `busy` の 429）かどうかで決める。401 はヘッダの書き方の違いでも出るので、1 回作り直してから決める（`backend/app/ops/read_window_http.py:64-95`）。
- 鍵の値は引数・画面・ファイルに置かない（K1 は環境の secret、K2 は入力を求める画面と `-H @-`）。
- K2 は P1 と同じ文を使うので、違いは送る道（run と /fire）だけになる。
- 鍵の値は PO の端末の中だけで動き、Opus もクラウドも値を見ない。
- 残る点: 環境の画面の欄の名前が段0 のときから変わっているかは未確認。違えば止める（§5）。

## 維持の仕組み

- 担当: ADR-1012 のテーマとして Opus が持つ。結果は設計書 §13 に足し、便2 のカードの前提にする。
- ops-investigate-3 は段階4 の調べ係の環境として残す。鍵を取り消すときは、相談係の環境と両方止まる（設計 §2 弊害）。
