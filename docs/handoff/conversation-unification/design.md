# 会話の表を会社の中で1つにまとめる — 設計（KGI は PO 承認済み・設計審査3回目 APPROVE）

> この文書は何か（1行）: 会社ごとに2つある会話の表を meta_messages の1つにまとめ、全会話を必ずリードに結ぶまでの手順。
> 現在地: [recon.md](recon.md)。上位: docs/specs/db-ssot/conversation-unification/design.md・docs/specs/db-ssot/ideal-state.md。関連 ADR: ADR-106・ADR-096・ADR-110・ADR-1049・ADR-136・ADR-1003。

## 1. 目的（PO から見て変わること）
- 会話の記録が、会社ごとに1か所だけになる。
- 受信箱で手で記録した会話が、同じ会話の流れに並ぶ。
- 持ち主（リード）の無い会話が、保存できなくなる。

## 2. KGI（PO 承認 2026-11-07「1」: 問い「この5つで承認する【おすすめ】」への答え）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 全会社で会話の表が1つ（conversation_logs が 0 表） | 本番 `information_schema.tables` で table_name='conversation_logs' の数が 0 |
| K2 | 便1 反映後 24 時間で、conversation_logs に新しく入った行が 0 | 本番 ai_ro で created_at > 反映時刻 の数 |
| K3 | 受信箱で手で記録した会話が、その相手の会話の流れに出る | PO が本番画面で1件記録して目視（○×） |
| K4 | リードの無い会話が 0 件で、空のまま入れようとすると止まる | 本番の数 0 ＋ CI の試験で NOT NULL 違反を確認 |
| K5 | 数字が変わらない: 成約分析・週次の助言・会社詳細の会話タブ・会社の会話数と最終会話日（v_company_stats）・言語判定の結果が便1の前後で同じ | 反映前に基準値を取り、反映後に同じ問いで比べる（差 0）。下見は recon §8-4。言語判定は画面が使う値（確定か・確定のときの言語。useInboxState.ts:723）で比べる（recon §8-6） |

## 3. 対象と対象外
- 対象: §4 の3便。
- 対象外: 全社1つ（public）への移動（PO 2026-11-07 不採用）。会話の取り込み（conversation-import）は便1 の後に別に進める。meta_messages の表名の変更。

## 4. 進め方（1便ずつ「出す→本番で確かめる→次」）
### 便1 書く所と読む所を meta_messages だけにする（表の形は変えない。集計ビューだけ作り直す）
- 写しをやめる: webhook.py:832・:877、dm_writer.py:233 の write_conversation_log 呼び出しを外す。
- 手の記録を meta_messages へ: conv_logs.py の作成・取得・変更・削除を meta_messages に向ける。API の形（URL・返す項目）は変えない。入れる値:
  - is_manual=true・recorded_by_user_id・occurred_at（画面の入力）・created_at（= occurred_at）・platform（= channel_type）・direction・message_text（= content_text）。
  - created_at を occurred_at にそろえる理由: 会話の流れは created_at の順（leads.py:1018・:1037）、成約分析は meta 側を m.created_at で読む（analytics.py:2496）。今の手の記録は occurred_at で読まれている（analytics.py:2515）。そろえれば、昨日の電話を今日記録しても流れの正しい位置に並び、成約分析の時刻も今と同じになる（recon §8-6）。
  - 変更 API（今の conv_logs.py:377 付近）で occurred_at を直すときは、created_at も同じ値に直す。
  - 消すときは今と同じ「消した印」（deleted_at）を付ける。行は残す（今の conv_logs.py:440 と同じ・監査の記録も今と同じ）。
  - sender_id = `'manual:user_' || recorded_by_user_id`（空を許さない列。前例は recon §8-2）。sender_name は空。
  - message_id = `'manual_' || 新しい uuid`（訳のキー。一意）。
  - company_id・contact_id は今の手の記録と同じ補い方（conv_log_writer.py:117-150 の関数を使う）。
  - 訳は message_translations だけに置き、translated_text の写しをやめる。
- 手の記録を「自動連携の行」として扱わない（recon §8-3）。次の所に `is_manual IS NOT TRUE` を足す:
  - 送信の宛先 leads.py:1834-1844。24時間の窓 leads.py:1119-1128。最新の窓口 leads.py:1102-1112（messages[-1] を使う枝も手の記録を飛ばす）。
  - 受信箱の一覧 meta_inbox.py:920-947 の latest と agg（宛先・未読数・最後の受信時刻に効くため）。
  - 翻訳の見張り translation_monitor.py:80-90。
  - 画像の送信 leads.py:2453-2460（直近 inbound の sender_id・platform で送り先を決める）。
  - 未読に戻す leads.py:1300-1310（直近 inbound の1行を選ぶ）。
  - 本文のラベル付け priority_scoring.py:268。今は手の記録が入っていない。担当が書いた要約は相手の言葉そのものではないので、今と同じく入れない（言語判定で電話・対面を外すのと同じ考え）。
  - 会話の流れ（leads.py:963 から始まる取得）には手の記録も出す（K3）。
- 消した印の付いた行を出さない（recon §8-6。leads.py・meta_inbox.py には今 deleted_at の条件が1つも無い）。`deleted_at IS NULL` を次に足す:
  - 会話の流れ leads.py:1010-1040 の2つの取得（添付列ありと無しの両方）。
  - 新しく meta を読む所（companies.py の会話タブ・v_company_stats）にも付ける。analytics.py・lang_judge.py は付いている。
  - 上の除外リストの所は手の記録を読まないので、消した印の条件は要らない。
- 影響なしと確かめた所: 既読 leads.py:1207（未読数は手の記録を数えない）、訳 leads.py:1412・添付の取り直し :1567（message_id で1行を指す）、Discord の反応 reaction_writer.py:115・discord_reactions.py:107（Discord の行だけ）。
- 読む所を meta_messages へ: analytics.py:2257・:2516、companies.py:1104（訳は message_translations から）、lang_judge.py:85・:123、scripts/lead_regression/generate.py:502・:517、smoke [7e]。
- 言語判定 lang_judge.py は meta_messages だけを読む。今 conversation_logs 側に付いている「文字が原文でない窓口（電話・対面）を外す」条件（lang_judge.py:33-37 `_NOT_VERBATIM_CLAUSE`）を、meta の platform で付け直す。付けないと、手で記録した電話の会話が多数決に入る。
- 集計ビュー v_company_stats を meta_messages で作り直す migration を足す（company_id で結ぶ。最終会話日は occurred_at、空なら created_at。消した印の行は数えない）。migrations/ を含むので危険 PR の手順（ADR-135・ADR-136）。表を消す操作は含まないので ADR-1003 の例外には当たらない。
- 名簿の conversation_store を全窓口 meta_messages にする（値の変更は seed の決まりに従う。詳細はカードで決める）。
- 毎朝の突合（celery_app.py:151-157・sa02_recon_monitor.py）を外す。逆向きの台本2本と、その試験を消す。
- リード統合の一覧 leads.py:3014 の conversation_logs は便3 まで残す（外すと統合が止まる。recon §8-5）。
- 試験: 手の記録が meta_messages に入り、会話の流れの API に出ること。写しが書かれないこと。手の記録が最新でも、送信の宛先・画像の送信の宛先・未読に戻す行・24時間の窓・受信箱の一覧の宛先と未読数が変わらないこと。消した手の記録が流れに出ないこと。過去の時刻で記録した手の記録が、流れのその時刻の位置に並ぶこと。あとで時刻を直した手の記録が、直した時刻の位置に並ぶこと。本文のラベル付けに手の記録が入らないこと。電話の手の記録が言語判定に数えられないこと。
### 便1.5 アプリから直接送った返信も受信箱に出す（KGI K6〜K9 は PO 承認 2026-11-07「1」: 問い「この4つで承認し、第一段階のすぐ後の段階として作る【おすすめ】」への答え。設計審査は便1.5 のカードの前に別に受ける）
PO 要件（2026-11-07 原文）: 「Messangerに限らず、受信箱で送受信管理している連絡媒体は全てに適応させる要件定義として、SAアプリでなく直接スマホアプリ等から返信を返しても受信箱に表示させる」。PO 選択「2. 今回から新しいノートに残す」。
- 窓口ごとの今（recon §9）:
  - Messenger: 受け取りの解析はある（webhook.py:369-386 の is_echo）。ただし購読の既定 meta_graph.py:45-52 に `message_echoes` が無い。本番の購読記録にも無い。Meta 公式の購読項目一覧に `message_echoes`（"A notification is sent when your business has sent a message."）がある。
  - Instagram: Meta 公式の Instagram 版の説明では、返信の写しは `messages` の購読で `is_echo` 付きで届く。解析 A 形式は受ける。B 形式（webhook.py:421-423）は捨てている。
  - Discord チケット: スタッフが Discord で直接書いた文は捨てている（ticket_channel_writer.py:208-216 「non-customer message ignored」）。アプリからの送信は Discord の webhook で担当の名前を使って送る（leads.py:2246-2270 ADR-159）。届いた写しは webhook_id 付きなので :199 で飛ばしている。直接書いた文と区別できる。
  - Discord DM: 受け取り自体を全部飛ばしている（client.py:432-435 ADR-146 F7）。受信箱の窓口ではないので対象外。
  - WhatsApp・電話・対面: 自動の連携が無い（名簿で manual）。手の記録で残す。WhatsApp の連携が付いた時に同じ型を当てる（whatsapp-intake で扱う）。
  - 本番の Meta 接続: 全社で有効 0 件（各社 tenant_meta_config の is_active 数 0）。本番で直接の目視は接続を付け直すまでできない。
- 変更（すべて meta_messages だけに書く。conversation_logs には書かない）:
  - 返信の写し（echo）を meta_messages に outbound で入れる。`ON CONFLICT (message_id) WHERE message_id IS NOT NULL DO NOTHING`。echo の app_id が自社アプリ（META_APP_ID）なら入れない（アプリから送った分は送信の処理が既に入れている。二重を防ぐ）。
  - アプリの送信の INSERT（leads.py:2086・2346・2532/2552・2843/2863）にも同じ ON CONFLICT を付ける（写しが先に届いても送信が失敗しない保険）。
  - 購読の既定に `message_echoes` を足す。既存の接続は付け直しで反映（接続画面の操作。PO の作業）。
  - B 形式の echo も A 形式と同じく outbound で受ける。→ **カード便1.5 で絞り込み（2026-11-09 Opus）**: B 形式（changes[]）の写しは今までどおり捨て、ログを1行残す。理由: Meta 公式の説明に B 形式の写しの形が無く、お客さんの id の場所が分からない。Instagram の写しは A 形式（messaging[]）で届くと公式に書かれている（webhooks/examples）ので K7 は満たせる。
  - アプリの送信の INSERT は **DO NOTHING ではなく DO UPDATE**（sent_by_staff_id 等を書き足す）にする（カード便1.5 §2 の (2)・2026-11-09 Opus）。理由: RETURNING の行が無いと古い SQLite 用の2回目の INSERT（leads.py:2101-2121 ほか）に進み、写しが先に入っていたとき重複で送信が 500 になるため。
  - `_create_outbound_lead_for_echo`（webhook.py:537-581）の窓口の決め打ち "messenger" を、届いた窓口にする。
  - Discord チケット: bot でも客でもない人の文を outbound で入れる（sender_name はその人の表示名）。
- 便1 との関係: 便1 で webhook.py:832 の写し先を外すとき、echo の行き先はこの便で meta に付け直す。echo は購読が無いため本番で今まで 0 件（recon §8 p10）なので、便1 と便1.5 の間に失う返信は無い。
- KGI（PO 承認済み）:

| # | 基準 | 検証方法 |
|---|---|---|
| K6 | Messenger のスマホアプリまたは Meta Business Suite から送った返信が、その相手の会話の流れに1件だけ出る | 接続後、PO が1通送り本番画面で目視（○×）。CI では記録した echo の形で試験 |
| K7 | Instagram アプリから送った返信が、同じく1件だけ出る | K6 と同じ |
| K8 | Discord のチケットチャンネルにスタッフが直接書いた返信が、1件だけ出る | PO が1通書き本番画面で目視（○×）＋ CI 試験 |
| K9 | アプリから送った返信が二重に出ない | 送信1通につき meta_messages の行が1（本番 ai_ro で message_id の重複 0）＋ CI 試験（写しが先・後の両方） |

### 便2 lead_id を必須にし、リードを消すときは止める（migration・危険 PR）
- 先に、リード無しの1件（会社4 id=14・2026-05-14 の英文の問い合わせ）の扱いを PO が決める。
- `ALTER COLUMN lead_id SET NOT NULL`、FK を ON DELETE RESTRICT に替える（ADR-1049 の統合は付け替えてから消すので止まらない。recon §8-5）。
- data_deletion.py:116（利用者の削除依頼で meta_messages を消す処理）はリードを消さないので RESTRICT に当たらない。カードで実物を確かめる。
### 便3 conversation_logs を消す（DROP TABLE・ADR-1003 の例外で PO 本人の「GO #番号」）
- 7日間エラー0 と K2=0 の後。控えは直前に ai_ro から取る（PR-C と同じ型）。
- 同じ PR で片付ける: リード統合の一覧 leads.py:3014、conv_log_writer.py、AI 読み取りの伏せ字の決まり（migrations/20261024_100300_create_ai_cloud_views.sql:387-395・:613 の conversation_logs 行）、migration-test.yml・rls_bootstrap.py・conftest.py と試験、openapi.json、e2e、run_all_migrations.sh の該当行（recon §8-1）。
- 名簿の conversation_store 列も、読む所が無くなったら消す（列を消す操作も PO 本人の GO）。

## 5. 代替案
- A 全社1つ（public）: 不採用（PO 2026-11-07。リードとの FK が張れない・守りが RLS の書き方だけになる）。
- B conversation_logs を正本にする: 不採用。conversation_logs だけにある会話は 0 件で、受信箱・送信・既読・添付が meta_messages を読む（recon §2・§3）。
- C 2つのまま取り込みだけ進める: 不採用（PO 2026-11-07）。

## 6. リスクと対処
- 便1 で数字が変わる: K5 の基準値を先に取り、差が出たら止める。
- 手の記録の ID が変わる（conversation_logs.id → meta_messages.id）: 画面が持つ ID の使い道をカードで全部数える。本番の手の記録は 0 件（recon §2）。
- 手の記録が送信や24時間の窓を狂わせる: 便1 の除外と試験で止める（recon §8-3）。
- 会社の会話数が変わる: 今は全社で company_id が空のため、前後とも 0 件（recon §8-4）。K5 で確かめる。
- 消した手の記録が流れに戻ってくる: 会話の流れに消した印の条件を足し、試験で止める（recon §8-6）。
- 言語判定の生の数が1リードで変わる: 会社4 のリード38 は、写しで入った電話の1行だけが数えられている（en・1件・未確定）。条件を付け直すと 0件・未確定になる。画面は確定のときだけ言語を変える（useInboxState.ts:723）ので、画面の動きは変わらない（recon §8-6）。
- 便2・便3 は DB の形を変える: 危険 PR の手順（ADR-136）と控え。

## 7. 戻し方
- 便1: revert で写しと読む所が戻る。便1 の間に meta_messages にだけ入った手の記録は、戻すと会話タブに出なくなる（数はカードで数える）。
- 便1 の v_company_stats の作り直しは revert では戻らない（ビューは meta を読んだまま）。戻すときは、元の定義（migrations/20260612_120000_fix_company_stats_ssot.sql）で作り直す migration を別に出す。
- 便2: 制約を外す migration。便3: 控えから戻す。

## 8. 維持の仕組み
- 守り手: 設計担当（Opus）が便ごとに本番の数で確かめる。便3のあとは CI の確かめが止める。
- CI: conversation_logs という語を backend/app と scripts に新しく書くと止める確かめを便3で足す（足し方はカードで決める）。
- 仕様の正本 docs/specs/db-ssot/conversation-unification/design.md の §4 を今の数に直す。

## 9. 外部・過去事例の参照と我々への応用
- 不要。理由: 同じ会社の中で同じ事実を1つの表にまとめる作業で、判断は本番の数（recon §2）とコードの行で決まるため。

## 10. 審査
### 1回目（2026-11-07・クラウド architect opus・HEAD 7f13b0d28）: 判定の前に止まった。途中の指摘は REVISE 相当
- 止まった理由: 審査役の検索の語に削除の SQL 文が入り、クラウドの見張りに止められた。指示どおり言い換えずに終えた。
- 指摘と直し（Opus が実物で照合して反映）:
  1. 集計ビュー v_company_stats の漏れ → 便1 で作り直し、K5 に足した（recon §8-1・§8-4）。
  2. AI 読み取りの伏せ字・書く手伝い・試験などの漏れ → 便3 の片付けに並べた（recon §8-1）。
  3. 手の記録の sender_id の埋め方が無い → 便1 で値を決めた（recon §8-2）。
  4. 手の記録が送信の宛先・24時間の窓を狂わせる → 便1 で除外する（recon §8-3）。
  5. 統合の一覧から外すと統合が止まる → 便3 まで残す（recon §8-5）。
  6. webhook.py:723 は INSERT の途中 → :712 に直した。
- K5 の扱い: 対象を足しただけで、PO 承認済みの基準（差 0）は変えていない。
### 2回目（2026-11-07・クラウド architect opus・HEAD d7169b3cd）: REVISE
- 1回目の直し6件のうち5件は正しく入っていた。recon §8 の行番号はすべて一致。
- 最後の返事の途中（指摘4の後と未確認の一覧）は、記録の取り出しで切れて読めなかった。3回目で全体を見直してもらう。
- 指摘と直し（Opus が origin/main 170ff9612 と本番で照合して反映。recon §8-6）:
  1. 画像の送信 leads.py:2453-2460・未読に戻す :1300-1310 が除外リストに無い → 足した。試験も足した。
  2. 手の記録を消すと消した印が付くが、会話の流れなどが印を見ない → 消した印を付ける方を残し、読む所に条件を足した（行を本当に消す案は、監査と 410 の返し方が今と変わるので採らない）。
  3. 会話の流れは created_at、手の記録は occurred_at → 手の記録の created_at を occurred_at にそろえた。
  4. 言語判定の「原文でない窓口を外す」条件が meta 側に無い → meta の platform で付け直した。K5 の比べ方を画面が使う値に定めた。
### 3回目（2026-11-07・クラウド architect opus・HEAD df5b52d59・116秒）: APPROVE
- 2回目の4件は正しく入った。recon §8-6 の行番号はすべて一致。空を許さない列と message_id の一意も便1 の値で満たす。
- 中・低の指摘と扱い:
  1. 中: 変更 API で occurred_at を直すとき created_at がずれる → 便1 の値に足した。試験はカードで足す。
  2. 低: 本文のラベル付けに手の記録が入る → 今と同じく入れない（除外リストに移した）。
  3. 低: 新しい会社を作った直後、meta_messages に is_manual・deleted_at などの列が無い（tenant.py:1025-1039。列は run_all_migrations で付く）→ カードで確かめる。
  4. 低: v_company_stats の作り直しは revert で戻らない → §7 に書いた。
  5. 低: K5 の成約分析・週次の助言の「同じ問い」が未固定 → カードで文として固定する。
- 未確認（審査役）: lead_id が空で入る道が主要3か所のほかに無いか → 便2 のカードで確かめる。
