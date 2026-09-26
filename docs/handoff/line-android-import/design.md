# Android LINE履歴をTermuxから取り込む

この文書は、Androidで保存したトーク履歴を既存の在庫解析へ渡す方法を記録する。
親: [商品マスタ](../../specs/product-master/README.md)
現状: [recon.md](recon.md)
現状のリポジトリパス: docs/handoff/line-android-import/recon.md
対象ADR: ADR-072（既存のschema修飾を維持）、ADR-154（既存の解析パイプラインへ接続）。新しいDB操作や解析ロジックは追加しない。
関連: [既存の取込・解析・配信契約](../pmg-import-delivery-ssot/design.md)

## 合意した範囲

2026-09-12、ユーザーはAndroid専用API・Termux送信・フロントエンド不要の構成に「合意」と回答し、実装開始を指示した。GitHubの引き継ぎはIssue #3437。
PC用画面・API・パーサーを維持する。取引先確認と解析は既存の共通サービスを使う。新着LINEの自動取得はこの変更に含まない。

## API契約

POST /api/v1/tcg/line-import/android。既存と同じrequire_super_admin／Firebase MFA認証。新しい認証バイパスは追加しない。
fileはUTF-8の.txt、10MiB以下。window_hoursは0以上、既定0（全期間を共通処理へ渡す）。PC入口の既定24時間は維持。
AndroidではYYYY/M/D(曜日)と時刻・送信者・本文のタブを解析する。送信者内のスペースを分割しない。継続行・空行は保持、改行コードはLFへ正規化。原本はTermuxにバイト単位で保持。
読めない形式・0メッセージは400、サイズ超過は413、負のwindow_hoursは422。PC形式のファイルはAndroid入口で拒否する。
同じ共通サービスへsource_format=androidを明示。PCのパーサーとアップロード関数は変更しない。Android冪等キーは形式接頭辞＋原文のSHA256でPCから分離し、誤ってPC入口へ送ったAndroid履歴の0件記録で再試行が塞がれないようにする。
取引先確認待ち・投稿の同一性・取引先別最新投稿の採用・commit後の解析開始は既存契約を維持。全件が在庫解析されるとは約束しない。

## Termux契約

共有後に原本を保存し、SQLiteキューへ登録。同一ファイルはSHA256で二重登録しない。送信先HTTPSはAndroid専用APIに固定。リダイレクトへ認証情報を転送しない。
失敗時は原本を残し、次回共有またはsendで再送。401/403は認証待ち、400/413/415/422は要調査、pending_reviewは確認待ち、okはAPI受付済み。解析完了とは区別する。
認証ファイルは端末内600。IDトークン手動設定は暫定で期限切れ時に再設定。ユーザーの普段のログイン方法・更新トークン運用は未確定。送信はAPI導入と認証設定が完了してから有効にする。

## 受け入れ基準と検証

| 基準 | 検証 |
|---|---|
| スペース入り送信者、複数行、空行、末尾を保持 | test_tcg_line_android_parser.py、実ファイルの件数確認 |
| 不正ファイルと権限不足を拒否 | test_tcg_line_android_api.py |
| 未登録送信者の原文を保留して解析しない | 同APIテストの共通サービス試験 |
| PC入口の挙動を維持 | test_tcg_line_import.pyと関数ASTの差分確認 |
| 通信失敗・重複・確認待ちを扱う | tools/termux-line-import/test_android_import.py |

## 外部・過去事例の参照と我々への応用

[LINE公式の履歴出力](https://help.line.me/line/smartphone/?contentId=20007388&lang=ja)に対応する。通知転送の成功例は全文取得の根拠として使わない。
実ファイル2,048,526 bytesに対し旧パーサー0件、新Androidパーサー1,129件・123送信者・複数行1,035件。実ファイル・本文・認証情報は公開リポジトリに含めない。

## 弊害・トレードオフ

本文内の日付単独行・時刻とタブの組合せには形式上の曖昧性がある。原本を保持して追加サンプルで検証する。日付変更直前の空行も保持するため、PC経路の本文正規化と異なり、異なる形式間で同じ投稿の再利用が成立しないことがある。
ファイルの日時窓を変更しても同一ファイルの再取込は既存と同様に冪等である。専用クライアントはwindow_hours=0固定。
原文が同じで同じ分の投稿は、既存の投稿同一性条件の限界を継承する。

## 維持の仕組み

- 守り手: backend/tests/test_tcg_line_android_parser.py
- 守り手: backend/tests/test_tcg_line_android_api.py
- 守り手: backend/tests/test_tcg_line_import.py
- 人手で守る: 実トークとの全文照合、MFA認証の設定、API導入後の端末共有操作。DB移行・本番データ操作は本変更に含めない。

## 追補 2026-09-17：受信通知・経過履歴・定期点検・原本1件保持

この追補は、LINEから共有したtxtがアプリに入ったか・どこで止まったかを、スマホの通知と履歴でわかるようにする設計である。
現状: [recon.md](recon.md) の「追補 2026-09-17」（docs/handoff/line-android-import/recon.md）。対象ADR: ADR-072・ADR-154（変更なし。backend・DB・APIに触れない）。

### KGI（PO承認 2026-09-17）
| 基準 | 検証方法 |
|---|---|
| 共有1回ごとに「受信」と「結果（完了／確認待ち／失敗＋理由）」の通知が出る | 実機で本番送信3回＋通信遮断1回。tools/termux-line-import/test_android_import.py の通知テスト |
| 詰まり判定時間を超えた未完了ジョブで通知が出て、履歴に いつ・どこで・何が・なぜ・どう検知・何分・何回 が残る | 実機で通信遮断して判定時間の経過を待つ。同テストの時刻差し替えテスト |
| 通信が戻ると、次の定期点検（15分周期）で自動再送される | 実機で通信を戻し次回点検を確認。同テストの check テスト |
| 送信後、端末に残る原本（state/originals と inbox）は最新1件だけ | 実機でファイル数を数える。同テストの整理テスト |
| 送信処理は通知が失敗しても止まらない | 同テストで通知を失敗させるテスト |

### 変更範囲
- 変更: tools/termux-line-import/client.py、tools/termux-line-import/termux-file-editor、tools/termux-line-import/test_android_import.py、tools/termux-line-import/README.md。新規: tools/termux-line-import/line-import-check。
- 触らない: backend/、frontend/、device_session.py、android_parser.py、送信先・認証・window_hours=0（別作業）。

### 技術How
1. 履歴（既存 outbox.sqlite3 に追加。新しい保存先は作らない）
   - `events` テーブル：id, at（UNIX秒）, digest, stage, result, reason, http_code, elapsed_seconds, detected_by。本文・トークン・応答本文は保存しない。
   - stage：received（受信）／store（原本保存）／parse（形式確認）／send（送信）／check（定期点検）／cleanup（整理）／notify（通知）。
   - detected_by：share（共有時）／check（定期点検）／manual（手動send）。
   - `jobs` に received_at・last_attempt_at・finished_at を列追加（既存DBは ALTER TABLE で追加、既存行はNULL）。
   - 90日より古い events と、原本が消えた90日超の jobs 行は点検時に削除する。
2. 通知
   - termux-notification を絶対パスで、10秒タイムアウト付きで呼ぶ。失敗・タイムアウトは events に notify/failed として残し、例外を外に出さない。
   - 通知IDは用途別に固定（受信・結果=4201、詰まり=4202）し、同じ種類の通知は上書きする。
   - 文面：受信「LINE取込：受信しました（送信中）」。結果「取り込み完了 投稿N件」／「取り込み完了・取引先確認待ちN件（PC画面で確認）」／「失敗：<理由>（原本は保持）」。詰まり「詰まり：<受信時刻>から<分>分未完了／段階<stage>／理由<reason>／再送<回>回」。
3. 定期点検（`line-import check`）
   - 排他ロックは非待機で取り、取れなければ何もせず終了する（共有中の処理を妨げない）。
   - 手順：古い履歴の削除 → 再送時刻を過ぎたジョブの再送 → 未完了ジョブ（queued/retry/auth_required）で `now - received_at >= stall_seconds` のものを詰まり通知。
   - `stall_seconds` は config.json に置く。未設定の間は詰まり通知を出さず、`status` に「詰まり判定時間：未設定（計測後に設定）」と表示する。設定は `line-import set-stall <秒>`。値は実機計測の最大所要時間＋余裕で決め、PO合意後に設定する。
   - 登録は `line-import schedule`（termux-job-scheduler --job-id 4201 --period-ms 900000 --persisted true --script ~/bin/line-import-check）。
4. 原本1件保持
   - 新しいtxtの enqueue が成功したら、それ以外の未完了ジョブは superseded にする。LINEの履歴出力は全履歴を含むため、新しいファイルが古いファイルを包含する。
   - 最新以外の原本と、inbox の received-* を削除する。削除対象は、inbox 直下の received-* ディレクトリと、originals 直下の <64桁hex>.txt に限る。シンボリックリンクはたどらない。
   - `line-import cleanup --dry-run` で消す対象を一覧表示し、`cleanup` で実行する。
5. 手動確認：`line-import history [件数]` で履歴を日本時間で表示する。`status` に最新ジョブの状態と経過時間を追加する。

### 計画
1. 実装とテスト（unittest）。
2. PR作成（Draft）。
3. 端末の現行版をバックアップし、新版を配置。
4. `cleanup --dry-run` の一覧をPOに提示し、合意後に実行。
5. 本番送信3回で所要時間を計測。
6. 判定時間をPOと合意して設定し、`schedule` を登録。
7. 通信遮断テスト。
8. 結果を本書と docs/ai-agents/evidence-registry.md に記録し、PRを更新。

### KPI
- 通知の表示率：共有回数に対する結果通知の数（100%）。
- 共有から結果通知までの所要秒（実測の最大と中央値）。
- 詰まり検知の遅れ：判定時間を超えてから通知が出るまでの秒数（15分以内）。
- 端末に残る原本の数（1）。

### 弊害・トレードオフ
- Androidの予定実行は最短15分で、省電力で遅れることがある。そのため、詰まりの検知は判定時間から最大15分以上遅れうる。
- 最新1件だけを残すため、古いファイルを後から再送することはできない。アプリ側に取り込み済みであることで代替する。
- 未送信の古いファイルは superseded として送らない。新しいファイルが全履歴を含むことが前提で、この前提が崩れる形式変更があった場合は見直す。
- 通知はTermux:APIアプリに依存する。アプリが消えると通知だけが出なくなるが、送信は続く。

### 外部・過去事例の参照と我々への応用
- termux-job-scheduler の公式ヘルプ（端末で確認）にあるとおり、最短周期は15分で、--persisted で再起動後も残る。常駐プロセスは使わず、この予定実行を採用する。
- Termux:API の README（github.com/termux/termux-api）にあるとおり、Termux本体と同じ入手元（F-Droid）のアプリが必要。導入手順を README に追記する。
- 送信箱（outbox）方式で、送れなかったものを後で再送する。既存の client.py の再送間隔を踏襲し、定期点検でその再送を実際に走らせる。

### 実機計測と決定（2026-09-17）
| 回 | 受信 | 受信→完了 | 結果 |
|---|---|---|---|
| 1 | 17:58:54 | 4.4秒 | pending_review（投稿1,698件・確認待ち33件） |
| 2 | 17:59:27 | 1.8秒 | 同上 |
| 3 | 18:00:18 | 0.8秒 | 同上 |
- 3回とも受信・結果の通知が表示された（PO確認）。送信後の端末原本は originals 1件・inbox 0件。
- 詰まり判定時間は PO決定で60秒（`set-stall 60`）。送信中は点検が排他ロックで待たずに終了するため、送信中の誤検知はない。点検周期は PO決定で15分（Androidの最短周期。常駐方式は電池・停止リスクのため不採用）。
- 実機で判明：termux-job-scheduler の既定は「ネットワーク接続時のみ・電池残量低下時は実行しない」だった。圏外で点検が止まると詰まりを検知できないため、`schedule` は `--network none --battery-not-low false` で登録する。登録直後に点検が1回実行されることを events で確認。点検は毎回 `check ok` を記録する。
- 通信遮断テスト（2026-09-17）：機内モードで19:24:51共有→即時に失敗通知。19:45:09の点検で受信20分、19:48:43の点検で受信23分の詰まりを検知し、通知が表示された（PO確認）。理由は「通信できません（圏外・タイムアウト等）」。機内モード解除後、20:03:41の点検で自動再送され、pending_review（投稿1,702件）になった。KGI 5項目は全て実機で確認済み。
- 同一内容の再共有（2026-09-17 22:06、自動書き出し試験で発生）：既に取り込み済みのため送信されず、結果通知も出なかった。KGI「共有1回ごとに結果通知」を満たさないため、`send/duplicate` を記録し「取り込み済み（同じ内容のため送信なし）」を通知するよう修正（unittest追加）。
- 手順上の反省：`cleanup` の一覧をPOに提示した後、PO回答前に共有テストを依頼したため、自動整理で古い原本11件（提示10件＋当時の最新1件）が回答前に削除された。以後、削除を伴う操作は回答を得てから依頼する。

### 維持の仕組み（追補分）
- 守り手: tools/termux-line-import/test_android_import.py
- 人手で守る: 実機の通知表示・予定実行の登録状態・判定時間の値。理由：Android端末上の状態でCIからは確認できない。
