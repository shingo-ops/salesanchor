# 既存仕入元の LINE チャネル欠落への対処

対象ADR: ADR-156（パイプライン用テーブルの public 移行）

## 方針

**チャネルが無ければ、その場で作って取り込みを続ける。** 未登録仕入元の自動登録
（`tcg_line_import_svc.py` の「4b. 未解決仕入元の自動登録」）と同じ扱いに揃える。
仕入元そのものが `public.suppliers` に無い場合は、従来どおり失敗させる
（黙って作ると正体不明の仕入元がマスタに増えるため）。

データ側の是正（`scripts/migrate-pipeline-data-to-public.sh` の再実行、または
バックアップからの復旧）は DB 作業のため本便には含めない。本便はアプリ側の防御のみ。

## 受け入れ基準

| 基準 | 検証方法 |
| --- | --- |
| チャネルが無い仕入元でも取り込みが成功する | 単体テスト `test_missing_supplier_channel_is_created_and_import_continues` |
| そのときチャネルが1件作られる | 同テストで `INSERT INTO public.supplier_channels` の発行を確認 |
| 仕入元自体が無い場合は従来どおり失敗する | 単体テスト `test_supplier_missing_from_public_still_raises` |
| 本番で「かやま」を含むファイルが200になる | デプロイ後に実データを送信し HTTP 200 と取込件数を確認 |
| 作成されたチャネルが記録に残る | `logging.warning("supplier_channel was missing and has been created: supplier_code=%s")` |

## 弊害・トレードオフ

- 欠落を自動で埋めるため、**データ移行の不備が表面化しにくくなる**。警告ログを必ず残し、
  多発する場合はデータ側の是正（移行スクリプトの再実行）を行う。
- 同時実行で同じ仕入元のチャネルが二重に作られうる。既存の自動登録経路と同じ性質で、
  取得時は `ORDER BY sc.id LIMIT 1` のため動作に影響しない。

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_line_import.py`（上記2テスト）
- 人手で守る: 警告ログの監視。多発時は `scripts/migrate-pipeline-data-to-public.sh` の
  実行状況を確認する（deploy には組み込まれていない手作業のため）。
