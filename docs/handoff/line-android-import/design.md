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
