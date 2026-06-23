# ③-b(1) translation maintenance jobs tenant context design

## 目的

`translation.py` / `translation_monitor.py` / `sa02_recon_monitor.py` に tenant context を付与し、将来の RLS 有効化に備える。

## 実装方針

- 各 tenant ループ内で `set_tenant_context()` を呼ぶ。
- tenant 処理後に `clear_tenant_context()` で session context を戻す。
- `translation.py` はメッセージ単位で `reset_tenant_context()` を再適用する。
- data_deletion.py は別ステップで admin 接続隔離を検討するため、今回は触らない。
- recon: docs/handoff/translation-context-batch/recon.md

## 受け入れ基準

| 基準 | 検証方法 |
| --- | --- |
| 3経路が tenant ごとに context を設定・解除する | `backend/tests/test_translation_task_context.py` / `backend/tests/test_translation_monitor.py` / `backend/tests/test_sa02_recon_monitor.py` を実行 |
| 既存の翻訳テストが緑のまま | `pytest -q -o addopts='' backend/tests/test_translation_monitor.py backend/tests/test_sa02_recon_monitor.py backend/tests/test_translation_task_context.py` |
| 変更は session context 付与だけで、RLS 無しの本番挙動を変えない | `backend/app/auth/dependencies.py` の current_setting 系はそのままであることを確認 |

## 外部・過去事例の参照と我々への応用

`refresh_meta_tokens.py` と `maintenance.py` の `set_tenant_context_sync()` パターンを踏襲し、tenant ループの外で接続を取り直さずに session context を明示する。

## ADR

ADR-110
