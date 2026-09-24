# 端末取り込みが Form 既定値を下流へ渡さないようにする

対象ADR: ADR-100（取り込み・解析パイプライン。端末からの取り込み経路の不具合修正）
recon: `docs/handoff/fix-device-import-form-default/recon.md`（事象・原因・検出漏れの理由）

## 方針

`backend/app/routers/line_import_devices.py` の呼び出しで `window_start=None, window_end=None` を
明示的に渡す。あわせて、同種の事故を検出するテストを追加する。

より根本的には「エンドポイント関数を直接呼ぶ」構造自体をやめ、共通処理を素の関数へ切り出すのが
望ましいが、本便は**本番停止の復旧を最優先**とし、変更範囲を最小に保つ。構造の整理は別便とする。

## 受け入れ基準

| 基準 | 検証方法 |
| --- | --- |
| 下流へ Form オブジェクトが渡らない | 追加テスト `test_upload_passes_plain_values_not_form_defaults`（渡された値の型を検査） |
| 端末からの取り込みが 200 になる | デプロイ後に実機から送信し HTTP 200 / accepted を確認 |
| 既存テストを壊していない | CI（この環境は firebase_admin 未導入のため実行不可） |

## 外部・過去事例の参照と我々への応用

- FastAPI 公式の設計: `Form` / `Query` / `Depends` の既定値は**依存解決時に評価される**。
  エンドポイント関数を直接呼ぶと未解決のオブジェクトが渡る。公式ドキュメントでも、
  共有したいロジックは通常の関数に切り出すことが推奨されている。
- 同一リポジトリの先行事例: 2026-09-21〜23 の取り込み障害（`docs/handoff/line-import-schema-rewire/`、
  `docs/handoff/line-import-missing-channel/`）でも、モックが実態を隠して検出が遅れた。
  今回も「モックが型を検査していない」ことが検出漏れの原因で、同じ構図。
  よって本便では値ではなく**型**を検査するテストを足している。
- 一般的な慣行: 片方のシグネチャ変更がもう片方の呼び出し側を壊す関係は、呼び出し側に
  キーワード引数を明示することで検出しやすくなる（位置引数だと静かに壊れる）。

## 弊害・トレードオフ

- 「エンドポイント関数を直接呼ぶ」構造は残るため、引数が増えるたびに同じ注意が必要。
  コメントとテストで気づける形にしているが、構造的な解決は別便に委ねる。
- 同ファイルの既存 lint 指摘（E701, `backend/tests/test_line_import_devices.py:37`）を
  あわせて修正した。本便で同ファイルを変更するため、コミットフックの ruff が通らないため。

## 維持の仕組み

- 守り手: `backend/tests/test_line_import_devices.py` の追加テスト（型検査）
- 人手で守る: `upload_android_line_export` の引数を増やすときは、直接呼び出し箇所
  （`backend/app/routers/line_import_devices.py`）にも明示的に渡す
