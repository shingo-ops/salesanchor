---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     リポジトリ外のパスはバッククォートを付けない。 -->
# recon — 価格のない〆・完売の行が要確認に残る件

> この文書は何か: 「カードセット〆切」（安川さん）のような価格のない〆・完売の行が要確認一覧に出続ける原因と範囲の調査。設計は docs/handoff/shime-review-exclude/design.md。

**基準**: git fetch 後の origin/main 70c3eda3d（2026-10-19）。本番 DB は reader 鍵（ssh -F /dev/null、ai_ro の SELECT のみ）。
**生出力**: /tmp/CC報告ファイル/shime-review-exclude-20261019/（*.sql・*.out・*.err）と /tmp/CC報告ファイル/yasukawa-shime-20261019/。投稿の原文は社外秘のためこの文書に貼らない。
**担当**: Planner（Opus）。調査の実行は Sonnet、本番照会の一部は Opus（reader 鍵の SELECT のみ）。

この文書の「〆の行」（SHIME）= status が sold out、exclusion='excluded'、price_normalized と quantity_normalized が NULL、product_id あり、prompt_version が v102 始まりの行。〆も完売も保存の形は同じ（PO 承認 10/19「同じ扱い」）。

## 0. 既存 ADR の検索

- 【事実】`docs/adr/FEATURE-INDEX.md` に要確認の理由（excluded・price_unresolved）を定める項目は無い。docs/handoff/review-excluded-ack/recon.md の ADR 検索でも「要確認の除外・確認済みを定める ADR は見当たらない」。
- 【事実】2つの理由の一覧 SQL への初出は commit 3301b4f68（2026-09-13、本文なし）。同コミットの試験は「配信に載る条件 = 要確認でない条件」を前提にしている（git show 3301b4f68）。
- 【事実】関連 ADR: `docs/adr/ADR-158-product-level-supersession.md`（仕入元×商品×状態の新しい投稿で古い在庫の is_current を FALSE にする）。要確認の理由は定めていない。

## 1. 起きていること

- 【事実】安川さんの〆: msg 6912cc37 / job a6dce5f0 / item c838f466。product 440301・状態 Sealed box（condition 14）・Sold out・excluded・pid_basis V102:matched_followup。同じ仕入元の同じ商品・状態の在庫（job 19e04929、4セット@18,500）は ADR-158 のまとめで既に is_current FALSE（在庫表に出ていない）。生出力 yasukawa-shime-20261019/recon.md。
- 【事実】それでも要確認に出る理由は、一覧 SQL が毎回 `price_unresolved`（価格 NULL）と `excluded`（除外あり・確認済みでない）を足すため。`backend/app/services/tcg_condition_review_svc.py:233`、`backend/app/services/tcg_condition_review_svc.py:234`。外れる条件は「価格が入る」（:240）と「このままで良い」の確認済み（:241、excluded だけ）。〆の行は価格が入らないので price_unresolved が残り続ける。
- 【事実】本番の「このままで良い」(review_ack) は全期間で1件（試験アカウント）。k1-ack.out。

## 2. file:line 引用表

| 場所 | 内容 |
|---|---|
| `backend/app/services/tcg_condition_review_svc.py:138` | review_joins。要確認の判定（cr）の唯一の SQL。f-string |
| `backend/app/services/tcg_condition_review_svc.py:180` | cr_latest（その行の最新の item_corrections 1件、どの項目でも） |
| `backend/app/services/tcg_condition_review_svc.py:192` | cr_review_ack（確認済みの印） |
| `backend/app/services/tcg_condition_review_svc.py:228` | cr_reasons。理由の配列（:229-241） |
| `backend/app/services/tcg_condition_review_svc.py:254` | needs_review = 理由が1つ以上 or unknown_review or 空箱（:254-255） |
| `backend/app/services/tcg_condition_review_svc.py:111` | _fence_review_joins。`) cr_input|cr_hash|cr_valid|cr_reasons|cr` の5か所に OFFSET 0 を足す。個数が違えば例外 |
| `backend/app/services/tcg_analysis_review_svc.py:76` | 要確認一覧が review_joins を使う。要確認の条件は :88-91 |
| `backend/app/services/tcg_distribution_svc.py:366` | 在庫表（dist_base）が review_joins(fenced=True) を使う。WHERE は :367-375（price_normalized IS NOT NULL・exclusion≠excluded・Sold out 除外を含む） |
| `backend/app/services/tcg_distribution_svc.py:480` | 配信プレビュー件数。:481-489 は dist_base と同じ WHERE |
| `backend/app/services/tcg_distribution_svc.py:524` | 除外内訳。cr.needs_review を使わない（:496-518） |
| `backend/app/services/tcg_distribution_svc.py:242` | _sold_out_filter（`lower(btrim(COALESCE(ar.status, ''))) NOT IN ('sold out', 'soldout')`） |
| `backend/app/services/tcg_distribution_svc.py:230` | _condition_filter（`cr.canonical NOT LIKE 'FLAG_%'`、include_flag_single で FLAG_SINGLE を通す） |
| `backend/app/services/tcg_distribution_svc.py:217` | _age_window（max_age_hours。本番値 48、r2-settings.out） |
| `backend/app/services/tcg_import_progress.py:129` | 取り込み進捗が review_joins を使う |
| `backend/app/services/tcg_condition_review_svc.py:275` | context_sql。状態の判断の保存と、旧エンジンの再解析（`backend/app/services/tcg_analyzer_svc.py:1592`・`backend/app/services/tcg_analyzer_svc.py:1801`）が使う。旧エンジンはその結果の needs_review・review_reasons を analysis_results に書く |
| `backend/app/services/tcg_analysis_dashboard_svc.py:61` | ダッシュボードの要確認件数は ar.needs_review を数える（cr は使わない） |
| `backend/tests/test_tcg_condition_review_fenced.py:1` | fenced の文字列検査 |
| `backend/tests/test_tcg_condition_review.py:681` | OFFSET 0 の壁が残ることの検査 |

## 3. 本番の実数（直近7日・画面と同じ範囲 sm.is_active、2026-10-19 06:24Z）

- 【事実】SHIME は 45 行（r1-reasons.out）。44 行は保存済みの理由が空・ar.needs_review=False で、要確認に出る理由は price_unresolved と excluded だけ。1 行（20f9cb54、状態 Error）は保存済みの理由 condition_unknown,unit_unknown,category_unknown がある。
- 【事実】仕分け（split2.out）。条件は ①状態が FLAG でない ②同じ仕入れ窓口（supplier_channel）に同じ商品・同じ状態の過去の在庫（価格あり・売り切れでない・自分より前の投稿）がある ③同じ窓口・同じ商品の行で、在庫表の条件（is_current・pid/unit 解決・除外なし・価格あり・48 時間以内・FLAG_ でない・売り切れでない）を今満たすものが無い ④人の修正（item_corrections）が無い。
  - 甲（①〜④すべて）35 行。安川さんの c838f466 を含む。
  - 乙（②が無い）8 行。f364283f・20f9cb54 ほか。
  - 丙（②あり・③が無い）2 行。044ba439（相手 Searched pack ¥400 In Stock）・1d027e6a。
  - ① FLAG は 0 行、④ 人の修正ありは 0 行。
- 【事実】45 行のうち 42 行は1つの仕入元の1投稿（job 225a8f49、41 商品の完売一覧）。乙と丙の 10 行はすべてこの投稿。
- 【事実】本番設定 include_flag_single=false、max_age_hours=48（r2-settings.out）。

## 4. 不明点リスト

| # | 内容 | 扱い |
|---|---|---|
| U1 | 追加する相関副問い合わせの速さ（analysis_results の product_id・source_messages の supplier_channel_id の索引の有無） | 設計 §7 T3 で本番 ai_ro の実測（変更前後を同じ時刻に比べる）。遅くなれば停止 |
| U2 | 丙の2行の元の投稿が本当に別の品か | 原文は未確認。設計は「自動で確かめられない行は残す」なので結論に影響しない |
| U3 | 旧エンジン（tcg_analyzer_svc）の再解析が今どれだけ走っているか | 未確認。走っても新しい規則と同じ値を保存するだけ（設計 §6） |

## 改訂2（2026-10-20）の現在地

- 【事実】基準は origin/main d1f1b6ac7。本番は reader 鍵・ai_ro の読み取りだけ。生出力の原本は ~/CC報告ファイル-keep/shime-remaining-20261020/（recon4・recon5・recon6・review1。原文は社外秘のためこの文書に貼らない）。
- 【事実】直近30日の「Sold out・excluded」の行 54 行のうち、要確認に出るのは 15 行。改訂2の式では 4 行（外れる 11・戻る 0）。7日では 14 → 4（recon6 sim-v2-count.out）。
- 【事実】在庫表は差し替えられた投稿の is_current 行も出す（`backend/app/services/tcg_distribution_svc.py:316`）。在庫表 1087 行のうち 300 行（recon5 inactive.out）。
- 【事実】外れる 11 行は、在庫表に同じ窓口・同じ商品・別の投稿の行が 0（まとめあり・なし。recon6 cross.out）。
- 設計は docs/handoff/shime-review-exclude/design.md §12。

## 改訂3（2026-10-20）の現在地

- 【事実】基準は origin/main 109503d77（コードの抜き書き recon3・recon4）。本番は reader 鍵・ai_ro の読み取りだけ。生出力の原本は ~/CC報告ファイル-keep/shime-next3-20261020/（recon1〜recon4。原文は社外秘のためこの文書に貼らない）。
- 【事実】A: 取り残しの状態が2種類以上の〆は直近60日・is_active 不問で 22 行、sm.is_active では 0 行、要確認 0 行。7日以内の再掲で「全部に当てる」を支える 3・反する 3（recon2 SUMMARY.md）。
- 【事実】B: 直近30日（終点 2026-10-20）の possible_footer_line 54 件のうち余白行が完売の語だけの文なのは 2928ea55 の1行。In Stock・Pre-order 0（recon2・recon4 D5）。
- 【事実】C: SOLDOUT_REF・SOLDOUT_INHERIT の〆 22 行のうち unit_unknown は 2 行（39300bc2・018e101c）。参照先の単位は 22/22 で1種類、2行は Set（recon2・recon4 D6）。要確認の一覧は unit_resolved が偽なら unit_unresolved を足す（`backend/app/services/tcg_condition_review_svc.py:261`）。
- 設計は docs/handoff/shime-review-exclude/design.md §13。

## 改訂3 追補（A の設計し直し、2026-10-20）

材料の原本: ~/CC報告ファイル-keep/shime-next3-20261020/recon5・recon6・recon7（原文と仕入元の名前は社外秘のためここに書かない。ei は先頭8文字）。
- 【事実】取り残し2種類以上の〆 22 行（60日・is_active 不問）を原文と照合: 全部に当てるが正しい 2・誤り 13・同じ 3・決められない 4（recon5 JUDGE.md）。
- 【事実】最新の在庫の投稿の状態が1種類 9 行。保存の状態と違うのは 83d61b3d だけ（F5_diff.tsv、60日の候補 1256 行で n_stranded=2 の差は1行）。
- 【事実】「全部」系の語を含む〆は 60日で 5 行、うち取り残し2種類以上は 2 行（F4.md）。
- 【事実】要確認に残った 0c91e2e0・5642ad0b の settled=偽 は、前の投稿の古いシュリなしの行 a42dcf92（is_current=真・48時間内）が相手に数えられるため（recon7 G4.md「今の相手の行数」1）。
- 【事実】相手を「〆以後の投稿か、〆より前の最新の在庫の投稿」に絞る形 (i) で、参考 40 件の偽→真は 2 件（0c91e2e0・5642ad0b）、今の一覧の〆の形 51 行の変化 0（G4.md、本番 08:49Z）。さらに is_current 等で絞る (ii) は 0 件。
- 設計は design.md §13-10。
