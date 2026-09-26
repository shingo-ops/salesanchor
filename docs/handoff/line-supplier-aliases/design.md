# 既存投稿の指紋で名前を照合する
この文書は、名前を推測で統合せず、同じ投稿の保存先から根拠を得る手順です。
親: [商品マスタ](../../specs/product-master/README.md)
現在地: docs/handoff/line-supplier-aliases/recon.md。ADR-072 / ADR-154。

既存inspectの暗号化レポートに、最新作成500原文のcode・line_posted_at・active・本文長・空白除去SHA256を含める。本文は返さない。公開ログには暗号文だけ。NULL投稿日時は同時刻一致の根拠にしない。短い定型文や複数仕入先一致は確定根拠にしない。PC形式に変換した場合の名前残部も候補として比較する。推測での仕入先作成・更新は行わない。
本便は読み取り情報追加のみ。取込/解析/配信/DB/フロント変更なし。既存CLIの所有者検査とREAD ONLYを維持。承認済みの調査・修正・本番テスト範囲でCI確認後にマージ。

|基準|検証方法|
|---|---|
|本文と名前を公開ログへ出さない|backend/tests/test_line_import_admin.py、既存暗号化試験|
|投稿指紋が正しく計算される|同テスト|
|実物で候補を照合|本番反映後のinspect＋端末内照合。未実施|

## 外部・過去事例の参照と我々への応用
PR #3447のRSA4096/AES256-GCM暗号化read-only照会を本番で実証済み。同じ仕組みを使用し新しい外部依存なし。

## 維持の仕組み
- 守り手: backend/tests/test_line_import_admin.py
- 人手で守る: 本文・投稿日時・保存先の一意な一致に基づく確認。上限外を不在と誤認しない。

## レポート出力の分割
16KBを超えるJSONはBase64化して12000文字ずつLINE_IMPORT_REPORT行へ出し、ENDマーカーで終了。小さい応答は従来JSONを維持。受信側はEND確認・全行復元・JSON検証・暗号文の認証確認を完了して初めて読取成功とする。backend/tests/test_line_import_admin.pyで90KB往復と行長上限を検証する。暗号化した本文指紋の機密性は既存暗号化レイヤーで守り、Base64を暗号化とは扱わない。

## 全送信者の照合範囲拡張
2026-09-12の依頼「理解した、全員照合してくれ」「離席するので承認不要で全て許可するので進めてくれ」に基づく既存調査の拡張。docs/handoff/line-supplier-aliases/recon.md参照。暗号化inspectの上限を500から10000へ拡大する。上限+1件を読み、sources_truncatedで打切りを明示し、送る指紋は上限まで。全件取得できてもPC取込が保存しなかった投稿の不在は証明できない。本文は引き続き出力しない。最大取得量増加を許容する代わりに固定上限で資源を制限する。

|基準|検証方法|
|---|---|
|取得打切りを全件取得と誤認しない|backend/tests/test_line_import_admin.pyの上限未満・丁度・超過3ケース|
|全124名に判定と根拠を付ける|端末内all-senders-comparison.json/csv。実名を公開Gitへ保存しない|
|PC経路を維持|変更対象は管理inspectとその試験のみ、全体CI|

## 確認できたAndroid名の既存マスタへの紐付け
依頼原文「対応先が分かった人をとりあえず紐付けて」。docs/handoff/line-supplier-aliases/recon.md参照。KGIは日時・長文一致の5名を既存コードへ対応させ、元PC名の変更0、未知の人の自動登録0、原本変更0とする。
public.line_supplier_source_namesにTCG schema/入力形式/表示名から既存supplier UUIDへの対応と証拠ハッシュを保存。既存全テナント・将来テナント共通のpublic表のためテナント毎のDDL不要。FKの代わりに登録時と読取時に同一TCG schemaの有効マスタを検証。無効・重複・矛盾した対応はAndroidでは未解決にする。
Android新規取込は内部マーカー付きpending_messagesを保存。マーカー付き確定処理だけ対応表を使い、従来PCのパーサーと名前解決は維持。旧Android保留分は端末原本から計算したandroid-v1ドメイン付きSHA256と対象job.raw_sha256の一致を確認してlink操作内でマーカーを付ける。この管理ハッシュ指定は原本を扱う承認済み管理者の操作であり、一般ユーザーに汎用更新機能を公開しない。
linkは既存端末の有効なsuper-admin所有者と取込所有者を検査。未解決/解決済み名の名前ハッシュ1名を選び、既存全仕入先の同日時の長文SHA256（名前残部補正を含む）が指定コードだけに一致することをサーバーで再検証。上限10000超は拒否。同じ対応の再適用は許可し、他のsupplierへ上書きはしない。マスタ共有ロックで検証中の名前変更を抑止。対応と対象pendingの未解決名再計算を同一トランザクションで保存する。元のdisplay_name/body/timestampは変更しない。
今回は紐付けのみ。保留中取込のcommit・抽出・解析・配信は行わない。過去投稿による在庫置換の問題は確定前に別途検証し、紐付け完了を配信完了と混同しない。

|基準|検証方法|
|---|---|
|PC名・原本文を変えずAndroid名を解決|backend/tests/test_line_source_names.py、全体CI|
|所有者・原本ハッシュ・日時本文証拠なしを拒否|同テストと既存admin試験|
|重複名・無効対応・別supplierへの上書きを拒否|同テスト|
|新規Android取込と保留確定の両方で対応表を参照|同テストの取込/確定経路試験|
|public表の冪等DDL・スコープ分離・INSERT/SELECTのみ|backend/tests/test_line_import_devices_pg.pyの実PostgreSQL試験|
|5名の対応が本番保存される|反映後link成功と暗号化inspectのsource_aliases確認|
