# recon: extraction-partial-success

## 現状把握

### 問題のある挙動（変更前）

| ファイル | 行 | 挙動 |
|---|---|---|
| `backend/app/services/tcg_work_reference.py:31` | validate_work_id | work_idがreferenceに存在しない場合 `raise ValueError("Work ID is not in the supplied reference")` |
| `backend/app/services/tcg_work_reference.py:43` | validate_product_code | product_codeがreferenceに存在しない場合 `raise ValueError("Product code is not in the supplied reference")` |
| `backend/app/tasks/tcg_extraction.py:208` | WORK_ID_CONFLICT | Geminiの resolved_work_id と証拠の work_id が不一致の場合 `raise RecordError("WORK_ID_CONFLICT")` |

### 下流はNoneを正常処理する（変更の根拠）

| ファイル | 行 | 挙動 |
|---|---|---|
| `backend/app/services/tcg_analyzer_svc.py:571` | match_pid_with_work | `resolved_work_id is None` のとき work_id フィルタをスキップ |
| `backend/app/services/tcg_analyzer_svc.py:404` | select_product_candidates | 候補0件のとき None を返す（raiseしない） |

### 問題の影響

- Geminiが存在しないwork_idやproduct_codeを返すと、そのアイテムだけでなく抽出ジョブ全体が失敗する
- `status='error'` になり、全アイテムが失われる
- 下流のアナライザは None を正常処理できるにもかかわらず、上流で例外が起きるため到達しない

## ADR検索結果

- `git grep -i "partial" docs/adr/` → 該当なし（partial success に関するADRなし）
- `docs/adr/FEATURE-INDEX.md` → TCG抽出パイプライン関連のADRなし
