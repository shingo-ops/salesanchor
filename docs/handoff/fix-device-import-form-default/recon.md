# 端末からのLINE取り込みが全て500になった原因

対象ADR: ADR-100（取り込み・解析パイプライン。端末からの取り込み経路の不具合修正）

## 事象

2026-09-24 12:41 以降、端末からの取り込みが全て HTTP 500 になった。

```
最後の成功 12:26:31 (accepted HTTP200)
12:35      PR #3719 マージ・デプロイ
初回失敗   12:41:24 → 14:03 まで11回連続
応答       {"detail":"内部サーバーエラーが発生しました"}（DBエラーではなく未捕捉例外）
```

無効トークンでは 401 が返るため API 自体は正常。`window_hours` の値（0 / 未指定 / 6）を変えても
全て500で、パラメータ依存ではない（2026-09-24 実測）。

## 原因

`backend/app/routers/line_import_devices.py:72`（修正前）

```python
result = await upload_android_line_export(file=file, window_hours=window_hours, db=db, current_user=user)
```

この呼び出しは FastAPI のエンドポイント関数を **Python の関数として直接呼んでいる**。
PR #3719（`33a71362`）が `backend/app/routers/tcg_line_import.py:687-695` に
`window_start` / `window_end` を追加したが、この呼び出し側では渡していない。
FastAPI の依存解決を経ないため、渡さなかった引数には **`Form(...)` オブジェクトが
そのまま入る（None にならない）**。

実測（2026-09-24）:

```
Form既定値の型: Form（None ではない）
"2026-09-24 10:00:00" >= Form → TypeError: '>=' not supported between instances of 'str' and 'Form'
```

`window_start` は `backend/app/services/tcg_line_import_svc.py` の取り込み処理で
時刻比較に使われるため、`Form` が渡ると TypeError になり、`backend/app/main.py` の
未捕捉例外ハンドラが HTTP 500 を返す。

## なぜテストで検出されなかったか

`backend/tests/test_line_import_devices.py` の既存テストは
`upload_android_line_export` を `AsyncMock` に差し替えており、渡された値の**型**を検査していない
（`window_hours` の値だけを検査）。モックは Form オブジェクトを受け取っても例外にならない。
