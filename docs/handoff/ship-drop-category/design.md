# 発送日欄の未訳10行の整理 — 設計（草案・2026-10-13）

状態：設計案作成済み・Fable 再審査 APPROVE（2026-10-14、/tmp/CC報告ファイル/ship_cleanup_design_review2.txt）・PO の方針 y と実装着手 y 済み・便A 実装委任中・便B 未着手。
社外秘：仕入元の原文は書かない。下の例はすべて一般化した形。repo に移すときもこのままの粒度で。

## 1. 目的と成功条件
発送日の欄（ship_ja / ship_en）には「いつ送るか」だけを入れる。今は、対応表に無い言い方は元の文字のまま入り、英語の欄が空になる（本番 10行・2026-10-13 commit 後）。

| 基準 | 検証方法 |
|---|---|
| 10行のうち発送情報の行は ship_en が入る（#1〜#6・#7 の出荷予定部分・#8） | 当て直し後に analysis_results の該当10 id を読み取りで確認 |
| 梱包の文（カートン・括り）と完売の文は ship_ja に出ない（#7 の完売部分・#9・#10） | 同上。#9・#10 は ship_ja が NULL |
| 便A 単独で動きが変わらない | 便A の PR で既存テスト全緑＋本番デプロイ後に発送欄除外0件のまま ship の新規行に変化なし |
| すでに英語の入っている 148行は意図せず変わらない | 全157ジョブの dryrun 差分を全件一覧にし、10行（＋双子）以外の変化は「旬の exclude 追加で中旬〜下旬の形に正しく変わった行」など理由を1行ずつ付けて PO が y（Fable 指摘3：控えはラベルで原文ではないため、事前に完全一致は保証できない） |
| 10行の行ごとの期待値 | #1 発売日発送/Ships on release day、#2 発送日要相談/Ship date negotiable、#3-6 発売日発送/Ships on release day、#7 N日〜M日発送/Ships day N-M（発売告知・完売は捨て）、#8 N月中旬〜下旬入荷 / 入荷次第発送（en 両方）、#9・#10 NULL/NULL |
| 発送時期の札に当たる文は、梱包の札にも当たっても残る | 単体テスト（例「カートン 11/20発送」→ 11/20発送） |

## 2. 現在地（origin/main、file:line）
- 網：backend/app/services/gemini_raw_copy_v101.py:809-826 `_ship_for` が「発送|出荷|入荷|発売|着」（gemini_raw_copy_v10.py:180）を含む行から文字を取り " / " でつなぐ。
- 当て方：backend/app/services/tcg_analyzer_svc.py:1156-1178 `build_ship_labels`。" / " ごとに備考マスタ category=発送時期系（:1116, :1120-1149）へ当て、外れた部分は原文のまま ja・en=None（:1167-1170）。
- 呼び出し：backend/app/services/line_analysis_v102_svc.py:671（masters は :196）。note_ja は :682 で常に None。
- マスタ：public.tcg_note_master（migrations/20260919_020000_master_ssot_public_tables.sql:234-247、label_template_en は migrations/20261013_140100_*.sql:2）。発送時期系18行は migrations/20260907_100000_tcg_note_master_expand_t004.sql:30-36、migrations/20260909_130000_tcg_note_b2_t004.sql:66-90。
- 梱包・完売の札は既にある：NJ050 カートン発送可（荷姿系、expand_t004.sql:52）、NJ073 完売（取引条件系、b2_t004.sql:91）。「括り」の札は無い。
- 調査の生資料：/tmp/CC報告ファイル/ship_label_logic.txt、/tmp/CC報告ファイル/ship_10rows_detail.txt（社外秘・repo 外）。

## 3. PO の決定（2026-10-13 チャット、原文は会話記録）
| # | 形（一般化） | 扱い |
|---|---|---|
| 1 | 「発送日発送」 | 発売日発送（打ち間違い） |
| 2 | 「発送日要発送」 | 発送日要相談（打ち間違い） |
| 3-6 | 「発売日」だけの行 | 発売日発送 |
| 7a | 「N日〜M日出荷予定」 | 発送情報 |
| 7b | 「N日出荷分は完売」 | 完売情報（発送日に入れない） |
| 8 | 「N月中旬から下旬入荷予定」 | 発送情報 |
| 9 | 「…でカートン、…で括り発送可」 | 発送情報ではない（網にかけない）— 方式は y |
| 10 | 「カートン発送可」 | 9と同じ |
| 7c | 「N月N日発売」 | 発送日に入れない（PO y 2026-10-13） |

## 4. 変更（便A＝コード PR、便B＝マスタ投入と当て直しの PO `!` スクリプト）
共用マスタのデータは migration で触らない（PO 方針 2026-09-18、CI migration-guard チェック7・正本 scripts/migration-guard/protected-tables.txt:29（.github/workflows/migration-guard.yml:397-400）が public.tcg_note_master のデータ操作を止める）。マスタの行は前例 po_ship/po_step12.py と同じく、PO の `!` 実行スクリプトで取引内に入れる。順番は 便A デプロイ → 便B。便A は「発送欄除外」の行が0件なら今と同じ動きなので、先に出しても変化しない。
### 4-1 マスタ（便B・PO `!` スクリプト・本番 id で UPDATE/INSERT。本番の現物 2026-10-13 23:53 JST 取得：/tmp/CC報告ファイル/note_master_prod.txt）
本番の発送時期系は28行（migration の18行＋10/13 13:52Z に po.sh step1 が入れた id 189〜198。旬の発送 193〜195・月日範囲 192 など）。荷姿系3・取引条件系11。tenant_id は NULL（中央）前提＝便B の書き込み前に確認。
- id 120 発売日発送：search_keywords に `発送日発送` を足す。
- id 99 発送日要相談：search_keywords に `発送日要発送` を足す。
- 新 発送時期系 REGEX p1 `^\s*発売日\s*$` → 発売日発送 / Ships on release day（部分一致にすると id 95・137 と二重に当たるため行全体一致）。
- 新 発送時期系 REGEX p1 `(\d{1,2})日[〜~ー\-](\d{1,2})日[^\d]{0,4}?(発送|出荷)` → `$1日〜$2日発送` / `Ships day $1-$2`。除外=`完売,月`（「10月16日〜18日出荷」は id 192 が持つので二重を避ける）。
- 新 発送時期系 REGEX p1 旬の入荷（id 193〜195 は 発送|出荷 だけ）：`(\d{1,2})月上旬[^\d]{0,4}?入荷`→`$1月上旬入荷`/`Arrives in early month $1`、中旬・下旬も同様（3行）。
- 新 発送時期系 REGEX p1 旬の範囲（3組×動詞2＝6行）：例 `(\d{1,2})月中旬(?:から|〜|~|ー|-)下旬[^\d]{0,4}?入荷` → `$1月中旬〜下旬入荷` / `Arrives mid-to-late month $1`。発送|出荷 版は `…発送` / `Ships mid-to-late month $1`。
- 既存 id 193〜195 と新しい旬の入荷3行の exclude_keywords に `から中旬,から下旬,〜中旬,〜下旬,~中旬,~下旬,ー中旬,ー下旬,-中旬,-下旬` を足す（Fable 指摘2：区切り5種すべて）（「中旬から下旬発送」に id 194 も当たって二重になるのを防ぐ。194 の pattern は「から下旬」4字を挟んでも当たる）。
- 新 区分 `発送欄除外`（発送日の欄から捨てる札。解析の出力（ship_ja・note_ja）には使わない。管理画面の一覧・CSV には出る＝何を捨てるかを人が見て直せるようにするのが目的（note_master.py:146,:272、super_admin_note_master.py:134-145,:256 は category で絞らない）。label_ja は CSV 取り込みが label_ja で突き合わせるため既存と重ならない名にする）：
  - `発送欄除外:完売` LITERAL kw=`完売` 除外=`出荷予定,発送予定`
  - `発送欄除外:カートン` LITERAL kw=`カートン可,カートン発送可,マスターカートン発送可,カートン発送可能`
  - `発送欄除外:括り` LITERAL kw=`括り発送可,括り可`
  - `発送欄除外:発売日告知` REGEX `^[^\d]{0,3}(\d{1,2})月(\d{1,2})日\s*発売\s*$`
  当初案（既存の荷姿系・取引条件系をそのまま使う）から変えた理由：本番の取引条件系に「予約商品」「在庫品」「〆」「要相談」があり、発送時期系に当たらない発送の文がこれらに当たると黙って消える。捨てる札を専用の区分に分け、何を捨てるかを一覧で見えるようにする。
- 英語の文言は草案。管理画面で後から直せる。

### 4-2 コード
- tcg_analyzer_svc.py：`SHIP_DROP_CATEGORY = "発送欄除外"`、`load_ship_drop_master(session)`（load_ship_master と同じ形・category だけ違う。共通化してよい）。
- build_ship_labels(ship, ship_entries, drop_entries=()) ：部分ごとに ①発送時期系に当たる→今どおり ②当たらず drop_entries に当たる→その部分を捨てる ③どちらにも当たらない→今どおり原文・en None。全部捨てたら (None, None)。
- load_note_master（tcg_analyzer_svc.py:1013-1040）は category を見ずに全 enabled 行を読む（:1362 で備考に使う）→ `AND category IS DISTINCT FROM '発送欄除外'` を足し、旧エンジンの備考に「発送欄除外:…」が出ないようにする。
- line_analysis_v102_svc.py：`_SHIP_DROP_KEY` を作り :192-197 の masters に足す。**:329 の除外を `k not in (_SHIP_ENTRIES_KEY, _SHIP_DROP_KEY)` にする**（extract_items に **kwargs で流れると TypeError で投稿全体が落ちる。tests/test_line_analysis_v102_svc.py:199-200 が同じ落とし穴を守っている）。:671 は `masters.get(_SHIP_DROP_KEY, ())` で渡す（fixture に新キーが無い既存テスト4本 test_line_analysis_v102_svc.py:28・test_line_analysis_v102_pg.py:60・test_v102_buyback_unit.py:218・test_v102_unit_price_check.py:172 を壊さない）。
- load_ship_drop_master は0件で warning を出さない（便A 単独の期間は0件が正常。load_ship_master の :1134-1135 とは違う）。
- 触らない：_ship_for の網（gemini_raw_copy_v101.py:809-826）、Gemini の指示書、note_ja、配信列の並び、管理画面。
- テスト：build_ship_labels の単体（10行の一般化例＋「カートン 11/20発送」が残る＋未知の言い方が残る＋全部捨てで None）、load_note_master が新区分を読まない（fixture に1行足す）、:199 と同型で drop キーも extract_items に渡らない。旬の範囲は区切り5種で二重にならない（ー・- を各1件）。

### 4-3 当て直し（便B の中）
dryrun は前回の commit と同じ157ジョブ全部で行い（148行が変わらないことの検証のため）、commit で書くのも157ジョブ。変わるのは該当8ジョブ（541a8d47・8880aa32・6c555f8d・2391d2ab・c88adc8e・e9fbf372・f9ef70fc・badd89d8）。既存の po.sh（dryrun→commit）を対象ジョブだけに絞って PO の `!` 実行。デプロイ中は実行しない（10/13 の教訓）。

## 5. 代替案
- A（採用）マスタの札で捨てる：捨てる札を専用区分に置き、言い方が増えてもマスタ追加だけで済む。
- B 網の正規表現から「発送可」を外す：「土日祝発送可」「即日発送可」など本物の発送情報も落ちる。不採用。
- C Gemini に梱包行を ship 役割にしないよう指示：プロンプト変更は全件の再測定が要り、効き方が揺れる。不採用。

## 5-2. 外部事例
該当事例なし（不要）。理由：社内の備考マスタ（public.tcg_note_master）に区分を1つ足し、既存の当て方（build_ship_labels）の分岐を1つ増やすだけの変更で、新しい技術選択や外部の仕組みの導入を含まない。成否は外部の数値ではなく、本番 dryrun の差分（§1 の表）で判定する。

## 6. リスクと対処
- 本番マスタが migration と違う → 確認済み（10行は po.sh で投入され migration に無い）。便B のスクリプトは本番 id を前提にし、書く直前に id 99・120・193〜195 の kw/exclude が上の取得値と同じこと、label_ja「発送欄除外:…」が未登録であることを確かめ、違えば何も書かずに止まる。
- 捨てる札が広すぎて発送の文が消える → 専用区分の4行だけにした。dryrun で捨てた部分を全件一覧にし PO に見せる。
- 新 REGEX が既存の当たり行に二重ラベルを付ける → 全157ジョブ dryrun で差分10行に限られることを受入条件にする。
- label_template_en：本番の発送時期系 REGEX 行は全て値あり（note_master_prod.txt で確認）。新しい行にも入れる。
- 便B を便A より先に流すと旧エンジンの備考に「発送欄除外:…」が出る → 便B のスクリプトは書く前にコンテナ内で `tcg_analyzer_svc.SHIP_DROP_CATEGORY` が存在することを確かめ、無ければ止まる（Fable 指摘5）。
- 「N月N日発売予定」の形は捨て札に当たらず原文のまま残る（意図どおり：発売日告知の行は行全体が「N月N日発売」のときだけ捨てる）。

## 7. 決定済み（旧未決）
- PO y（2026-10-13）。#7c「N月N日発売」：発売日のお知らせで発送日ではない、として捨てるか。推奨：捨てる（発売日は商品マスタが持つ。発送情報は同じ投稿の「出荷予定」側で取れる）。捨てる場合は取引条件系ではなく、発送時期系に当たらない「日付＋発売」だけの部分を捨てる行を荷姿系と同じ扱いの区分に足す。

## 8. 自己審査（Architect 役・同一AI）
下書きの自己審査は APPROVE としていたが、Fable 審査（/tmp/CC報告ファイル/ship_cleanup_design_review.txt、2026-10-14）で REVISE：指摘1〜8を本版に反映済み。再審査（同日、review2.txt）で APPROVE：引用行番号は origin/main 0819129 と一致、exclude 10語は21例の検算で二重0・消失0。
- 整合：ADR-155（マスタ SSOT・管理画面で編集）に沿う。コードに語を直書きしない。
- 根拠：網・当て方・マスタの行は file:line で確認済み。本番マスタの現物は未確認（リスク表に手順あり）。
- 検証可能性：1 の表はすべて読み取りと dryrun で○×が出る。
- 実装範囲：便A＝tcg_analyzer_svc.py＋line_analysis_v102_svc.py＋テスト（migration なし）。便B＝repo 外の PO スクリプト。マスタに入れる行は、dryrun の後に「今の値／足す値／足した後」の表を PO に見せて y を取ってから commit（feedback_show_candidates_before_master_write）。
- 審査：PO 方針（2026-10-12）により設計審査は Fable（architect, model fable）に依頼する。上の自己審査は下書き。

## 9. 維持
新しい言い方が出たら、マスタに行を足すだけで済む（コード変更不要）。未訳行の件数は、当て直しのたびに「ship_ja あり・ship_en なし」の件数で見る。
