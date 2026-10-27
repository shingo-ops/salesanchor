# design: v102 の既定の指示書を raw_copy_v101_f_dm に切り替え

関連 recon: `docs/handoff/v102-prompt-fdm/recon.md`

関連 ADR（既存 ADR の検索結果）: ADR-1003（PO の委任に基づく Claude Opus の GO 発行）、ADR-136-cc-bot-github-identity.md（危険 PR の GO 手順と GO 記録の形）、ADR-135（main にマージ＝本番投入可）。指示書の既定 key を定める ADR は無い（前回 #4128 と同じ）。

状態: 設計審査済み（新しく起動した Reviewer opus の審査4回目で APPROVE）。PO 承認 2026-10-27（「切り替えますか」に「1」）。

出どころ: 社外秘の作業記録（リポジトリ外）の切り替え設計 第7.4版から §1・§3・§4・§6・§7・§8 を写した。文中の `../heading-fix/`・`review*`・`recon7` などはリポジトリ外の記録の名前で、ここからは開けない。仕入元の名前と投稿の本文は書かない。

## 1. 目的と成功条件
- 目的: 試験で D1・K1〜K3 に合格した f_dm を、本番の新しい抽出に使う。試験の根拠は ../heading-fix/test/RESULT-20261027.md と ../heading-fix/test/judge/out_20261027_133527_7784/REPORT.txt（FINAL=PASS rc=0 selftest=0。f_ct・f_dm を同じ1回の変換で同じマスタで判定）。
- 利用者に見える変化: 見出しの決まりで外れていた件（例: LIMIT OVER の ¥4,200 の件）が正しい行で読まれ、注意書きの下の傷あり未開封箱の件（試験 63件）が Damaged sealed box で読まれる。
- 時刻の基準: 下の「反映の時刻 T」は、切り替え PR の merge commit を含む deploy run のうち、最初に成功したものの完了時刻（UTC）。新しい抽出かどうかは extraction_jobs.extracted_at >= T で決める。prompt_version と extracted_at は同じ UPDATE で書かれる（svc:544,:549）。created_at では決めない。f_ct の job 2270件のうち1006件は、作られてから1日以上あとに読み直されているから（review1 の q_reext.raw）。

| 基準 | 検証方法 |
|---|---|
| S1 本番に反映された | 切り替え PR の merge commit を含む deploy run のうち、最初のものが success であり、smoke が成功していること |
| S2 新しい抽出が f_dm を使っている | extracted_at >= T で status が done か empty の v102 の job（prompt_version が `v102:` で始まる。filtered と empty の道は prompt_version を書き換えないので、status で絞る。tcg_extraction.py:376,:397）が1件以上あり、そのすべてが `v102:raw_copy_v101_f_dm:` で始まること。`v102:raw_copy_v101_f_ct:` で始まる件は0件であること。判定の時刻は、T のあと最初の v102 の抽出が出た時点。T から24時間たっても0件なら、§7 の「0件の見分け方」に従う。失敗の見張りは別にあり、T から2時間で判定する（§7 の F1〜F3） |
| S3 落とした件が増えすぎない | f_dm で抽出した job（prompt_version で絞る）について、analysis_results の行のうち status='none' の数と割合を数える。判定は、f_dm の行が2,000行になった時点か、T から72時間のどちらか早い方。その時点で 'none' が3行以上、かつ割合が0.1%以上なら不合格（§7 で戻す）。72時間で2,000行に届かなければ、その時点の数で判定し、行数も記録する |
| S4 円付けの見張り（合否には使わない） | switch/q_yen_added.sql と同じ数え方で数える。ただし WHERE は created_at を使わず、S3 と同じ範囲（prompt_version で f_dm を絞る。f_ct は extracted_at が T の前14日）に書き換える。新しい SQL は switch/post/q_yen_post.sql に置く。数え方は、元の本文の line_end の行（1始まり。split_part）に円が無いのに、raw_price に円があるもの。f_dm の件（S3 と同じ範囲）と、T の前14日間の f_ct の件を同じ SQL で並べ、PO に報告する。参考の f_ct の値は 382 / 21,751件（1.76%） |
| S5 単体試験 | test_line_analysis_v102_svc.py と test_prompt_ab.py は、実装の場で流して緑。test_line_analysis_v102_pg.py は CI 専用の DB が要るので、CI で緑 |

### S3 の閾値の根拠
- 試験（同じ157投稿を2回）: f_dm は2回で5,033行（2,517＋2,516）。status='none' は0行（judge/out_20261027_133527_7784/snap_dm1-cd-20261026_r1・_r2 の status 列。diag_k3/SUMMARY.txt と同じ数え方。scratchpad の 5_none.txt を ../heading-fix/test/record/none_fdm.txt に写した）。参考: f_hd は5,032行で1行（約0.02%）。以下の計算は、f_hd の1行を「試験で起こりうる割合」の目安として残す（0行だと割合の見積もりが0になり、壊れていないのに戻す確率を計算できないため、厳しい側の目安を使う）。
- 本番の f_ct（直近14日）: 0 / 41,071行（recon の q_none.raw）。41,071 は computed_at で数えた数で、再解析の行も入っている。抽出した日で数えると、平常の12日で 18,771行、1日あたり1,564行（review2 の q_rowsday.raw）。2,000行に届くのは T から約31時間後になる。
- 不合格の線「3行以上かつ0.1%以上」は、試験の割合の5倍。本当の割合が試験と同じ0.02%なら、2,000行で出る数の平均は0.4行で、3行以上になる確率は約0.8%（ポアソン分布で計算）。なので、壊れていないのに戻すことはまず無い。1件だけ偶然落ちたことでは戻さない。1〜2行のときは、記録して PO に報告するだけにする。
- 前提と幅:
  - この計算は「行ごとに独立に落ちる」とみなしている。実際の誤りは投稿ごとに出る癖がある（試験の1件も、1投稿の書き方から出た）。そのため判定のときは、'none' の行が何投稿から出たかも記録する。
  - f_dm の0件 / 5,033行から出せる割合の上の幅は、片側95%で約0.06%（3 / 5,033）。f_hd の1件から出せる上の幅は約0.094%。本当の割合が0.05%なら、2,000行で3行以上になる確率は約8%。0.1%なら約32%（review2 の計算）。この閾値は「試験より大きく悪いとき」を見つける線で、小さな悪化までは見分けられない。小さな悪化は、宿題の正答率の測定（§4）で見る。

### 試験で出た「カンマ＋円」の件の扱い（heading-fix の宿題への答え）
- 決めたこと: 戻す条件にはしない。S4 で見張り、PO に報告する。害は S3（落とした件）で数え、S3 で止める。
- 第7版の注記: この節は f_hd の試験（hd1-d r2）で出た件の話。f_dm の試験では status='none' が0行だったが、同じ投稿で円が付いたかは数えていない（まだ確かめていない）。扱いは同じ（S4 で見張る）。
- 理由1: 値段そのものは正しく読めている。f_hd r2 では、この投稿の35件すべてに円が付いた（カンマは元の本文の34件に初めからあった）。その34件は書き写しの照合を通り、K3 の採点で A1〜A5 が合っていた。本番も、照合では同じく円を除いて探し直す（svc:359-360,:1187-1188）。
- 理由2: 害が出たのは1件だけで、元の行にカンマが無い件だった。照合で落ちて、記録上は status='none' になった。これはそのまま S3 で数える量なので、別の閾値を置くと同じ害を二重に数えてしまう。
- PO への報告文には「何回に1回起きるかは、まだ確かめていない。切り替えのあと数えて報告する」と書く。

## 3. 変更の内容（切り替え PR）
1. `line_analysis_v102_svc.py:95` を `"v102-f_dm"` に、:97 を `"raw_copy_v101_f_dm"` に変える。ほかの行は触らない。
2. 次のファイルの固定値を f_ct から f_dm に替える。行は review1 の観点2の表のとおりで、#4128 の差分と1対1になる（行番号は origin/main 77b40a1ae。d7924ae70 からは prompt_ab.py と test_prompt_ab.py だけがずれた。recon7.txt）。
   - `backend/app/tools/prompt_ab.py:15,626`
   - `backend/tests/test_line_analysis_v102_pg.py:115`
   - `backend/tests/test_line_analysis_v102_svc.py:72,74,87,312`
   - `backend/tests/test_prompt_ab.py:105,689,690,693,698,928`
3. `docs/specs/line-analysis-tuning/README.md` を次のように直す。
   - :19 の「既定は f_ct」を f_dm に直す。
   - :39 は #4128 の履歴の行なので書き換えない。その下に、f_dm への切り替えの行を1行足す。行に書く sha256（64桁）は switch/recon7/4c_out.txt の id=397 の行から写す。
   - :39 の下に足す1行の中に、測定の宿題（§4。fetch_snapshot.py の絞り方を、次の正答率の測定の前に見直す）を書き添える。README の §4 は PO の判断の表なので、そこには書かない。足す1行には `v102-f_ct` と `raw_copy_v101_f_ct` の文字を書かない（§10-3 の grep で、残ってよい行の外に数えられないようにする）。この書き添えは #4128 の差分には無い追加なので、recon.md の対応表に「1対1の外の追加」と書く。
   - `docs/handoff/v102-prompt-fdm/recon.md` と `design.md` を新しく作る。design.md には、この switch/design.md の §1（|基準|検証方法| の表）・§3・§4・§6・§7 と、§8 の外部事例欄、ADR を探した結果（ADR-1003、ADR-136-cc-bot-github-identity.md、ADR-135）を写す。仕入元の名前と投稿の本文は書かない。
4. 触らないもの:
   - DB
   - migrations/
   - deploy.yml
   - scripts/ 全体（fetch_snapshot.py:5,26、README.md:17、test_fetch_snapshot.py:80,129,133,144 を含む）
   - ほかの版の定数
   - `backend/tests/test_v102_value_overrides.py:232,353`: `v102:raw_copy_v101_f_ct:abc` を固定値で使っているが、効くのは `v102:` の接頭辞だけ（svc:159-160 の startswith）。#4128 のあとに入ったもので、替えなくても合否は変わらない。
   - `docs/specs/line-analysis-tuning/README.md:39`（#4128 の履歴の行）
   - f_hd の行（id=377）と、f_hd を名前で書いた記録（試験の資料）。
   - 定数を名前で使う箇所（prompt_ab.py:78,323,493、tools/reextract_v6_with_v102.py:217、test_line_analysis_v102_pg.py:169）: 定数に追随する。

## 4. 選んだ理由と、採らなかった案
- 定数を替える PR にする: 本番がそうやって指示書を選んでいるので、ほかに道は無い。DB の行を差し替える案は採らない。定数は f_ct を指したままなので解析が止まり、名前と中身も食い違う。
- 本番での f_dm の正答率の測定は、この便では行わない。f_dm が使えることの根拠は試験（D1・K1〜K3）。理由は次のとおり。
  - 正解の表 gold_v1 の投稿は、切り替えより前のもので、f_ct で抽出されている。f_dm では読まれていない。
  - 人の訂正や再解析では Gemini を呼ばず、そのときの定数で engine_version を上書きする（svc:776,:1168）。そのため切り替えのあと、正解の表の投稿でも再解析されたものは engine_version が v102-f_dm になる。fetch_snapshot.py の既定（:26 v102-f_ct、:83 で絞る）のままだと、その投稿は0行になって測定から黙って落ちる。
- 宿題（別の便。scripts/ は危険パスなので GO が要る）: 次に正答率を測る前に、fetch_snapshot.py の絞り方を見直す。prompt_version で絞るか、落ちた投稿の数を出して止めるか。それまでの間は、クラウドの正答率の鎖を流す前に、この宿題が済んだかを確かめる。
  - 2026-10-25 01:53 UTC に、claude.ai のクラウドの定期実行を一覧で確かめた（RemoteTrigger list、15件）。cron_expression はすべて空で、一回きりのものだけ。有効なのは「試行11」の1件で、予定時刻は 2026-10-25 01:52 UTC。切り替えより前に終わる。
  - agent-console の定期実行と予約にも、fetch_snapshot を呼ぶものは無い（§9）。
- 見張り（S2〜S4）は engine_version を使わず、extraction_jobs.prompt_version で絞る。prompt_version を書くのは抽出のときだけ（svc:544）だから。

## 6. 危険度と GO
- 変更するパスは backend/app/services、backend/app/tools、backend/tests、docs。check-process-artifacts.js の危険パターン（:117 の scripts/、:125 の backend/app/ops/、migrations/、deploy.yml）には当たらない。
- ただし backend/app/services を触るので、関所が GO 記録を機械的に求める（check-process-artifacts.js:143、:939-950）。
- GO は、PO の委任に基づく Claude Opus 発行（ADR-1003）とする。出す前に、次の3つがすべて揃っていることを確かめる（ADR-1003「委譲の条件」）。
  1. 必須の CI がすべて通っている。
  2. Reviewer（新しく起動した opus）が APPROVE している。
  3. PO に3行のまとめ（対象・変更内容・バックアップ確認）を報告している。
- 切り替えそのものは、PO が 2026-10-25 に「切り替えはまだしない」とした範囲の外にある。だから GO の前に、PO の「切り替える」の返事が別に要る。PO の返事は PR 本文の GO 記録に原文のまま写す。GO 原文は ADR-136-cc-bot-github-identity.md:62,67 の形 `GO #<この PR の番号>` で書く。発行者・日時・HEAD も残す。
- GO の直前に、次を確かめる。
  - 読み取り鍵で、f_dm の行（id=397）の is_active と sha256（84afd2e4…ac8b0c）をもう一度確かめる。f_ct の行（id=133）が残っていることも確かめる。
  - 読み取り鍵で、switch/post/q_pre_go.sql を流す（v102 の試行で `prompt_version LIKE 'v102:%'`、`started_at >= now() - interval '24 hours'`、phase='failed' の一覧。失敗の種類は問わない）。出してよい条件は1つ: 一覧の一番新しい started_at が、流した時刻（生出力の AUDIT ts、UTC）より6時間以上前であること（一覧が0行ならそのまま満たす）。満たさなければマージを延ばし、満たしてから流し直して確かめる。一覧が1行以上あるときは、その内訳（日本時間の時刻・HTTP の番号・job の状態）を GO 記録と PO への3行のまとめに書く。生出力は switch/post/ に時刻付きで残す。理由: Gemini 側の不調が続いている間に切り替えると、F1 が3件に届いて、指示書と関係なく戻すことになる（§7）。
  - RemoteTrigger list で、クラウドの予約を取り直す。fetch_snapshot を使う予約が、反映のあとに動く予定になっていないか確かめる。
  - agent-console の routines.json と reservations.json を Opus 本体が開き、fetch_snapshot を呼ぶものが無いか確かめる（担当からは見張りで読めない。review73 §3）。
  - その日の為替を取り直し、§9 の円の値を書き換えて PO への報告に使う。
  - PO に Gemini の前払い残高の画面を見てもらい、72時間分（本番 約94回/日 × 約0.0089 USD で1日 約0.84 USD、3日で約2.5 USD）より十分に多いことを確かめる。確かめられないときは、その旨を PO への3行のまとめに書く（10/27 00:06 JST に残高切れで本番が失敗したため。review73 L2）。
- GO 記録には「バックアップ確認」の欄を入れる（ADR-136-cc-bot-github-identity.md:68）。書く中身は次のとおり。
  - DB を変えないこと。
  - 反映前のバックアップは差分どおりなら走らないこと（§5）。
  - 戻し先の f_ct の行が残っていること。

## 7. 戻し方
- 戻す手順は通常の道で行う。
  1. 切り替え PR を revert する PR を作る。
  2. CI を通す。
  3. 新しく起動した Reviewer の APPROVE をもらう。
  4. GO 記録を書く（Opus の委任発行。戻す PR も services を触るので関所が求める）。
  5. マージする。
  6. deploy で反映する。
- DB の f_ct の行（id=133）は残っているので、反映した時点から f_ct に戻る。
- break-glass（`EMERGENCY:`）は使わない（review4 M10）。理由は2つ。
  - 戻す PR も関所が GO 記録を求め、委任の GO には Reviewer の APPROVE が要る（ADR-1003）。break-glass にしても、待ち時間はほとんど縮まない。
  - 抽出が全部止まっても、投稿の job は pending のまま残り、戻したあとに10分ごとの回収（tcg_extraction_recovery.py:140-165）が拾い直す。待つ間に投稿が失われることは無い。
- 失敗の見張り（T から2時間の時点で1回、以後は S3 の判定まで6時間ごと）。読み取り鍵で数える。数える単位は job（同じ job を2回数えない）。f_dm の job は prompt_version が `v102:raw_copy_v101_f_dm:` で始まるもので見分け、時刻では絞らない。celery-worker は T より前に作り直されるので（deploy.yml:454-461）、f_dm の値は T の少し前から書かれうるため。
  - F1 失敗した job: f_dm の job で status='error' のものと、extraction_attempts で prompt_version が `v102:raw_copy_v101_f_dm:` で始まり phase='failed' の試行を持つ job を、job の id で重ねずに数える。失敗の記録は1回の fail() で試行（phase='failed'）と job（status='error'）の両方に入るので（tcg_extraction_record_svc.py:235,244,262-264）、別々に足さない。失敗すると extracted_at は空に戻るので、時刻では絞らない。
    - 1件ごとに、試行の error_code と validation_result（category と、raw に出る HTTP の番号）を読み、次の2つに分ける（gemini_extraction_svc.py:198,:213-220。/tmp/CC報告ファイル/v4_errcode/report.md）。
    - HTTP 402（前払い残高切れ）は、category にかかわらず Gemini 側に入れ、PO への報告では「残高切れ」と名前を分けて書く。2026-10-27 に、同じ鍵で本番が 00:06 JST、試験が 00:20 JST に 402 で止まった（review7_evidence/att2.out、../heading-fix/damage-fix/design.md:100）。指示書では起こせない失敗なので。
    - 分けるときは category を先に見る。gemini_rate_limit と gemini_timeout は、raw の番号にかかわらず Gemini 側に入れる（rate_limit の行に HTTP 402 が出る例がある。review4 L15、q_fail_cat.raw）。HTTP の番号を見るのは gemini_http_error のときだけ。
    - Gemini 側の不調: error_code が API_ERROR で、category が gemini_rate_limit か gemini_timeout のもの、または gemini_http_error で HTTP の番号が5で始まるもの、または HTTP 402。Gemini の呼び出しにはクライアント側の時間切れが無いので、時間切れはサーバ側の 504 として出て、ここに入る（review4 M8）。
    - 指示書が原因かもしれないもの: それ以外のすべて。API_ERROR で HTTP が4xx（429・402を除く）、番号の無い gemini_unknown（通り道の gemini-egress の不調も入る。review4 L21。どちらでも戻す数に入るので、ログは見なくても○×は決まる）、SOFT_TIME_LIMIT、RESPONSE_TOO_LARGE、PARSED_TOO_LARGE、INPUT_TOO_LARGE、RECORD_WRITE_FAILED など。見分けられないものは、こちらに入れる（安全な側）。
    - 基準（2026-10-27 14:05 JST に取り直し。review7_evidence/rv7_att.out・att2.out）: f_c の初日（2026-10-10）の API_ERROR 6件のほかに、f_ct でも 10/27 JST（UTC では 10/26〜27）に 9回失敗した。すべて API_ERROR・gemini_http_error で、10/27 00:06 JST の HTTP 402 が1回（job は done に戻った）、10/27 06:44〜11:08 JST の HTTP 503 が8回（job 8件が status='error' のまま）。それより前の 10/20〜10/25 は全部 completed。だから「f_ct は失敗0件」ではなく、「Gemini 側の不調で f_ct も落ちる」が基準になる。
  - F2 応答が読めない・解析段の例外: f_dm の job で、review_reasons に response_unreadable か extract_exception を含むもの（svc:418-426,:539-540,:1528-1535。review_reasons は「,」区切りなので、`string_to_array(review_reasons, ',')` で要素ごとに比べる。review4 L16）と、error_message が ANALYSIS_FAILED か ANALYSIS_FAILED_RETRIED のもの（tcg_extraction.py:442-461,:475-480）。status は done か empty のままなので、S2 では成功に見えてしまう。これで拾う。基準はどれも0件（review3 の q_rr.raw、q_af.raw）。empty の job の解析段で起きた例外は記録に残らない（review4 L17）。そこは S2 の「0件の見分け方」と、記録だけする empty の割合で見る。指示書を替えると応答の形が変わりうるので、F1 の「指示書が原因かもしれないもの」と同じ扱いにする。
  - F3 止まったまま: extraction_jobs で created_at >= T、かつ created_at が見張りの時刻より30分以上前で、status が pending か running のもの（filtered は除く）。指示書の行が読めないときは、svc:500 で ValueError になり、試行も error も DB に書かれず、job は pending のまま残る（svc:177-180、tcg_extraction.py:427-432、/tmp/CC報告ファイル/v4_errcode/report.md の3）。これでしか見えない。
    - 時刻は created_at を使う。source_messages.received_at は取り込みが最大約21時間遅れ、まとめて来るので使わない（review3 の q_lat.raw・q_lat2.raw・q_lat4.raw）。§1 の「created_at では決めない」は「新しい抽出かどうか」の話で、ここは「T のあとに来た job が止まっているか」の話なので食い違わない。
    - 基準: 直近14日の filtered でない job 1,251件で、作られてから最初の試行まで最大148秒、30分を超えたものは0件（review3 の q_lat5.raw）。
    - Gemini で一斉に読み直すと古い job も pending に戻るが、created_at が T より前なので F3 に入らない。だから T のあと72時間は、Gemini での一斉の読み直しをしない。
  - 記録だけするもの: f_dm の job のうち empty の割合（基準は f_ct 61 / 2,272件で2.7%、すべて no_items。review3 の q_empty.raw）。f_dm の job が100件以上で10%を超えたら、PO に報告して判断をもらう。
- 戻す条件（どれも、戻す PR は上の通常の道で作る）:
  - S1 の deploy run か smoke が失敗した。
  - F1（種類を問わない）と F2 の job の数が、重ねずに合計3件以上。1〜2件なら、その job の記録とアプリのログを読み、原因を記録する。
    - Gemini 側の不調も、ここに入れて戻す側に倒す（review5 R8 の直し方2）。理由: 切り替えたあとは試行が全部 f_dm になり、Gemini の障害か f_dm が原因かを比べる相手が無い（直近14日の試行は全部 f_ct。数は review5 の q_att_pv14.raw の 1,248件のあとも増えていて、10/27 JST（UTC では 10/26〜27）には f_ct でも Gemini 側の不調で9回失敗した。F1 の基準を見る）。指示書が長くなったこと（f_dm 7,773字、f_ct 5,469字。recon7.txt）で時間切れや失敗が増える形も、ここで拾う。
    - 払うもの: Gemini の障害のときに戻しても、失敗は直らない。戻す PR と反映が1回ずつ無駄になり、障害が収まってから切り替えの PR を出し直すことになる（試験の根拠は変わらないので、設計はこのまま使える）。f_c の初日（2026-10-10）にはレート制限で 6 / 64件が失敗しており（review5 の q_f_c_day.raw）、同じことが起きれば戻すことになる。
    - F1 の2つの分け方（Gemini 側の不調 / 指示書が原因かもしれないもの）は、戻すかどうかには使わない。PO への報告と、切り替えを出し直すかの判断に使う。
  - 割合の線は置かない。基準が0件なので、件数の「3件」の線で足りる（review5 R8 (c)）。
  - F3 で2件以上止まっていて、かつ worker を作り直してから f_dm の job が1件も done か empty になっていない。抽出が全部止まったとみて戻す。
  - F3 で3件以上止まっていて、ほかの job は done になっている場合は、アプリのログ（tcg_extraction.py:428）で指示書の読み込みの失敗かを確かめてから決める。F3 が1〜2件で、ほかの job が done の場合は、ログを読んで記録し、次の回にもう一度数える。次の回にも同じ job が止まっていれば、3件以上と同じ扱いにする（review4 L18）。
  - S3 が不合格（'none' が3行以上で、かつ0.1%以上）。
- 戻す条件ではないもの: S2 で、T 以降に f_ct で始まる v102 の job（status が done か empty）が出た。これは反映されていないことを示すので、戻しても直らない（review4 L19）。Opus が deploy run と celery-worker のイメージを確かめ、反映をやり直すかを決める。
- 戻すかどうかは Opus が決め、決めたらすぐに PO に報告する。
- 失敗した job の入れ直し（review4 M9）: status='error' の job は、10分ごとの回収ではやり直されない（回収が見るのは pending と running だけ）。入れ直すには retry_extraction を使う（入口は tcg_diagnostics.py:95）。これは本番のデータを動かす操作なので、この切り替えの GO にも、この設計にも含めない。戻したあとも、f_dm の期間中も同じ。
  - 一覧の作り方: Sonnet が読み取り鍵で、F1 の job（prompt_version が `v102:raw_copy_v101_f_dm:` で始まり status='error'）の id と error_code を switch/post/ に書き出す。Opus がそれを PO に見せる。
  - 誰の名義でどう呼ぶかは、PO の同意を得たときに、別の実装カードで決める（review5 L22）。
  - 入れ直したあとも、F1 の数は減らさない。F1 は失敗した試行（phase='failed'）を持つ job も数えるので、成功に戻った job も数に残る。
- 0件の見分け方（S2 で T から24時間、v102 の抽出が0件だったとき）: T 以降に作られた job の数を、読み取り鍵で extraction_jobs.created_at から数える。filtered の job は除く。直近14日は、届いた投稿のすべてに job があり、約95%が v102 の job に進んでいる（review2 の q_sm_vs_job.raw）。
  - job が作られているのに抽出が0件なら、壊れたとみて戻す。
  - job も0件なら、壊れたとは言えない。判定を次の24時間に延ばし、PO に報告する。
- 切り替えている間に f_dm で読んだ件は、戻しても書き換えない。必要になったら、別の便で読み直しを検討する。
- 戻したあとに人の訂正や再解析をすると、f_dm で抽出した件も engine_version が v102-f_ct に付け替わる（svc:776,:1168）。どちらの指示書で抽出したかは、prompt_version で見分ける。

## 8. 外部事例
採用しない。判断の根拠は、自社の試験（同じ157投稿を2回）と、同じ形で切り替えた #4128 の実績で足りる。外の事例は、この指示書の文面に当てはまらない。


## 維持の仕組み
- 反映後の見張り（§7 の F1〜F3、§1 の S2〜S4）は Opus が時刻を決め、担当（Sonnet）が読み取り鍵で数える。SQL と生出力はリポジトリ外の作業記録 switch/post/ に置く。
- 次に正答率を測る前に fetch_snapshot.py の絞り方を見直す宿題（§4）は、docs/specs/line-analysis-tuning/README.md の f_dm の行に書き添えて残す。
