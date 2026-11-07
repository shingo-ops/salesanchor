# 審査 — design-pool-reset.md と ADR-1070（接続の返却時に文脈を消す Bx）

- 役割: 設計の審査役（Architect）。読むだけ。製品コード・本番・secret には触っていない。設計書と ADR は直していない。
- 審査の対象: origin/release/s1-rls-pool-reset 45719882fe22c73ccd8a42284dc9df7fd80b2ce4 の docs/handoff/s1-rls-stage5/design-pool-reset.md・docs/adr/ADR-1070-pool-reset-on-return.md
- コードの基準: origin/main b2bf396323d25efb3a0b1dbc0629677308ba3271（2026-11-07 fetch）。設計の基準 170ff9612 との差を `git diff --stat 170ff9612 origin/main -- backend/app backend/requirements.txt scripts/lint_tenant_schema.py` で取ったら 0 件。行番号は両方で同じ。
- 未確認の扱い: 設計が引く SQLAlchemy の写し（/tmp/CC報告ファイル/xtenant/sqla/...）はリポジトリに無く、この審査では読めなかった。pip での取得も時間切れで止めた。

## 1. 照合表（§2・§4-1・§4-2 のフルパス:行番号と import）

| # | 設計の記述 | origin/main の実物 | 結果 |
|---|---|---|---|
| 1 | backend/app/database.py `engine = create_async_engine(DATABASE_URL, **_engine_kwargs)` | backend/app/database.py:33 | 一致 |
| 2 | §2 のコードが使う `event` | backend/app/database.py:1-5 の import は `os`・`AsyncGenerator`・`AsyncSession, create_async_engine`・`declarative_base, sessionmaker` だけ。`from sqlalchemy import event` は無い | **不一致（指摘 M1）** |
| 3 | _engine_kwargs と postgresql の分岐 | backend/app/database.py:19-32（`if DATABASE_URL.startswith("postgresql")` は :24） | 一致 |
| 4 | admin_engine は対象外 | backend/app/database.py:84 | 一致 |
| 5 | SQLAlchemy 2.0.38 | backend/requirements.txt:4 `sqlalchemy==2.0.38` | 一致 |
| 6 | 一時表・サーバー側カーソル 0 件の git grep | 同じ命令を origin/main で流して 0 件 | 一致 |
| 7 | pool_reset_measure.py:50-79 の Bx | docs/handoff/s1-rls-stage5/pool_reset_measure.py:50-65（`_handler`）・:75-76（`pool_reset_on_return=None`）・:79（`event.listen(eng.sync_engine.pool, "reset", ...)`） | 一致（形の差は指摘 R3） |
| 8 | dependencies.py:386-405 `clear_tenant_context` | backend/app/auth/dependencies.py:386-405 | 一致 |
| 9 | dependencies.py:281 is_operator を空に | backend/app/auth/dependencies.py:281 | 一致 |
| 10 | 起点1 ticket_channel_writer.py の commit :249・`if inserted_row is None:` | backend/app/discord_gateway/ticket_channel_writer.py:249・:251 | 一致 |
| 11 | 起点1 import :20 `from app.auth.dependencies import set_tenant_context` | backend/app/discord_gateway/ticket_channel_writer.py:20（set_tenant_context だけ） | 一致（reset を足す必要あり＝設計どおり） |
| 12 | 起点2 message_translator.py の commit :507・`logger.info(` の前・tenant_id :425 | backend/app/services/message_translator.py:507・:509・:425 | 一致 |
| 13 | 起点2 import 無し | backend/app/services/message_translator.py:17-42 に app.auth.dependencies の import 無し | 一致 |
| 14 | 起点3a calibrate_tenant_weights commit :250・`return weights`・引数 :160 | backend/app/services/priority_scoring.py:250・:251・:160 | 一致 |
| 15 | 起点3 import 無し（:11-20） | backend/app/services/priority_scoring.py に import 無しは正しい。ただし import の並びは :11-24（:20-24 が app.schemas.customer_priority の括弧） | 範囲の書き方がずれる（指摘 R2） |
| 16 | 起点3b label_lead_messages `if saved > 0:` の commit :313 | backend/app/services/priority_scoring.py:312・:313（tenant_id は :257） | 一致 |
| 17 | 起点3c _compute_and_persist commit :439・`return CustomerScoreResponse(`・引数 :386 | backend/app/services/priority_scoring.py:439・:441・:386 | 一致 |
| 18 | 3c が直す customer_priority.py `override_priority_score`（:64-115） | backend/app/routers/customer_priority.py:64 で始まり、commit :140・reset :142 の後 :158 の前まで続く | 範囲の終わりがずれる（指摘 R2） |
| 19 | 起点4 tenant_commission_settings.py `_create_default` の rollback :109・import :33 | backend/app/routers/tenant_commission_settings.py:109・:33 | 一致 |
| 20 | 起点5 products.py `delete_product` の rollback :706・`record_audit_log` の前・import :32 | backend/app/routers/products.py:706（間に :707 logger.warning）・:713・:32 | 一致 |
| 21 | 起点7 webhook.py `_create_outbound_lead_for_echo` commit :580・`return lead_id`・tenant_id :540・import :50 | backend/app/routers/webhook.py:580・:581・:540・:50 | 一致 |
| 22 | 2 の波及 conv_logs.py:136 → :145、tasks/translation.py:79、llm_budget.py:472・:524 | backend/app/routers/conv_logs.py:131-155（set :132・ensure :133・UPDATE :141-153）・backend/app/tasks/translation.py:74-85。llm_budget は m9 表A 行 13・14 の値をそのまま採用（本審査では開いていない） | conv_logs の行番号は m9 と 3 行ずれる（m9 由来・害なし） |
| 23 | §4-2 起点6 calendar_service.py:303・:306・:271-272・google_calendar の :293-294 | backend/app/services/calendar_service.py:303・:306・:271-272、backend/app/services/google_calendar.py:293-294 | 一致（理由の書き方は指摘 R8） |
| 24 | §4-2 起点8 refresh_meta_tokens.py :97-99 | backend/app/tasks/refresh_meta_tokens.py:97-99 `create_engine(DATABASE_URL, echo=False)` | 一致 |
| 25 | §4-2 起点9 verify_meta_subscriptions.py :82-84 | backend/app/tasks/verify_meta_subscriptions.py:82-84 | 一致 |
| 26 | §4-2 data_deletion.py:59 | backend/app/tasks/data_deletion.py:59 `create_engine(_ADMIN_DATABASE_URL, ...)` | 一致 |
| 27 | §4-3 notifications.py:166・:187、tcg_distribution_svc.py:1160-1184 | backend/app/routers/notifications.py:166・:187、backend/app/services/tcg_distribution_svc.py:1160-1184（tenant_id=4 は :1175） | 一致 |
| 28 | §4-3 discord_role_sync.py:112-130 | backend/app/services/discord_role_sync.py:112-131（commit :131） | 一致 |
| 29 | §4-3 tcg_product_import.py:484・:497 | backend/app/routers/tcg_product_import.py:484・:497。backend/app/services/ に tenant_context の名前のファイルは 0 件 | 一致 |
| 30 | §4-3 product_packagings.py:164・:174・:203 | backend/app/services/product_packagings.py:164・:174・:203 が `await db.execute(` | 一致 |
| 31 | §4-3 webhook.py:125・:219・:106 | backend/app/routers/webhook.py:106・:125・:219。:125 に来るのは :109 の except の後だけ（該当行なしは :108 で return None） | 一致 |
| 32 | §7 R2 の写し /tmp/CC報告ファイル/xtenant/sqla/base.py:1006-1012、§2 の pg_base.py:265-284、§10 の base.py:1405-1432 | リポジトリに無い | **未確認**（指摘 R4） |

## 2. m9 の振り分けの漏れ

| m9 の項目 | 設計の行き先 | 結果 |
|---|---|---|
| BREAK-新 起点1〜5・7 | §4-1（1・2・3a/3b/3c・4・5・7） | 有り |
| BREAK-新 起点6・8・9 | §4-2 | 有り |
| BREAK-既 起点1〜5 | §4-3（1・4・2・5・3） | 有り |
| BREAK-既 6 番目（data_deletion・m9 では「参考」） | §4-2 | 有り |
| 表B B1（BREAK-新） | §4-1 の 2 にまとめる | 有り |
| 表B B2・B3（要確認） | §4-4 U2（要確認 84 行）に含む | 有り |
| 表B B4 | §4-3 | 有り |
| U1〜U7 | §4-4 | 7 件とも有り |

漏れは無し。

## 3. §4-1 を直した後に、文脈なしで RLS 表・tenant 表に触る文が残るか

| 起点 | commit・rollback | その後の文 | 結果 |
|---|---|---|---|
| 1 | :249 commit → reset を足す | :280 INSERT・:311 UPDATE（文脈あり）→ :328 commit の後は `enqueue_inbound_translation`（db を使わない）と return。:329 except は rollback 無しで抜けるだけ。customer_reply_notifier は別 session で backend/app/services/customer_reply_notifier.py:45 が set、:71-72 が rollback の後に reset | 残らない |
| 2 | message_translator.py:507 commit → reset を足す | ensure_inbound_translations の 2 回目以降の translate_inbound（:541・:553・:562・:573・:584）、conv_logs.py:141 UPDATE → :154 commit・:155 reset、tasks/translation.py:85 finally で clear。generate_outbound_draft の :645 commit の後は db を使わず、呼び元 backend/app/routers/translation.py:166 が reset。leads.py:1434 の translate_message も 2 の直しでかかる | 残らない |
| 3a | :250 commit → reset | すぐ return | 残らない |
| 3b | :313 commit → reset | 呼び元 _compute_and_persist の :391・:392 以降、customer_priority.py:169 の SELECT | 残らない |
| 3c | :439 commit → reset | 呼び元 customer_priority.py:88 の SELECT・:104 の UPDATE・:128 の監査 → :140 commit・:142 reset → :143 get_or_compute_score。recalculate は :283 で reset | 残らない |
| 4 | :109 rollback → reset | :111 `_fetch_settings`（文脈あり） | 残らない |
| 5 | :706 rollback → reset | :713 record_audit_log → :719 commit・:720 reset。:723 rollback の後は raise だけ | 残らない |
| 7 | :580 commit → reset | webhook.py:832 write_conversation_log → :844 commit・:845 reset | 残らない |

例外の側（webhook.py:846・conv_logs.py:157 など rollback しない except）は取引が中断状態になるだけで、Bx の有無で結果が変わらない（設計 §9 の別件と同じ）。

## 4. 指摘

| ID | 重さ | 指摘 | 根拠 | 直し方 |
|---|---|---|---|---|
| M1 | 必須 | §2 のコードは `event.listen` を使うが、`event` の import を足すことが書かれていない。このまま入れると import の時点で NameError になり、backend・celery・discord-gateway が起動しない | backend/app/database.py:1-5 に `from sqlalchemy import event` が無い。測定台本は pool_reset_measure.py:18 で import している | §2 の変更後のコードに `from sqlalchemy import event` を足す行を明記する |
| M2 | 必須 | §5 便2 の試験 (1)(2)(3) と K4・「維持の仕組み」の「Bx を外すと CI が赤」が、今の書き方では成り立たない。pytest は app.database の import より前に DATABASE_URL を SQLite に差し替えるので、`app.database.engine` は SQLite で listener が付かない。(1) の `event.contains(engine.sync_engine.pool, ...)` は False になる。(2)(3) の「CI の postgres」に繋ぐ engine の作り方も書かれていない | backend/tests/conftest.py:17-18 `os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"`。CI の postgres は .github/workflows/test.yml:121-127 と :234 の `RLS_TEST_DATABASE_URL`（salesanchor_app 役）で使える | database.py に「engine を受け取って `pool_reset_on_return` 相当の listener を付ける関数」を切り出す形にし、試験は RLS_TEST_DATABASE_URL から作った engine にその関数を当てて (1)〜(3) を確かめる（無いときは skip ではなく CI の必須ジョブで必ず流れることを書く）。本体の engine に付いていることは「DATABASE_URL が postgresql のとき関数を呼ぶ」ことを別の試験（monkeypatch した URL で app.database を読み直す等）で確かめる |
| M3 | 必須 | K1〜K3 の基準値（中央値 1081.5ms・p95 1207.3ms・0 件・18 件／約 65 分）と、その取り方（health_base.txt・docker logs の grep の命令）がリポジトリに無い。「同じ台本で」「同じ取り方」と書いてあるが再現できず、配備後に同じ物差しで判定できない。K2 は「4 つとも 0 件」とあるが数える文字は 5 つ、コンテナは 4 つで、何が 4 なのか読めない | `git grep -n health_base origin/release/s1-rls-pool-reset` は設計の 1 行だけ。基準値の数字は design-pool-reset.md 以外のファイルに無い | 台本（読み取りだけの命令）と生の出力を docs/handoff/s1-rls-stage5/ に置き、K1〜K3 から参照する。K2 は「文字 5 つ × コンテナ 4 つ、各 0 件」のように表で書く |
| M4 | 必須 | ADR と設計で、便1 の直す箇所の数が合わない。ADR は「7 か所」、設計 §4-1 の表は 8 行（1・2・3a・3b・3c・4・5・7）で起点は 6 つ。設計 §3 の表も「7 か所」 | docs/adr/ADR-1070-pool-reset-on-return.md:18・:26、design-pool-reset.md:55 と :69-78 | 「6 起点・8 か所」に揃える（ADR と設計 §3 の両方） |
| R1 | 推奨 | §8「戻し方」と §9「触らない範囲・後続」が 2 回ずつあり、中身が違う（2 回目は §4-3 と R4・Rule C の行が無い） | design-pool-reset.md:149-159 と :161-169 | 後ろの §8・§9 を消す |
| R2 | 推奨 | 行の範囲の書き方が 2 か所ずれる | priority_scoring.py の import は :11-24（照合表 15）。override_priority_score は :64-115 でなく :64 から :142 の reset・:158 の手前まで（照合表 18） | 範囲を直す |
| R3 | 推奨 | §2 は「測った形から変えない」と書くが、cursor を try/finally で閉じる点と、関数を名前つきにする点が測定台本と違う。動きは同じと見られるが、文と食い違う | pool_reset_measure.py:58-64 は try/finally 無し | 「cursor の close を finally に入れたことだけ違う」と書き添える |
| R4 | 推奨 | SQLAlchemy の挙動の根拠（reset イベントが `pool_reset_on_return=None` でも呼ばれること、reset 中の例外で接続が invalidate されること、公式の例の順番）が /tmp の写しにしか無く、審査で確かめられない。挙動そのものは m1・m6・m7 の実測で裏付けがある | 照合表 32 | 写しの該当部分を docs/handoff/s1-rls-stage5/ に置くか、上流の 2.0.38 タグの URL と行を書く。§2 の pg_base.py と §10 の base.py の呼び方も揃える |
| R5 | 推奨 | BREAK-既1（配信失敗の Discord 通知）を「notification_logs が全期間 0 行だから一度も動いていない」とした根拠が弱い。Discord への送信は記録の INSERT より前に行われるので、INSERT だけが失敗していれば送信は起きていて記録が 0 行になり得る | backend/app/routers/notifications.py:185（送信）→ :187-194（記録）→ :195 の except は warning だけ | 本番の tenant_004.notification_channels で `is_active` かつ event_types に tcg_distribution_error を含む行の数を reader 鍵で読み、0 行なら「Bx の前後で送信は起きない」と書き足す。1 行以上なら便1 に入れるか PO に先に知らせる |
| R6 | 推奨 | message_translator.py の先頭に `from app.auth.dependencies import reset_tenant_context` を足すと、message_translator を読むだけで app.database（engine の作成）も読まれる。llm_budget はこれを避けて関数の中で import している。message_translator は scripts/lead_regression/generate.py:27 からも読まれる | backend/app/services/llm_budget.py:413 のコメント、backend/app/routers/conv_logs.py:129 の関数内 import | 起点2（と 3）は関数の中で import するか、設計 §4-1 の python -c に `scripts/lead_regression/generate.py` を読む確認（backend/tests/test_lead_regression_generate.py が緑）を足す |
| R7 | 推奨 | 便1 で reset を足すと、db を MagicMock にした単体試験では `_dialect_supports_search_path` が postgresql 扱いになり、execute の回数・順番を数える試験が変わる可能性がある（未確認） | backend/app/auth/dependencies.py:295-299 は bind.dialect.name を見るだけ | §5 便1 の「既存の単体試験が全部緑」の前に、test_message_translator*.py・test_ticket_channel_translation.py・test_customer_reply_notifier.py ほか該当関数の試験を実装役が流すと明記する |
| R8 | 推奨 | §4-2 起点6 の理由が「:303 の commit が失敗した後の except 側」だけになっている。except は Google API の失敗（cal_svc.create_event の例外）も受ける。その場合は :272 か google_calendar.py:294 の reset の後なので文脈はあり、結論（直さなくてよい）は変わらない | calendar_service.py:278-312 | 理由に「try の中の commit は :303 以外すべて reset が続く（:272・google_calendar.py:294）ので、except に来たとき文脈が無いのは :303 の commit 自体が失敗した場合だけ」と書く |
| R9 | 推奨 | K2・K3 の基準値は約 65 分の窓で取り、判定は配備後 24 時間。長さが違うので、Bx と関係なく 24 時間のうちに出る既存の失敗で K2 が × になり得る | design-pool-reset.md:133-134 | 配備前の 24 時間で同じ数え方の基準値を取り、K2 は「基準値から増えない」にするか、既存の行を除く条件を書く |

## 5. 確かめることごとの結論

1. 行番号・import の照合: 32 件中、合わないのは 1 件（M1・event の import）。範囲がずれるのが 2 件（R2）。確かめられないのが 1 件（R4）。
2. m9 の振り分け: BREAK-新 9・BREAK-既 6・U1〜U7・表B の B1〜B4 に漏れは無い。
3. §4-1 を直した後: 同じ関数・呼び出し元に、文脈なしで RLS 表・tenant 表に触る文は残らない（§3 の表）。
4. Bx のコードと測定台本・database.py: 形は台本と同じ（差は R3）。database.py に入れるには `event` の import が要る（M1）。_engine_kwargs への足し方は今の database.py:19-33 と合う。
5. §6 の受入条件: K4 は今の試験の書き方では満たせない（M2）。K1〜K3 は基準値と取り方がリポジトリに無く、同じ物差しで再現できない（M3）。K5・K6 は ○× で判定できる。
6. 便1 だけ入った状態: 足すのは「同じ要求・同じ会社の文脈を、commit・rollback の後に張り直す」だけで、§3 の表のとおり後ろの文の文脈は同じ値になる。害は見つからなかった（import の副作用の注意だけ R6・R7）。
7. ADR と設計の食い違い: 直す箇所の数（M4）。それ以外の決定（engine の範囲、順番、2 便、触らない範囲）は一致。

## 6. 判定

**REVISE**

必須 4 件（M1〜M4）を直せば実装へ進めてよい。直した後の審査は、M1〜M4 の差分だけを見れば足りる。
