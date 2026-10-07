# design: staff_code を常にサーバー側で自動採番

recon: docs/handoff/staff-code-auto-number/recon.md

対象ADR: ADR-023（staff ライフサイクル。staff_code 採番そのものを規定する ADR は無い）

## KGI
スタッフ新規登録が保存でき、スタッフコードが `EMP-00001` 形式で自動付与される（登録画面にコード欄は無い）。

## KPI（観測可能な事象）

| 基準 | 検証方法 |
|------|---------|
| 登録画面にスタッフコード欄が表示されない | `frontend/src/components/StaffFormButtonMigration.test.tsx` "create form has no staff code field" + 画面目視 |
| `POST /staff`（staff_code 無し）が 201 で `^EMP-\d{5}$` を返す | `backend/tests/test_staff_code_auto_number.py::test_create_staff_auto_numbers_sequentially` |
| 2 件目も連番（`EMP-{id:05d}`）で重複しない | 同上 |
| クライアントが staff_code を送っても無視される | `test_create_staff_ignores_client_staff_code` |
| 仮コードが VARCHAR(20) に収まる | `test_placeholder_code_fits_varchar_20`（SQLite は長さ非強制のため単体で担保） |
| 本番で保存が成功する | デプロイ後にスタッフを 1 件登録し 201・コードが `EMP-` 形式であること（PO 確認） |

## 変更方針
- `backend/app/routers/staff.py`: 仮コードを `"TMP-" + uuid hex 16桁`（20文字）に変更。定数 `STAFF_CODE_MAX_LENGTH = 20`（tenant.py:590 の列幅と同値）から長さを導出。常に INSERT 後 `UPDATE staff SET staff_code = 'EMP-%05d'`（採番式は従来どおり staff.id）。ADR-072 の `reset_tenant_context` は維持。
- `backend/app/schemas/staff.py`: `StaffCreate.staff_code` を削除（Pydantic は余剰フィールドを無視するため、送られても使われない）。
- `frontend/src/pages/staff/StaffPage.tsx`: 登録フォームのコード欄・state・payload を削除。未使用になった i18n キー `staff.staffCodeLabel` / `staff.staffCodePlaceholder` を ja/en 両方から削除（`staff.staffCode` は一覧/編集で使用中のため残す）。
- 触らない範囲: frontend/src/pages/staff/StaffEditPage.tsx（既存コードの表示・編集）、DataError の汎用エラー変換（スコープ外。新規マッピングは追加しない）。

## 影響範囲
- 呼び出し元: `POST /staff` を呼ぶのは frontend/src/pages/staff/StaffPage.tsx のみ（recon 参照）。
- 既存スタッフの staff_code は不変。

## 戻し方
PR を revert（DB マイグレーション無し）。

## 外部・過去事例の参照と我々への応用
INSERT 時に一意な仮値を入れ、採番確定後に UPDATE する従来方式（#101）を踏襲し、列幅超過だけを是正する最小修正。SQLite テストが VARCHAR 長を強制しない盲点は、長さ定数 + 単体テストで守る。

## 維持の仕組み
- 守り手: `backend/tests/test_staff_code_auto_number.py`（仮コード長 <= 20、EMP- 形式、連番）、`frontend/src/components/StaffFormButtonMigration.test.tsx`（コード欄なし）、CI の i18n キー parity チェック。
