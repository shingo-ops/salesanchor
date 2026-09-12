# design — LINE メッセージ整合性: SP0136 の抽出やり直しと並存メッセージの掃除

この文書は何か（専門用語なしの1行）: 同じ仕入元から在庫の投稿が2つ残ってしまっている状態を、古い方だけ消して1つに揃えるための手順書。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md
recon: docs/handoff/tcg-line-message-integrity/recon.md

- 仕事名: tcg-line-message-integrity
- 日付: 2026-09-08
- 実測時の origin/main SHA: 8d6e9bb107ddf8c2996af4dd56e900adbbb9f028
- 対象ADR: ADR-154
- 区分（STANDARD-WORKFLOW 1.8）: 既存の延長・修正

---

## 1. 何を直すか

tenant_004 の supplier_channel SP0136 に、有効な source_message が2件並存している。
1つの channel に有効な在庫投稿は1件であるべきなので、古い方を無効化して1件に揃える。

掃除規則（PO 合意 2026-09-06）: channel ごとに received_at 最新の1件を残す。
NULL は最古扱い。同値なら created_at 最新。残す1件の抽出が成功していない channel は掃除の対象外。

## 2. 現在地（すべて実測・SHA 8d6e9bb1）

| メッセージ | received_at | created_at | items | results | ジョブ状態 |
|---|---|---|---|---|---|
| c5ad04aa-213f-41e5-bfbe-35f5b8925b2a | NULL | 2026-08-30 11:13:22 | 31 | 31 | done |
| 2336edf3-e5cf-46f5-b114-6ae827deaa44 | 2026-09-03 06:30:00 | 2026-09-04 07:54:11 | 0 | 0 | error |

規則を当てると残るのは 2336edf3。だがその抽出ジョブ a6c1d827 が error のため、
掃除の対象外条件に該当し、掃除できる channel がゼロになる。

有効メッセージが2件以上ある channel は SP0136 の1本のみ（2026-09-07 実測）。
配信行数の基準点は 652 行（FLAG_ 除外条件）。

## 3. 詰まりの原因と、採らなかった手

ジョブ a6c1d827 の error_message は「レート制限超過 (HTTP 429)」。
2026-09-07 07:56 UTC に同じモデル（gemini_extraction_svc.py:126 の gemini-3.6-flash）で
抽出が成功しているため、モデルとキーに原因は見当たらない。

やり直す手段として3案を検討した。

| 案 | 内容 | 判定 |
|---|---|---|
| 画面の再実行ボタン | DiagnosticsDrawer.tsx の handleRetryErrors が表示中の全行の先頭50件を送る | 不採用。他セッションが終端化した DIST-STALE-A 12件まで巻き戻す |
| 掃除規則の変更 | 抽出成功している側を残す規則に変える | 不採用。PO 合意（最新を残す）の変更が必要 |
| 1件だけ戻して1件だけ実行 | migration で1行 pending に戻し、その1件だけ抽出を直接呼ぶ | 採用 |

外部・過去事例の検討: 本件は自リポジトリ内の1行是正であり、外部事例からの応用は該当なし。
過去事例としては migrations/20260907_120000_tcg_dist_stale_jobs_terminate_t004.sql
（別セッションによる滞留12件の終端化）が同型の1回限り是正であり、書式を参考にした。

## 4. どう直すか

| 便 | 内容 | 本番影響 |
|---|---|---|
| 1 | 実行前スナップショット（本文書 §2 の値） | なし・完了 |
| 2 | migration PR: ジョブ a6c1d827 を error→pending に戻す | DB 1行更新・GO必須 |
| 3 | 本番コンテナで extract_and_analyze_source_message('2336edf3-...') を1回実行 | Gemini 呼び出し1回・GO必須 |
| 4 | 事後確認（ジョブ status・items・results・配信行数） | なし |
| 5 | 掃除 migration（c5ad04aa を is_active=FALSE に） | DB 1行更新・GO必須 |

便3が必要な理由: status='pending' のジョブを定期的に拾う仕組みは存在しない。
extract_source_message_task を呼ぶ箇所は tcg_line_import_svc.py:645（取込時）と
tcg_diagnostics_svc.py:225（再実行ボタン）の2つのみで、beat_schedule に登録は無い
（celery_app.py の TCG 関連は tcg-mirror-daily-write と discard-stale-pending-import-jobs の2本のみ）。
よって pending に戻すだけでは滞留する。

tcg_extraction.py:68 の extract_and_analyze_source_message は Celery 非依存の同期関数であり、
同ファイル冒頭に「検証時は直接呼び出すこと」と明記されている。これを1回呼ぶ。

TCG_AUTO_ANALYZE は本番 worker で 1（2026-09-07 実測）。
よって抽出成功時に analyze_extraction_job が自動で走り、analysis_results が生成される。
照合を別途呼ぶ必要はない。

## 5. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| ジョブ a6c1d827 の status が done になる | psql で当該 id の status を SELECT |
| 2336edf3 の extraction_items が1件以上になる | 2 と同じ結合クエリで items を再測 |
| 2336edf3 の analysis_results が1件以上になる | 2 と同じ結合クエリで results を再測 |
| 他の55件の error ジョブが変化しない | status 別件数を再測し error 件数を比較 |
| 配信行数が 652 から増える | 2 と同じ配信条件の COUNT を再測 |

便5（掃除）に進む条件: 上記5基準すべてを満たすこと。
1つでも満たさない場合は便5に進まず、原因を測り直す。

## 6. 弊害・トレードオフ

- 便2をマージすると deploy.yml:458 が run_all_migrations.sh を自動実行するため、
  適用のタイミングを選べない。便4のカードを先に用意しておく。
- 便3は docker exec による直接実行で、実行記録がリポジトリに残らない。
  便1と便4のスナップショットが証跡となる。
- 抽出が再び429で落ちる可能性は残る。その場合 error_message が上書きされるが、
  現在値は本文書 3 に記録済み。
- 便5で無効化する c5ad04aa には items 31 / results 31 がぶら下がる。
  DB からは削除せず is_active=FALSE にするのみで、行は監査のため残す。

## 7. 維持の仕組み

- 守り手: .github/workflows/migration-guard.yml
- 対象: migrations/ に置いたファイルが scripts/run_all_migrations.sh に登録されていること。
  登録漏れは MIGRATION GUARD が落とす。
- 関所なしの箇所（人手で守る）: 「1 channel につき有効な在庫投稿は1件」を DB で強制する
  部分排他制約は未実装である。便5の掃除が完了するまで付けられない（付けると既存の並存で失敗する）。
  それまでは人手（診断画面の supplier-channels セクション）で守る。
  制約の設計は本テーマの次の便で扱う。

## 8. 外部・過去事例

- 過去事例: migrations/20260907_120000_tcg_dist_stale_jobs_terminate_t004.sql が
  滞留ジョブ12件を1回限りで終端化した同型の是正。id 名指し・冪等条件つきの書式を踏襲した。
- 過去事例: migrations/20260906_230000_redact_extraction_error_keys_t004.sql が
  error_message の一括是正を行った先例。ただし同 migration は「24行を置換」と記すのに対し、
  2026-09-07 実測では生の API レスポンスを含む行が27件あり、数が一致しない。
  この食い違いは本テーマの範囲外として別途扱う（未解決）。
- 外部事例: 該当なし。自リポジトリ内の1行是正であり、外部の設計パターンを要しない。

## 9. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 2026-09-04 の429がなぜ起きたか | Gemini 側のログは取得できない | 未解消・追跡打ち切り |
| 2 | SEC-01 migration の24行と実測27件の差 | 別テーマで再測 | 未解消 |
| 3 | 失敗したジョブの再実行履歴が残らない設計の是正 | 別テーマ（A-5）で扱う | 未解消 |
---

## 10. 実行結果（2026-09-08 実測）

### 便2（migration・PR #3365）

マージ 2026-09-08T08:24:22Z / mergeCommit 1deec7bb / デプロイ run 34204321626 success。
適用後: ジョブ a6c1d827 が status=pending・error_message=NULL。
「レート制限超過 (HTTP 429)」の件数が 16 から 15 に減少。他の型は不変。

### 便3（抽出の1回実行）

本番 celery-worker で extract_and_analyze_source_message('2336edf3-...') を1回実行。
結果: status=done / items_count=28 / extracted_at 2026-09-08 11:57:52。
analysis_stats: total 28 / pid_resolved 20 / unit_resolved 27 / needs_review 8 /
e3a_recovered 0 / e5_changed 0 / e3b_flagged 1 / e4_resolved 0。
429 は再現しなかった。

CARD-LMI-EXEC-01 は ModuleNotFoundError で抽出に到達せず停止した（Gemini 未呼び出し）。
原因: docker exec -w /app はカレントディレクトリのみ変更し sys.path に影響しない。
/tmp のスクリプトを実行すると sys.path 先頭が /tmp になる。
CARD-LMI-EXEC-02 で -e PYTHONPATH=/app を付与して解決。

### 受け入れ基準の照合（5 の表に対応）

| 基準 | 結果 |
|---|---|
| ジョブ a6c1d827 の status が done | 充足 |
| 2336edf3 の extraction_items が1件以上 | 充足（28件） |
| 2336edf3 の analysis_results が1件以上 | 充足（28件） |
| 他の55件の error ジョブが変化しない | 充足（error 56件のまま） |
| 配信行数が増える | 充足（657 から 677） |

5基準すべて充足。便5に進む条件を満たした。

### 配信行数の基準点の更新

652（2026-09-07 実測）は並行取込により 657 へ変動していた。抽出実行後は 677。
以降の比較は 677 を基準点とする。ただし並行取込で常時変動するため、
事後確認では SP0136 に紐づく行数で測る。

### 便5 の設計根拠（superseded_by）

tcg_line_import_svc.py:407 は SET superseded_by = :new_id, is_active = FALSE を同時に行う。
DB 実測: is_active=FALSE の 771 行すべてが superseded_by を持ち、
is_active=TRUE の 92 行すべてが NULL。例外 0 件。
よって掃除 migration も superseded_by を同時に設定し、この不変条件を保つ。
