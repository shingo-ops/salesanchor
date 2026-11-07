# 会話の表を会社の中で1つにまとめる — 設計（KGI は PO 承認済み・設計審査2回目 REVISE を反映）

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
  - 会話の流れ（leads.py:963 から始まる取得）には手の記録も出す（K3）。
- 消した印の付いた行を出さない（recon §8-6。leads.py・meta_inbox.py には今 deleted_at の条件が1つも無い）。`deleted_at IS NULL` を次に足す:
  - 会話の流れ leads.py:1010-1040 の2つの取得（添付列ありと無しの両方）。
  - 本文のラベル付け priority_scoring.py:268。
  - 新しく meta を読む所（companies.py の会話タブ・v_company_stats）にも付ける。analytics.py・lang_judge.py は付いている。
  - 上の除外リストの所は手の記録を読まないので、消した印の条件は要らない。
- 影響なしと確かめた所: 既読 leads.py:1207（未読数は手の記録を数えない）、訳 leads.py:1412・添付の取り直し :1567（message_id で1行を指す）、Discord の反応 reaction_writer.py:115・discord_reactions.py:107（Discord の行だけ）。
- 読む所を meta_messages へ: analytics.py:2257・:2516、companies.py:1104（訳は message_translations から）、lang_judge.py:85・:123、scripts/lead_regression/generate.py:502・:517、smoke [7e]。
- 言語判定 lang_judge.py は meta_messages だけを読む。今 conversation_logs 側に付いている「文字が原文でない窓口（電話・対面）を外す」条件（lang_judge.py:33-37 `_NOT_VERBATIM_CLAUSE`）を、meta の platform で付け直す。付けないと、手で記録した電話の会話が多数決に入る。
- 集計ビュー v_company_stats を meta_messages で作り直す migration を足す（company_id で結ぶ。最終会話日は occurred_at、空なら created_at。消した印の行は数えない）。migrations/ を含むので危険 PR の手順（ADR-135・ADR-136）。表を消す操作は含まないので ADR-1003 の例外には当たらない。
- 名簿の conversation_store を全窓口 meta_messages にする（値の変更は seed の決まりに従う。詳細はカードで決める）。
- 毎朝の突合（celery_app.py:151-157・sa02_recon_monitor.py）を外す。逆向きの台本2本と、その試験を消す。
- リード統合の一覧 leads.py:3014 の conversation_logs は便3 まで残す（外すと統合が止まる。recon §8-5）。
- 試験: 手の記録が meta_messages に入り、会話の流れの API に出ること。写しが書かれないこと。手の記録が最新でも、送信の宛先・画像の送信の宛先・未読に戻す行・24時間の窓・受信箱の一覧の宛先と未読数が変わらないこと。消した手の記録が流れに出ないこと。過去の時刻で記録した手の記録が、流れのその時刻の位置に並ぶこと。電話の手の記録が言語判定に数えられないこと。
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
- 便2: 制約を外す migration。便3: 控えから戻す。

## 8. 維持の仕組み
- CI: conversation_logs という語を backend/app と scripts に新しく書くと止める確かめを便3で足す（足し方はカードで決める）。
- 仕様の正本 docs/specs/db-ssot/conversation-unification/design.md の §4 を今の数に直す。

## 9. 外部事例
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
