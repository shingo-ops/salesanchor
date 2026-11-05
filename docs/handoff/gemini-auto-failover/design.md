# design — Gemini の道の自動切り替えと止まりの見張り

状態: 設計第1版（Opus、2026-11-05）。完了条件は PO 2026-11-05「1」で承認済み。実装の進め方（設計 → 点検 → 作る係 → わざと断られる試験）も同じ「1」で承認済み。
設計審査（クラウドの Opus・同じ AI による点検で、独立した第三者の点検ではない）: 1回目 REVISE（R1〜R5）→ 7a1180fba で直し。2回目 REVISE（R1〜R5 は全部直ったと確認。必須 N1 は card-1 の「10番以外」の文言だけ、推奨 N2・N3）→ 041889ecf で直し、差分を Opus が確かめた。実物の google-genai 2.8.0 と aiohttp 3.14.5 で、非同期の呼び出しが届かない中継で ClientProxyConnectionError を出すことを点検役が実行して確かめた。
根拠: [recon.md](recon.md)。決定の記録: [ADR-1062](../../adr/ADR-1062-gemini-auto-route-failover.md)。
関連: ADR-1050（送り直し・諦めの知らせ）、ADR-1012（24時間保守）、docs/handoff/gemini-direct-default/design.md（10/02 の「直接が既定・人が中継に切り替える」。本件で置き換える）、docs/runbooks/gemini-egress-emergency.md。

## 1. 目的（PO の言葉）

「落ちたら自動で切り替えて prod2 から解析させる非常装置」と「半日気づかない事態の再発防止」。
奥の目的: 仕入元の投稿の解析が、人が気づくのを待たずに続くこと。続かないときは、すぐ人に届くこと。

## 2. 完了条件（KGI、PO 承認済み）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 直接の道で「この国からは使えません」と断られたら、同じ呼び出しを prod2 の中継の道ですぐやり直す。人の操作なし | 試験 T1・T4。本番で、直接を先にした1回きりの呼び出しを worker と backend で流し、記録に「直接→中継」の切り替えと成功が出る |
| K2 | 中継の道が使えないときは直接の道に戻す | 試験 T2・T6・T6b（実物の部品に届かない中継を渡す。T6b は非同期）。本番で、届かない中継を先にした1回きりの呼び出しで「中継→直接」の切り替えが記録に出る（今は直接が断られるので、最後は場所の断りで終わるのが正しい） |
| K3 | 解析が待っているのに30分成功が無ければ、断られ方に関係なく Discord に1通 | 試験 T9a〜T9g。本番で、今日の 08:49〜19:25 を基準時刻にした1回きりの判定が「止まり」を返す。知らせの文の1回きりの送信が管理者用 Discord に届く |
| K4 | 失敗の記録に断りの理由の文を残す | 試験 T5・T11・T12。本番の反映後、失敗した試みの validation_result に reason がある（失敗が出るまでは、T5 と本番の1回きりの呼び出しの出力で確かめる） |
| K5 | 訳す機能も同じ自動切り替え | 試験 T3。本番で、直接を先にした訳の1回きりの呼び出しが backend で成功する |

## 3. 対象と対象外

対象:
- 新しい部品 `backend/app/services/gemini_route.py`（道の選び方の正本。ここ1か所だけ）
- 解析の3か所の呼び出し（recon §3 の呼び出し1〜3）と、訳す機能（recon §4）
- 失敗の記録に reason を足す2か所（recon §3 の :439 と v102 の :518）
- 新しい定期作業 `backend/app/tasks/gemini_route_watch.py`（5分ごと）

対象外（理由）:
- 作品比べ `backend/app/services/tcg_work_comparison_svc.py:98`: 人が明示で呼ぶ道具で、自動では動かない（:94）。道は環境変数のまま。
- .env の GEMINI_PROXY_URL・GEMINI_GRPC_PROXY・grpc_proxy の行: 消さない。最初の道を決める値として残す（§4-1）。
- 送り直しの条件（`backend/app/tasks/tcg_extraction_recovery.py:306-314`・`:402-410`）: 変えない。raw の末尾で引いているので、raw の文も変えない。
- 今日失敗した約64件のやり直し: 別に PO に聞く。
- DB の形の変更: なし。

## 4. 変えた後の動き

### 4-1. 道の選び方（gemini_route.py）

- 道は2つ: 直接（direct）と中継（relay）。
- 中継の先: GEMINI_PROXY_URL があればその値、無ければ定数 `DEFAULT_RELAY_URL = "http://gemini-egress:18888"`（docker-compose.yml の gemini-egress と同じ。値はこの1か所だけ）。
- 最初の道: 直近10分以内に「切り替えて成功した道」があればそれ。無ければ GEMINI_PROXY_URL があれば中継、無ければ直接。覚えるのはプロセスの中だけ（worker の子プロセスごと）。
- 切り替える条件（どちらか）:
  - 場所の断り: google.genai.errors.APIError で code が 400、かつ message に "location is not supported"（大文字小文字は区別しない）。
  - 道に届かない: 例外の連なり（`__cause__`・`__context__`、5段まで）に httpx.ConnectError・httpx.ConnectTimeout・httpx.ProxyError、または aiohttp.ClientConnectorError（中継の失敗の子を含む）のどれかがある。非同期の呼び出しは aiohttp を使うため（recon §6）。読み込み中の時間切れ（ReadTimeout）は切り替えない（長い呼び出しを2倍にしないため）。
- 切り替えは1回の呼び出しで1回まで。切り替え先も失敗したら、切り替え先の例外を投げる（最初の例外は `__context__` に残る）。
- 切り替えて成功したら、その道を10分覚え、Redis の数を1つ足す（§4-3）。Redis が使えなくても呼び出しは止めない。
- 記録: 切り替えのたびに logger.warning を1行（道の名前と理由。鍵は出さない）。

### 4-2. 呼び出し側

- 解析（呼び出し1〜3）: 今の `client = _get_genai_client()` の行は残し、`client.models.generate_content(...)` を `gemini_route.generate_content_routed(client, model=..., contents=..., config=...)` に置き換える。既存の試験が `_get_genai_client` を差し替えている作りをそのまま使える。
- `_get_genai_client()` は中身を `gemini_route.build_client(gemini_route.first_route())` に任せる。
- 訳す機能: 古い部品をやめ、新しい部品の非同期の呼び出し `gemini_route.agenerate_content_routed(...)`（`client.aio.models.generate_content`）にする。温度は今と同じ 0.1。使用量台帳の sdk 名は "google-genai" にする（`backend/app/services/llm_budget.py:172` で許されている）。

### 4-3. 止まりの見張り（gemini_route_watch.py、5分ごと）

1. 止まりの判定: 直前30分に終わった試み（finished_at）で、completed が0、かつ failed が1以上 → 止まり。条件は recon §8 で過去7日に当てはめ、空振り0・今日は 08:50 に当たる。
2. 止まりで、Redis の印が無ければ Discord に1通送り、印を置く。文は「解析が30分成功していません」「直前30分の失敗 N 回」「最後の失敗の理由（reason、無ければ raw）」「止まった判定の時刻」。
3. 成功が戻り（completed が1以上）、印があれば「解析が戻りました」を1通送り、印を消す。
4. 道の切り替えの知らせ: Redis の数（直接→中継、中継→直接）が1以上で、その向きの「知らせ済み」の印が無ければ1通送り、印を24時間置く。呼び出しの途中では Discord に送らない（解析を遅くしないため）。
5. 送り先が未設定・Redis が使えない → warning を出して何もしない（送りすぎを防ぐ）。
6. 試みが「始めた」のまま止まった場合: 15分で recover-stale-extraction-jobs が待ちに戻し、やり直しが completed か failed で終わる（recon §7）。その failed をこの見張りが数えるので、止まりの知らせは最大で約55分（15分＋次の回収まで最大10分＋30分）で出る。K3 の「30分」は終わった試みについての数で、PO 承認の文言は変えない。

### 4-4. 失敗の理由の記録

- `gemini_route.failure_reason(exc)`: 例外の連なりから APIError を探し `"{code} {status}: {message}"`、無ければ httpx の例外の型名と文、それも無ければ型名。`key=...` と `AIza` で始まる鍵の形を伏せ、300字まで。
- 記録の2か所で `{"raw": ..., "category": ..., "reason": failure_reason(exc)}` にする。raw と category は今のまま（送り直しの SQL が raw の末尾で引いているため）。

## 5. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| ずっと中継だけにする | prod2 が止まると解析も止まる。今日の .env はこの形で、片方が死ぬと止まるのは変わらない |
| 中継の箱の中で切り替える（tinyproxy の前に判定を置く） | 断りの理由は Google の返事の中身にあり、通り道からは見えない（HTTPS の中身は読めない） |
| 部品の送り直し設定（HttpRetryOptions）で済ます | 道を変えられない。訳す機能を含む全部に効いてしまう（ADR-1050 Why と同じ理由） |
| 見張りを Prometheus の規則にする | 解析の成否は DB にしかなく、Prometheus に数が出ていない。数を出す仕組みから作ると変更が大きい |
| 訳す機能は古い部品のまま grpc_proxy で切り替える | grpc_proxy はプロセス全体に効く環境変数で、呼び出しごとに変えられない |

## 6. 危ないことと対処

- 両方の道が同時に使えない → 切り替えでは直らない。§4-3 の見張りが30分で知らせる。
- 見張りが1件の失敗で鳴る（投稿が少ない時間）→ 過去7日の空振りは0（recon §8）。2週間の空振り回数を数え、2回以上なら条件を見直す（§9）。
- Redis が止まると見張りが黙る → 今の諦めの知らせ（ADR-1050）と同じ弱さ。受け入れる。
- 訳す機能の部品替えで返事の形が変わる → 訳の結果は `.text` の JSON を読むだけ（変更後の `backend/app/services/message_translator.py:362` 以降）で、部品に依らない。本番で1回きりの呼び出しを流して確かめる（K5）。
- 場所の断りの文を Google が変える → 切り替わらなくなる。§4-3 の見張りが30分で知らせ、reason に新しい文が残るので条件を直せる。

## 7. 実装の分け方

1回の実装カード（[card-1.md](card-1.md)）。DB の変更なし・migrations なし・deploy.yml なし・本番 scripts なし → ADR-135 の危険な PR には当たらない。

## 8. 外部・過去事例の参照と我々への応用

- 同じ断り文の過去の報告は docs/handoff/gemini-egress-via-prod2/design.md §11 にある（東京の事業者で 2026-09-19〜・Singapore の利用者で 2026-05-09〜17、どちらも原因不明・数日で直った例あり）。適用限界: 直る時期も原因も書かれておらず、「また起きる・いつ直るか分からない」ことの裏付けにしか使えない。
- 設計が正しいことの証明には外部事例を使わない。根拠は本番の断り文の実測（recon §1）と過去7日の記録への当てはめ（recon §8）。

## 9. 維持の仕組み

| 何が | どう守られるか |
|---|---|
| 道の選び方が1か所だけ | gemini_route.py に集め、試験 T10 が「generate_content を直接呼ぶ所が解析と訳の対象ファイルに無い」ことを検査する |
| 見張りの定期作業が登録されている | `backend/tests/test_celery_beat_registered.py` と試験 T9 |
| 見張りが空振りしていないか | 2026-11-19 に、2週間分の知らせの回数を Discord の履歴と DB の当てはめで数える（tasks/todo.md に1行） |
| 切り替えが本当に起きたか | Discord の切り替えの知らせ（24時間に向きごと1通）と worker の warning の記録 |
| 手順書 | docs/runbooks/gemini-egress-emergency.md を「自動で切り替わる。人の切り替えは両方駄目なときだけ」に直す（この PR で） |

- 守り手: backend/tests/test_gemini_route.py
