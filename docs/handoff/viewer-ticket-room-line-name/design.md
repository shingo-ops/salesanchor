# 設計: 閲覧お試しのチケット部屋を LINE 名で作り、今の部屋も LINE 名に直す

- 状態: 設計案（Opus）。PO 決定: 2026-10-20 PO「1」（下の原文）。
- 現在地: `docs/handoff/viewer-ticket-room-line-name/recon.md`
- 対象 ADR: ADR-1019（閲覧ページ）。部屋の元の設計は `docs/handoff/gas-viewer-fresh-fast/design.md` D6。

## 1. 目的（PO の言葉）
- PO「チケット発行後のチャンネル名だけどLINE名で作成できる？すでに3名分作ってしまったが変更できるか？」
- PO が選んだ案「新しいチケット部屋をLINE名で作るように直し、片付けの仕組みも合わせて直す。その後、今の3部屋も名前を変える」（PO「1」、2026-10-20）。
- D6 の「個人の名前を部屋の名前に入れない」「trial-<id> は変えない」（前者は `docs/handoff/gas-viewer-fresh-fast/design.md:294`、後者は `:280`）を、この PO 決定で変える。部屋はカテゴリの中で本人・スタッフ・bot しか見られない（`backend/app/discord_gateway/private_channel.py` の overwrites）。LINE 名が見えるのはその人たちだけ。

## 2. 変更前 → 変更後
| | 変更前 | 変更後 |
|---|---|---|
| 新しい部屋の名前 | `trial-<番号>` | その人の LINE 名（前後の空白を除き、100 文字まで）。LINE 名が空、または LINE 名で作れなかったときは今と同じ `trial-<番号>` |
| 部屋の説明（topic） | 無し | `在庫集計ツールのお試し（番号 <番号>）`（片付けの目印） |
| 片付けの見つけ方 | 名前が `trial-数字` の部屋だけ | 名前が `trial-数字`、または説明が「在庫集計ツールのお試し（番号 数字）」と完全に同じ部屋 |
| 今ある `trial-<番号>` の部屋 | そのまま | 片付けの時（gateway の起動時と 24 時間ごと）に、その人の LINE 名と説明へ1回だけ直す |

## 3. 変更内容（file:line は origin/main）
### 3-1. 文面の SSOT に説明を足す
`backend/app/discord_gateway/viewer_bot_texts.py` の末尾に足す:
```python
ROOM_TOPIC = "在庫集計ツールのお試し（番号 {viewer_id}）"
```

### 3-2. 部屋の作成部品に topic を足す（顧客用チケットは変えない）
`backend/app/discord_gateway/private_channel.py` `create_private_text_channel` に、最後の引数 `topic: str | None = None` を足す。`guild.create_text_channel(...)` には topic が None でないときだけ `topic=topic` を渡す（None のときは今と同じ引数のまま呼ぶ。顧客用チケットの既存テストを変えずに通すため）。
さらに最後の引数 `log_name: str | None = None` を足し、作成成功のログ（:106-112）の `(%s)` には `log_name if log_name is not None else name` を出す。顧客用チケットは log_name を渡さないので今と同じ文字列のまま。閲覧の流れは `log_name=f"trial-{viewer_id}"` を渡し、LINE 名をログに出さない（`backend/app/discord_gateway/viewer_trial.py:5` の決まり）。 作成失敗のログ（:98-104）も、log_name が渡されたときは `exc` の文面を出さず `exc.status` だけを出す（Discord のエラー文に名前が入る可能性を消すため。顧客用チケットは今の文字列のまま）。

### 3-3. 部屋名を決める関数と作成
`backend/app/discord_gateway/viewer_trial.py`:
- :33 の近くに足す:
```python
_ROOM_TOPIC_RE = re.compile(r"^在庫集計ツールのお試し（番号 (\d+)）$")  # fullmatch で使う。T.ROOM_TOPIC と同じ形
_ROOM_NAME_MAX = 100


def _room_name(viewer_id: int, line_name: str | None) -> str:
    name = (line_name or "").strip()[:_ROOM_NAME_MAX]
    return name or f"trial-{viewer_id}"
```
- :109-123 `_create_room(guild, member, config, viewer_id)` を `_create_room(guild, member, config, viewer_id, line_name)` にし、
  1. `name = _room_name(viewer_id, line_name)`、`topic = T.ROOM_TOPIC.format(viewer_id=viewer_id)`、`log_name=f"trial-{viewer_id}"` で作る。
  2. 戻りが None で、かつ `name != f"trial-{viewer_id}"` なら、`trial-{viewer_id}`（topic は同じ）でもう1回だけ作る（LINE 名の文字を Discord が受け付けなかったときの逃げ道）。
- :143 の SELECT の**末尾**に `line_name` を足し（`SELECT id, email, discord_channel_id, line_name`）、:165 で `row[3]` を渡す。
- :261-267 の SELECT（FOR UPDATE）の**末尾**に `line_name` を足し（`... trial_expires_at, discord_user_id, line_name`）、:280 で `v[5]` を渡す。既存の `row[0..2]`・`v[0..4]` の番号は変えない。

### 3-4. 片付け（sweep_orphan_rooms、:366-404）
- 部屋の番号は、topic が `_ROOM_TOPIC_RE.fullmatch` に合えばその数字（topic を先に見る）、合わなければ名前が `_ROOM_NAME_RE` に合えばその数字。topic を先に見るのは、LINE 名が「trial-8」のような人の部屋を、別の番号の部屋と取り違えて消さないため（コード審査 任意1、2026-10-20）。topic は `topic = ch.topic if isinstance(ch.topic, str) else None` で取り、None なら合わないものとする。どちらにも合わない部屋は見ない（今と同じく、手で置いた部屋は消さない）。
- DB の読み取りを `SELECT line_name, discord_channel_id FROM public.viewer_accounts WHERE id = :id` に替える。行が無い部屋を消す動き・10 件の上限・DB 失敗で0件は今のまま。
- 今の部屋の名前直し: 行がある部屋のうち、①名前が `trial-数字` ②topic が `_ROOM_TOPIC_RE` に合わない（説明がまだ無い＝この変更より前に作った部屋）③行の discord_channel_id が `str(ch.id)` と同じ ④`_room_name(id, line_name)` が今の名前と違う、の4つが揃ったものだけ `await ch.edit(name=_room_name(...), topic=T.ROOM_TOPIC.format(viewer_id=id), reason="SalesAnchor viewer room renamed to LINE name")` を呼ぶ。失敗（例外）したら、`await ch.edit(topic=..., reason=同じ)` だけをもう1回呼ぶ（名前を Discord が拒んでも目印は付け、翌日から対象にしない）。それも失敗したらログ `[viewer-trial] sweep rename failed channel=%s` を出して次へ進む（消す処理は止めない）。上限は「名前直しを試した部屋の数」で1回 10 件（消す 10 件とは別に数える）。
  - 逃げ道で `trial-<番号>` になった部屋は topic があるので②で外れ、毎日やり直さない。
- 最後のログを `[viewer-trial] sweep deleted=%d renamed=%d checked=%d` にし、戻り値は今と同じ消した数。

### 3-5. 直すテスト（`backend/tests/test_viewer_discord_trial.py`）
- `_text_channel`（:64-70）の作り物に `ch.topic = None` を足す。
- 片付けのテスト（:291 `test_sweep_deletes_only_missing_ids_in_category` ほか）の作り物の行を2列（`(line_name, discord_channel_id)`）にする。
- on_open の作り物の行（:171 付近、3つ組）と on_code_submit の作り物の行（:242・:244 付近、5つ組）の末尾に line_name を足す。
- 新しいテスト: K1・K2・K4・K5・K8 を確かめるもの。K1 は説明の文字列をそのまま書いて比べ、K4 の片付けのテストは説明を `T.ROOM_TOPIC.format(viewer_id=N)` で組み立てる（文面と正規表現がずれたら K4 が落ちる）。K8 は作成成功と HTTPException の両方で、ログに LINE 名が含まれないことを見る。

## 4. 触らない範囲
- 顧客用チケット（`backend/app/discord_gateway/ticket_channel_creator.py`）の動き・部屋名。
- LINE 名を管理画面で直したときに部屋名も直す動き（今回は入れない。直したい時はスタッフが Discord で名前を変えられる。topic の番号で片付けは効く）。
- DB・migration・deploy.yml・本番 scripts/。

## 5. 代替案
- A（採用）: topic を目印にする。名前に何が入っても片付けが効く。スタッフが topic を消した部屋は片付けの対象外になるだけ（間違って消す方向には倒れない）。
- B: 片付けを「discord_channel_id が DB に無い部屋は全部消す」に替える。カテゴリに手で置いた部屋まで消すので不採用。
- C: 名前を「LINE名-番号」にする。PO の依頼は LINE 名なので不採用。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| LINE 名の文字を Discord が受け付けず部屋が作れない | `trial-<番号>` でもう1回作る（3-3） |
| 名前の変更に権限が足りない | 例外をログに出して飛ばす。部屋の作成・削除は今も動いているので同じ「チャンネルの管理」で足りる（公式: Modify Channel は MANAGE_CHANNELS。recon 参照） |
| 名前の変更の回数制限 | 公式頁に記載なし（未確認）。今の部屋は1部屋1回だけ、1回 10 件までに抑える |
| 英字・空白を含む LINE 名の見た目 | 【未確認】Discord はテキスト部屋の名前の英字を小文字に、空白を `-` にする場合がある。K7 の報告で PO に伝える。②の条件で繰り返しにはならない |
| 同じ LINE 名の人が2人 | 部屋名は重なってもよい（片付けは topic の番号、案内は部屋の ID で行う） |

## 7. 受入条件
|基準|検証方法|
|---|---|
| K1 新しい部屋が LINE 名＋説明で作られる | pytest: on_code_submit・on_open で create_text_channel に `name="<LINE名>"`、`topic="在庫集計ツールのお試し（番号 N）"` が渡る |
| K2 LINE 名が空・作成失敗のとき `trial-<番号>` で作られる | pytest: 空白だけの LINE 名で `trial-N`。1回目 None なら2回目が `trial-N` |
| K3 顧客用チケットの作成は変わらない | 既存の顧客用チケットのテストを変えずに合格（create_text_channel に topic を渡さない） |
| K4 片付けが topic の番号でも消し、目印の無い部屋は消さない | pytest: LINE 名＋topic の部屋で行が無ければ消す。名前も topic も合わない部屋は消さない。10件上限・DB 失敗0件の既存テストを §3-5 のとおり作り物だけ直して合格 |
| K5 今の `trial-<番号>` の部屋だけが1回だけ直る | pytest: 4条件が揃うと edit が呼ばれる。topic あり・ID 不一致・名前が同じなら呼ばれない。edit 失敗なら topic だけの edit がもう1回呼ばれ、消す処理は続く |
| K8 LINE 名がログに出ない | pytest（caplog）: LINE 名の部屋を作ったとき、ログに LINE 名の文字列が含まれない |
| K6 CI 全合格 | PR の必須チェック |
| K7 本番で今の部屋が LINE 名に直る | デプロイ後、gateway のログに `sweep deleted=… renamed=N` が出る（N は今の trial- 部屋のうち条件が揃った数）。PO が Discord で名前を目視 |

## 8. 外部・過去事例の参照と我々への応用
不要。Discord の公式仕様（名前 1〜100 文字・MANAGE_CHANNELS）だけで決まる小さな変更のため。

## 9. 維持の仕組み
- 守り手: `backend/tests/test_viewer_discord_trial.py` の K1〜K5・K8 の試験（CI の pytest で毎回走る）。
- 部屋名の決め方は `_room_name` の1か所、目印の文面は `backend/app/discord_gateway/viewer_bot_texts.py` の `ROOM_TOPIC` の1か所（SSOT）。片付けの正規表現は `backend/app/discord_gateway/viewer_trial.py` の `_ROOM_TOPIC_RE`。文面を変えるときは正規表現も合わせて変える（テスト K4 が落ちて気づく）。
- 戻し方: この PR を Revert する。直した部屋の名前は元に戻らず、戻した後の片付けは名前が `trial-数字` の部屋しか見ないので、LINE 名の部屋は片付けの対象外になる（その間に消した閲覧者の部屋はスタッフが Discord で消す）。
