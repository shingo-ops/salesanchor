HEAD: 8242dfcedf037434fdc5f5eb1f71190d7e80140d（origin/release/lead-regression-recon。指定どおり 8242dfced）
判定: APPROVE

# review — リードのカルテで成約しやすさを分析する（設計 第6版の審査）

- 審査したもの: docs/handoff/lead-regression/design.md（第6版）・docs/handoff/lead-regression/recon.md（第5版からの変更なし。git diff 59b0c012e HEAD --stat は design.md の1ファイルだけ）
- 照合の基準: origin/main 9e202335936921ad6a7f83bee0847cd09e987776。design.md:9 の第6版の基準 26dec7f26 からの差分（git diff --name-only 26dec7f26 origin/main）に、design.md が引く leads.py・webhook.py・conv_logs.py・tasks/dashboard.py・services/tenant.py・maintenance.py・sa02_recon_monitor.py は含まれない
- 前回の審査: origin/release/lead-regression-design-v5-report の docs/handoff/lead-regression/review-design-v5.md（第5版 REVISE・直す点5件）
- 第5版との差分: git diff 59b0c012e HEAD -- docs/handoff/lead-regression/design.md（17行足し・13行消し）
- 審査役: Claude Opus（設計審査役）。本番には接続していない。本番の中身に関わることは「未確認」と書く
- 行番号の書き方: 「ファイル:行」は origin/main の行。design.md は HEAD 8242dfced の行

## 判定の理由（要約）

第5版の直す点5件はすべて直っている（項目1）。特に直す点1の統合の向きは、実物の決まり（消える方が lead 以外なら断る `backend/app/routers/leads.py:3102`〜3109）に合わせて書き直され、§6-1 手順0（id と lead_id の組の記録）と手順1（3つの止める条件・手順2 より前に流す）で、元のリードの行がテスト用リードへ付け替わった場合に手順5・手順7 の前で止まる形になった。K6 の「元の行は1行も消えない」は守られる。

足した引用は中身としてすべて実物と合う。行の範囲の端が1行ずれるものが2件あるだけ（項目2）。leads の created_at・updated_at を最初のメッセージの時刻にする直しは、K5③・§3-3・§3-2・§4-2・K3d と食い違わない（項目3）。骨組みも崩れていない（項目4）。

直さないと進めない点は無い。下の「実装カードで拾う補足」3件は、実装カードを書くときに書き足せば足りる。

---

## 項目1 第5版の直す点5件

| # | 直す点（第5版） | 判定 | 根拠 |
|---|---|---|---|
| 1 | 統合の向き（§3-4・§6-1 手順0・手順1） | ○ | 下の 1-1〜1-4 |
| 2 | 本物との違いの漏れ（leads.created_at・受信の翻訳） | ○ | design.md:61 ④（created_at・updated_at に最初のメッセージの時刻。理由に `backend/app/tasks/dashboard.py:92`〜93）、design.md:66 ④（meta_messages の受信で自動翻訳の依頼を出さない `backend/app/routers/webhook.py:923`〜929）、design.md:69 ④（conversation_logs の受信の翻訳をしない・`conv_log_<id>` の行も無い `backend/app/routers/conv_logs.py:326`〜327・147〜173） |
| 3 | K6・§6-1 の audit_logs の数え方 | ○ | design.md:191 の (a)（new_data の lead_id。送信の記録と conversation_logs の create）と (b)（table_name が leads で record_id がテスト用リードか 4・6）。design.md:204 の手順9 も (a)・(b) を報告する形に直っている。K6 の欄 design.md:41 は「数え方は §6-1」 |
| 4 | K4 のレビュー役 | ○ | design.md:39「設計審査役（Opus）がマージ前のレビューで金型だけを使っていることを確かめ」、frontend/src/pages/dashboard/ に置けば UI の点検の対象に入ることも書き足した |
| 5 | §10 のエコーの道の記録 | ○ | design.md:235。`backend/app/routers/webhook.py:557`（channel_type 'messenger'）・573（platform 'messenger'）、824〜829（呼び出しは db・schema・tenant_id・sender_id だけ。関数の引数も psid まで 536〜541行）と一致 |

### 1-1. §3-4 の統合の向き（design.md:131〜134）

- 決まり: 消える方の状態が lead 以外なら 400 で断る（`backend/app/routers/leads.py:3102`〜3109、docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md 22行）。残す方の状態は問わない（`backend/app/routers/leads.py:3241`）。design.md:131 と一致。○
- 起こり得る向き（design.md:132）: テスト用リードを残す方・元のリード 4・6（状態 lead。recon.md:111）を消える方。付け替えてから消える方を消す（`backend/app/routers/leads.py:3237`〜3249 は処理の順序を書いた説明文。手順4 で13表の lead_id を付け替え、手順6 で消える方を消す）。このまま §6-1 を流すと手順5・手順7 が元の行を消す・持ち主を空にすることも書かれている。○
- 逆の向き（design.md:133）: テスト用リードの状態を人が lead に戻した場合だけ。○
- 統合の記録（design.md:134）: merge_absorb は record_id が残す方、merge_delete は record_id が消える方、どちらも table_name は leads、new_data に lead_id のキーは無い（`backend/app/routers/leads.py:3278`〜3289）。○

### 1-2. §6-1 手順0（design.md:195）

meta_messages・conversation_logs を id と lead_id の組で記録する、と書き足された。手順1 の「lead_id が記録した値と違う」の比べる元になる。○

### 1-3. §6-1 手順1（design.md:196）

- 起こり得る向きで止める条件が3つ足された: ①元のリード 4・6 のどちらかが leads に残っていない ②手順0 で記録した元の meta_messages・conversation_logs の行の lead_id が記録した値と違う ③audit_logs に merge_absorb・merge_delete の行があり、record_id がテスト用リードか 4・6。統合が起きれば、①（消える方は消される）と③（記録は2件必ず書かれる `backend/app/routers/leads.py:3278`〜3289）の両方に当たるので、見逃さない。○
- 逆の向きの今の条件（元のリードに `tlr-` の行・件数が増えた）も残っている。○
- 「この点検は手順2 より前に必ず流す」「手順5・手順7 が元の行を消したり持ち主を空にしたりしないのは、ここで止まるからである（K6）」と K6 との結び付きが書かれている。○

### 1-4. K6 が守られるか

手順1 で止まれば、手順2〜8 は流れない。統合で付け替わった元の行は手順5（lead_id がテスト用リードの conversation_logs）と手順7（leads を消して meta_messages の持ち主が空になる）の前に見つかる。K6 の検証（design.md:41。手順9 で元の行の id がすべて残っていること）とも食い違わない。○

## 項目2 第6版で足した引用の照合

すべて origin/main で行の中身を見た。

| 引用（design.md の行） | 実物 | 結果 |
|---|---|---|
| `backend/app/routers/leads.py:3102`〜3109（131行） | 3102 行の `if loser_row["status"] != "lead":` から 3109 行の raise の閉じまで | ○ |
| leads.py:3237〜3249（132行） | merge_leads の説明文（13表の付け替え・loser の削除の順序）。処理そのものではなく説明文の行 | ○（中身は合う。説明文であることは補足） |
| leads.py:3278〜3289（134行・191行） | merge_absorb（record_id=master_id）・merge_delete（record_id=loser_id、new_data は merged_into と reason） | ○ |
| leads.py:3226〜3232（131行） | 3226 行がパス `/leads/{master_id}/merge`、3230 行が merge_leads | ○ |
| `backend/app/routers/webhook.py:923`〜929（66行） | 本文があれば enqueue_inbound_translation("meta_messages", …) | ○ |
| webhook.py:557・573（235行） | 557 行 "channel_type": "messenger"、573 行 "platform": "messenger" | ○ |
| webhook.py:824〜829（235行） | _create_outbound_lead_for_echo(db, schema, tenant_id, sender_id)。platform を渡さない | ○ |
| webhook.py:646〜656（61行④） | INSERT INTO leads は 646〜651行、値の辞書は 652〜657行（status は 657行） | ○（範囲の終わりが1行短い。中身は合う） |
| webhook.py:547〜550（61行④） | INSERT INTO leads は 546〜551行（546 行が INSERT の始まり、551 行が VALUES の閉じ） | ○（範囲の両端が1行ずつずれる。中身は合う） |
| `backend/app/routers/conv_logs.py:326`〜327（69行④） | 本文があれば _fire_translation | ○ |
| conv_logs.py:147〜173（69行④） | 149 行で `conv_log_{log_id}`、153〜159 行で ensure_inbound_translations、161〜173 行で translated_text・original_language を書き戻す（commit は 174 行） | ○ |
| conv_logs.py:310〜320（69行・191行） | audit_logs に create・table_name conversation_logs・new_data に lead_id | ○ |
| `backend/app/tasks/dashboard.py:92`〜93（61行④） | leads を created_at の新しい順に5件 | ○ |
| `backend/app/services/tenant.py:355` からの leads の定義（61行④） | 355 行 CREATE TABLE … leads、405 行 created_at TIMESTAMPTZ DEFAULT NOW()、406 行 updated_at TIMESTAMPTZ DEFAULT NOW() | ○ |
| 「本物は updated_at を画面で直すたびに変える」（61行④） | `backend/app/routers/leads.py:592`・602（updated_at = NOW()） | ○ |
| docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md 18行・22行 | 18 行が13表の付け替え、22 行が loser の条件 status != 'lead' で 400 | ○ |
| recon.md:111 | リード2件（id 4・6）とも状態 lead | ○ |

ずれの一覧（中身はすべて合う。直さなくてよい程度）:

1. design.md:61 ④ の webhook.py「646〜656」は、書き込みの範囲が 646〜657 行（status は 657 行）。
2. design.md:61 ④ の webhook.py「547〜550」は、INSERT の文が 546〜551 行。design.md:236 の「547・550」も同じ範囲を指す。
3. design.md:132 の leads.py「3237〜3249」は処理の説明文（docstring）の行で、付け替えと削除の実際の処理の行ではない。

## 項目3 第6版の直しで新しく生まれた矛盾・SSOT

1. **leads の created_at・updated_at を最初のメッセージの時刻にすること**:
   - K5③（design.md:40 ③）: 数える列は meta_messages.created_at と conversation_logs の occurred_at・created_at だけで、leads.created_at は入っていない。最初のメッセージの時刻は書き込む日の 180〜70日前（design.md:109）なので、仮に数えても「2日前より後」に当たらない。毎朝の突合は leads を数えない（`backend/app/tasks/sa02_recon_monitor.py:74`。第5版の審査 項目4-4 と同じ）。食い違いなし。○
   - §3-3（design.md:118）: 過去の時刻を明示して入れる決まりと同じ向き。食い違いなし。○
   - §3-2（design.md:109）: 最初のメッセージの日時の作り方がそのまま created_at の値になる。こちらから営業したリードはこちらの最初の送信の時刻で、本物のエコーの道がそのときにリードを作る（`backend/app/routers/webhook.py:546`〜551）ことと合う。○
   - §4-2・K3d（design.md:151・38・142）: 分析が読む時刻は meta_messages.created_at・conversation_logs.occurred_at で、leads.created_at は読まない。範囲の決まりは状態だけで決まる。食い違いなし。○
2. **§6-1 の audit_logs の (a)(b) と K5②**: K5②（design.md:40 ②）は「書き込みを始めた時刻より後」の meta_message_sent・meta_message_send_failed（new_data の lead_id がテスト用リード）を書き込みの直後に 0件と判定する基準。§6-1 の (a) は消すときにそれを含めた件数を報告するだけで、消さない・判定しない。役目が別で食い違いなし。○（(b) の数え方の細かい点は補足2）
3. **SSOT**: 第6版は新しい表・列・写しを足していない。created_at・updated_at は leads の既存の列で、返信の速さは今までどおり leads に写さない。データを2か所に分ける箇所は増えていない。配線の SSOT（本物との違いを欄に全部書く design.md:57）は、④ の書き足しでむしろ揃った。○

## 項目4 前回まで ○ だった項目（差分の範囲）

- 統計（§3-2・§4-1・§4-2・K3）: 差分は design.md の 3〜9行（日付・状態・基準）と 39・41・61・66・69・131〜134・191・195・196・204・235 行だけで、§3-2 の表・時刻の作り方・§4-1・§4-2 には触れていない。崩れていない。○
- 画面（§4-3・K4）: K4 は書き足しだけ（レビュー役と置き場）。§4-3 は触れていない。○
- 安全（K5・§3-3・§6-1）: K5 の欄は変わっていない。§6-1 は止める条件と数え方を足しただけで、消す順番（手順2〜8）・目印・手順9 の id の突き合わせは同じ。手順1 の止める条件が増えたことで、元の行を消す道は狭まる向きだけ。○

## 項目5 実装カードに進めるか・§8

- §8（design.md:217〜221）: #1 は解決済み、#2 は今回要らないことの記録、#3 は解決済み、#4 は既存の委譲の決まり（PO 2026-09-30）に合わせた手順の記録。#5 は ①K の測り方の再確認（KGI の承認者としての確認）②こちらから営業したリードの「最初の返信」の測り方 ③欄の置き場 ④全テナントに出すか、public の表に1行書いて001だけに出すか、で、どれも事業・承認の判断。技術で決められる点は入っていない。○
- 実装カードに進める（APPROVE）。ただし PO 実装承認（§8 #5 の回答）はまだで、実装カードはその回答を受けてから書く（design.md:5 の状態どおり）。下の補足3件は実装カードで書き足す。

## 実装カードで拾う補足（APPROVE を止めない）

1. **leads.created_at を過去にしたことの画面への影響（§3-4 design.md:124）**: 第6版の理由は「新しいリード5件に並ばない」（`backend/app/tasks/dashboard.py:92`〜93。同じ読み方は `backend/app/routers/dashboard.py:176` にもある）。このほか、経路ごとの月のまとめ（`backend/app/routers/analytics.py:1716` の channels_summary）は leads.created_at の月で数える（1746行・1779行）ので、テスト用リードは書き込んだ月ではなく 180〜70日前の各月に入る。テナント001はテスト用なので止める理由にはならないが、§3-4 の「ダッシュボードの数字に 400件が入る」に「どの月に入るか」を書き足すとよい。
2. **§6-1 手順1 の③と (b) の数える範囲（design.md:196・191）**: 「audit_logs に merge_absorb・merge_delete の行があり record_id が 4・6」には時刻の条件が無い。書き込みより前に 4・6 が別のリードを統合した記録があれば、手順1 が止まる（止まる向きなので安全だが、PO への余計な報告になる）。本番にそういう行があるかは未確認。手順0 の「書き込みを始める時刻」より後に絞ると読みやすい。(b) も record_id が 4・6 の行をすべて数えると、元のリードを画面で直した update の行など、テスト用データと関係の無い行が入る。報告の件数は「書き込みを始めた時刻より後」に絞る、と書き添えるとよい。
3. **行の範囲のずれ（項目2 の1〜3）**: 実装カードに写すときに、webhook.py は 646〜657・546〜551、leads.py の付け替えは「説明文 3237〜3249」と書く。

## 見張りに止められた文面

審査の途中で、origin/main の leads.py を読み取りで検索した命令（検索の語に SQL の削除の語を含めた git show と grep の組み合わせ。書き込みは無い）が止められた。文面:

PreToolUse:Bash hook error: [[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0; exec bash "$CLAUDE_PROJECT_DIR/scripts/agent-hooks/cloud/dispatch.sh"]: BLOCKED(cloud): 'DELETE FROM' は不可逆操作です。クラウドでは行えません。手元で PO の承認を得て実行してください。

言い換えて流し直すことはしていない。その検索で見たかった「loser を消す行」は、説明文（`backend/app/routers/leads.py:3237`〜3249）と ADR-1049 18行で代わりに確かめた。消す処理の実際の行番号は未確認。
