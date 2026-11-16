# recon — 本番の解析（システム段）が計算の間に取引を開いたままにする件

- 日付: 2026-11-12。担当: Planner（Opus）。行番号は origin/main a3e93f053。
- 親: docs/handoff/app-idle-tx/（受信箱の流れの取引。K5 の残り）・docs/handoff/replay-tx-release/design.md（試しの道具の同じ型。§2 で「本番の解析 run_v102_analysis は別の設計で扱う」と対象外にした）。
- 既存 ADR の検索: `git grep -i -l -E "v102_analysis_lock|pg_advisory_xact_lock|idle in transaction" origin/main -- docs/adr` → ADR-1037（移行の鍵待ち 1 秒・反映前の点検）・ADR-1070（接続の返却時の後始末）の 2 本。解析の取引の切り方を決めた ADR は無い。

## 1. 本番の観測（事実）

生出力: /tmp/CC報告ファイル/replay-bin2/analysis-hold-sample-20261112T023025Z.txt（PO 同意票「1」・2026-11-12 11:30〜12:03 JST・2 秒ごと 900 回・BEGIN READ ONLY で pg_stat_activity を読むだけ）。

| 取引の始まり（JST） | 送り元 | 最後の文 | 見えた長さ | 作業係の記録との突き合わせ |
|---|---|---|---|---|
| 11:41:21 | 172.19.0.2（旧作業係） | 投稿日の SELECT | 13 秒以上 | 記録なし（反映で作業係が入れ直され消えた） |
| 11:41:24 | 172.19.0.2 | 同じ | 4 秒以上 | 同じ |
| 11:44:40 | 172.19.0.3（新作業係） | 同じ | 39 秒以上 | 同じ |
| 11:44:50 | 172.19.0.3 | 同じ | 35 秒以上 | 同じ |
| 11:53:25 | 172.19.0.3 | 同じ | 7 秒以上 | 11:53:24.514 starting v102 analysis → 11:53:32.915 v102 job= で一致 |
| 11:53:36 | 172.19.0.3 | 同じ | 7 秒以上 | 11:53:35.702 → 11:53:44.453 で一致 |
| 11:59:32 | 172.19.0.3 | 同じ | 2 秒以上 | 11:59:31.713 → 11:59:34.465 で一致 |

- 読み取りの間に本番反映が 2 回あった（gh run 43142604068：作業係の入れ直し 02:43:47Z・gh run 43142891628：02:50:11Z）。作業係の記録は入れ直しで消えるので、11:41 と 11:44 の 4 件は作業係の解析か試しの道具か確定できない（未確認）。
- 7 件とも、取引の始まりからの秒数（xact_sec）と最後の文からの秒数（idle_sec）の差は 0〜1 秒。読み取りは 1 秒未満で終わり、残りは全部「最後の文（投稿日）の後の待ち」。
- 作業係の記録で確かめた解析 4 回（03:03:07 の 0.7 秒を含む）の長さは 0.7・2.8・8.4・8.8 秒。

## 2. コード（事実）

### 2-1 取引の流れ（backend/app/services/line_analysis_v102_svc.py）

- :1537 取引の最初に `pg_advisory_xact_lock(v102_analysis:<job>)`。取引が終わるまで鍵を持つ。
- :1538-1565 読み取り: 文脈（load_extraction_context）・job（gemini_unsure・review_reasons）・件（extraction_items）・マスタ（load_v102_masters :1554）・人の判断（load_v102_decisions :1559）・前の組（_load_resolved_pairs :1561・_load_current_pairs :1563）・続きの参照（load_followup_reference）・売り切れの参照（load_soldout_ref_posts）・投稿日（load_posted_date :1566）。
- :1568 `run_v102_pipeline`（:355-401）。DB を使わない計算。ここで取引が開いたまま待つ。
- :1569 `_write_results`（書き込み）→ :1570 commit。失敗は :1572 rollback → :1574 理由を書いて :1576 commit。
- :1552-1553 の早い return（応答が読めなかった投稿）は commit も rollback もしない（取引は呼び出し元へ持ち越す）。
- :1560 `_fixed_products`（人が決めた商品の位置。マスタを使う計算）は読み取りの途中にある。§1 で読み取り全体が 1 秒未満なので、この計算は短い。
- :1578-1580 `_merge_supplier_products` は commit の後の別の取引。
- 同じファイルの Gemini 段は既に「外部呼び出しの間、DB の取引を持ち越さない」として :491 で commit してから呼ぶ（先例）。

### 2-2 同じ鍵を取るほかの場所（＝解析の間ずっと待たされる）

| 場所 | 何をする | 誰が使う |
|---|---|---|
| backend/app/services/v102_human_decisions_svc.py:593 | 人が直した値の保存（save_value_override） | 要確認の画面のスタッフ |
| backend/app/services/v102_transcription_svc.py:358 | 書き写しの直しの保存（apply_transcription_edit） | 要確認の画面のスタッフ |
| backend/app/services/tcg_analyzer_svc.py:1546-1549 | v6 の解析 | v6 の投稿のやり直し |

- 鍵の意味（v102_human_decisions_svc.py:470-472）:「システム段と保存が共有する advisory lock の鍵」。保存と解析が交差して、人の判断の読み込みと書き込みがずれるのを防ぐ。
- 解析が鍵を持つ 8〜39 秒の間、同じ投稿のスタッフの保存はその分待つ。実際に待たされた件数は未確認（数えていない）。

### 2-3 呼び出し元

- backend/app/tasks/tcg_extraction.py:476（投稿が届いた後の解析。作業係）・:746（やり直し reanalyze_v102_job。run_v102_analysis の後に UPDATE と commit）・backend/app/services/tcg_analyzer_svc.py:1442・backend/app/tools/reextract_v6_with_v102.py:393。
- 4 つとも run_v102_analysis の中の取引の切り方を変えれば、そのまま効く。

### 2-4 比べる値の形（事実）

- 文脈 ExtractionContext は NamedTuple（backend/app/tasks/tcg_extraction.py:256-264）。人の判断 Decisions・ValueOverrides は frozen dataclass（backend/app/services/v102_human_decisions_svc.py:95-121）。前の組は tuple の list。件は SQLAlchemy の Row。売り切れの参照 SoldoutRefPost は frozen dataclass（backend/app/services/gemini_raw_copy_v102_soldout_ref.py:90-91）。どれも `==` で中身を比べられる形。続きの参照は tuple か None、投稿日は date か None。

### 2-5 反映前の点検（ADR-1037）

- scripts/deploy-db-precheck.sh:27-30・:69-70: 5 秒おきに「取引の始まりから 5 秒より長い idle in transaction」を数え、3 回続けて 0 本で通す。上限 600 秒。
- 解析 1 回が 5 秒を超えると、その間の数えは 1 本になり、続けての数えが 0 に戻る。投稿が続けて届く時間は通りにくくなる。

## 3. 未確認

- U1 11:41・11:44 の 4 件（最長 39 秒以上）が作業係の解析か試しの道具か。同じ入れ物の中で動かした道具は送り元の住所が同じなので、住所では区別できない。
- U2 スタッフの保存が解析の鍵で実際に待たされた回数と長さ。
- U3 計算（run_v102_pipeline）の時間が投稿の何で決まるか（件数か原文の長さか）。
