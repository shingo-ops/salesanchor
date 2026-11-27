# 便0-B 7回目の結果の確かめ（Opus・2026-11-28）

対象: origin/release/ai-assistant-bin0b c4588a66a（DONE）。生の記録は同じ枝の docs/handoff/ai-assistant/bin0/out/。

## 1 K2（下書きの形）25/48 の原因

【事実】
- 種類ごとの数（b-main.tsv を集計）: invoice 24件 形○4・やり直し22・K3 0/42。event 24件 形○21・やり直し7・K3 35/39。unknown・rule 21件は係に回らず形の検査の対象外。
- 今の秘書は形の表 `secretary-agent/schema.json` を AI に渡している（`secretary-agent/server.mjs:70` `"--json-schema", SCHEMA`）。
- Hermes の試しでは形の表を渡していない。係の部屋の人格は `secretary-agent/prompt.txt` の写しだけ（`bin0/setup_profiles.sh:25`）。頼みの本文にも形の表は無い（`bin0/run_bin0.py:106` の body は model・provider・stream・messages だけ）。
- prompt.txt の1行目は「出力は指定された JSON の形だけです」だが、その「指定」は今の秘書では --json-schema が担っていた。
- 形の表の欄の名前が prompt.txt に出てくる回数（grep -c -w）: 請求書の欄 company_name 0・contact_name 0・items 0・product_name 0・quantity 0・notes 0・unit_price 1・due_date 1。予定の欄 title 2・end 1・is_all_day 1・location 1・description 1・is_meeting 1・add_meet 1。
- 請求書の欄の名前はほぼ書かれておらず、予定の欄の名前はほぼ書かれている。これは「請求書だけ形が外れ、K3 も 0」と並びが合う。

【未確認】
- 外れた下書きの中身（頼みと答えの中身は出さない決め）。欄の名前違いが本当の原因かは、形の表を渡して流し直して確かめる。

【原因の区分】設計とカードで、形の表を Hermes へ渡す手順を入れ忘れた（design.md §5:95「返す形は schema.json」と書いたが、渡し方を決めていない）。

## 2 K7（残らない）の原因

【事実】（raw/b8-k7.txt）
- 頼みの文が残った場所: 3部屋それぞれの logs/agent.log（文の種類 coordinator 28・invoice 8・calendar 14）と state.db・state.db-wal（会話を消す口が 200 を返した後も）。
- skills/.../templates/plugin.js の当たりは、部品の中の文字に短い頼みの文が当たった可能性がある（未確認）。
- 会話を消す口は 146/146 と 15/15 で 200 を返した（b-main.err・b-k4.err）。

【事実（説明書・Context7 /nousresearch/hermes-agent・main の版。v0.23.4 で同じかは未確認）】
- state.db の空き場所を詰め直す命令は `hermes sessions optimize`（VACUUM）。動いている間は断る作り。
- state.db の書き方は `database.journal_mode`（wal か delete）で選べる。
- agent.log に頼みの文を書かせない設定は、説明書では見つけていない（未確認）。

## 3 PO の問い「会話を残すと精度は上がるか」

【事実】
- 今の設定では、Hermes は残った会話を使わない。覚え書きと振り返りを止めている（bin0/config.yaml:12-20）。残っても精度には効かない。
- 秘書の育て方は既に決まっている。ADR-1077: 人が承認した「決まり帳」を会社ごとの DB に置き、決まりを足すたびに 20 件の試しを流して数を残す。
- 同じ ADR-1077:18「会話の全文は残さない。残すのは候補・決まり・『違う』の元になった 1 往復だけ」。
- LINE解析は正解表を本番 DB の表に置き、測って直す（ADR-1043）。どちらも「正解と結果をアプリの DB の1か所に置く」形。
- Hermes の中に会話を残すと、同じ会話がアプリの外にもう1か所できる（データの分散）。

## 4 次の手（案）
- K2: 形の表を係の部屋に渡す（人格に形の表を書き足す、または頼みに response_format を付ける。F4 は効くか未確認）。流し直しで確かめる。
- K7: 本物の完成品の中で、agent.log に文を書かせない設定と、state.db の消し残りを無くす手を調べる。無ければ記録の置き場を容器の再起動で消える場所にする案を比べる。
- どちらも流し直しに 3 部屋のログインが要る。

## 5 Hermes の中身の調べ 1回目（8ac22615c・out/source-check-b.md）の Opus の読み
- 【事実】形の強制の口は無い（response_format・json_schema は読まれない）。文章で渡せるのは system メッセージだけ（openai_routes.py:710-733・:950）。→ K2 の直しは「schema.json を元に system メッセージを毎回作る（写しを作らない）＋アプリ側の検査とやり直し1回」。69/69 に届くかはログインして測るまで未確認。
- 【事実】agent.log は logging.level: WARNING で目印 1→0（単一部屋の実測）。3部屋を1つの動き手で持つ形で効くかは未確認。
- 【事実】state.db は消しても残る。VACUUM と secure_delete=ON で 0（各1回）。secure_delete の設定の鍵は無い。動いている間の optimize は未確認。
- 【事実】部品の当たりは 23 文中 1 文（5字）・1 ファイル。前回 4 件との差は未確認。
- 【事実】消した後も残る使った量の総計は Hermes に無い。→ K9 はアプリ側で返事の usage を積む形で測る。
- 2回目の調べ（cse_01HHUUpS4GeqR4waowp66SF6）: 保存しない指定の有無・動いている間の VACUUM・3部屋での WARNING の効き・ログイン無しの通しの試し。

## 6 2回目の調べ（319df23fe・out/source-check-b2.md）の Opus の読み
- 【事実】chat completions の頼みを保存しない口は無い（Q6 ×）。AIに届かず失敗した頼みも state.db-wal に保存される（実測 4 行）。
- 【事実】部屋ごとの logging.level は効かない（Q8 ×・実測 INFO 行が既定と同じ）。効くのは起動側 /opt/data/config.yaml とソースの読み（未実測）。
- 【事実】動いている gateway がいると optimize は断られる。止めてから optimize で 538 ファイル全部 0 行（各1回）。
- 【事実】自動 VACUUM は 90 日超の会話を消した回に限るため、消した直後の消去には使えない。
- 【未確認】AI が答えるときに agent.log に頼みの文が出るか（今回は失敗が早く届かず）。
- 3回目の調べ（cse_01HHUUpSJzB697wb92DbHUD3）: 起動側での WARNING・動かしたままの optimize --force・止めて詰め直して起こす秒。

## 7 3回目の調べ（1ce1a63ed・out/source-check-b3.md）の Opus の読み
- 【事実】起動側に logging.level: WARNING を書いても agent.log の INFO は減らない（238 行）。理由は未確認。
- 【事実】動かしたまま optimize --force: 終了0・目印0・直後の送信 200・gateway 落ちず（各1回）。ソースのコメントは稼働中の実行を危ない側に分類（sessions_cmd.py:1473）。→ 設計では使わない。
- 【事実】止めて別の使い捨て容器で optimize → 起こす: 目印0・stop から /health 200 まで 29.8 秒。
- 【未確認】AI が答えた回に agent.log に頼みの先頭80字が出るか（全回で失敗が早く届かず）。
- 4回目の調べ（cse_01HHUUpSbZpiCanaGKuJvyX3）: 容器の中に作り物の AI を置き、成功の回のログを実測。ログを止める手を全部当てる。vacuum() の中身。

## 8 4回目の調べ（e23f3a54a・out/source-check-b4.md）の Opus の読み
- 【事実】3回目に WARNING が効かなかった理由: README 手順3の守り（DAC_OVERRIDE 無し）では起動のたびに /opt/data/config.yaml がひな形で上書きされる（docker/stage2-hook.sh:438-447・実測 133740 バイト・logging 0 行）。→ 起動側に置いた設定（memory off 等）も起動側では効いていなかった。部屋側の config は無傷。
- 【事実】管理者の固定設定 /etc/hermes/config.yaml（読み取り専用で差し込み）に logging.level: WARNING → 守りのままで invoice の agent.log の目印 0 行（E2・1回）。根拠 hermes_cli/managed_scope.py:31・hermes_logging.py:1051-1068。
- 【事実】頼みの先頭80字の行は agent.turn_context・INFO・ターンごとに無条件（turn_context.py:1290）。作り物の AI で成功の回に invoice の agent.log へ 1 行出た（E0）。
- 【事実】環境変数・起動の引数・logger 名ごとの level では止められない。tmpfs は RAM 上に書くだけ。
- 【事実】E2 の形で DELETE → stop → 別の使い捨て容器で optimize → start → 全 545 ファイルで目印 0 行（1回）。DELETE 無しだと 2 行残った。
- 【未確認】0 が optimize の効果か stop だけの効果か。1回の送信で AI へ 2 回届く中身。system メッセージが AI へ届く位置。消す前に Hermes から使った量を読めるか。固定設定に置いた他の鍵が 3 部屋で効く値。
- 5回目の調べ（cse_01HHUUpQmJfAfTEJfvfyzFzN・2026-11-28）: 上の未確認を作り物の AI で 3 部屋通して実測（Q13〜Q16・stop 直後の数え）。

## 9 5回目の調べ（e964c56b8・out/source-check-b5.md）の Opus の読み
- 【事実】1回の送信で AI へ 2 回届いた 2 回目は会話の題づけ。固定設定で auxiliary.title_generation.enabled: false にすると 1 回（Q13）。題の外の確かめの呼び出し（GET models・POST /api/show）は残る。agent.auxiliary_client の WARNING が 1 種出た（どの補助の呼び出しかは未確認）。
- 【事実】頼みの system メッセージは部屋の人格の後ろに改行 2 つでつながって AI に届く。人格を置き換えはしない（api_server_openai_routes.py 719-726 行目・chat_completion_helpers.py 2096-2097 行目・Q14）。→ K2 は schema.json から毎回作る system 文で渡す。
- 【事実】使った量は消す前に GET /p/<部屋>/api/sessions/<番号> の input_tokens・output_tokens・api_call_count で読め、返事の usage と一致（11/7・1回・Q15）。/health/detailed の数は 0 のままで使えない。
- 【事実】固定設定に置いた鍵（memory・user_profile・toolsets・background_review・fallback・title・logging）は 3 部屋とも思った値で表示（Q16）。固定設定なしの比べでは title true・logging INFO。
- 【事実】3 部屋通し: 目印 消す前 21／消した後 27／止めた後 27／詰め直し後 0／起こした後 0。→ 0 は詰め直し（optimize）の効果で、止めただけの効果ではない。止めてから /health 200 まで 47.4 秒（詰め直し 3 回込み）。
- 【未確認】optimize -p が部屋ごとの箱だけを詰めるか（3 回の後にしか数えていない）。消した後に使った量を読む道。長い詰め直しとのぶつかり。
- → 設計書を第2.6版へ直した（K2・K7・K9 の検証方法・§5・§9）。
