# design.md — rule-drawer-simplify

参照: [recon.md](./recon.md)

## KGI

画面上で「新規作成ドロワー」を開いたとき:
1. status_id フィールドが存在しない（フォームに表示されない）
2. ステータス（canonical）が Select ドロップダウンで表示される
3. 判定ボタンを押してマッチしたときのみ「作成」ボタンが有効になる
4. 作成リクエストに `status_id` を含めなくてもバックエンドが ST0001 形式で自動採番する

## 検証方法

| 基準 | 検証方法 |
|---|---|
| status_id フィールドなし | ドロワーを開いて DOM に `data-testid="rule-create-status-id"` が存在しないことを確認 |
| canonical が Select になった | `data-testid="rule-create-canonical"` が `<select>` タグであることを確認 |
| テストゲート | 判定前は作成ボタンが disabled、マッチ後のみ enabled になることを確認 |
| 自動採番 | POST リクエストに status_id を含めず、レスポンスに `ST\d{4}` 形式の status_id が返ることを確認 |

## 変更内容

### Backend

1. `backend/app/schemas/central_masters.py` — `TcgStatusMasterCreate.status_id` を `Optional[str] = None` に変更
2. `backend/app/routers/super_admin_status_master.py` — `create_status_master` に auto-generate ロジック追加（`ST{MAX+1:04d}` パターン）

### Frontend

3. `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx` — 全面書き換え
   - 削除: status_id TextField、match_type Select、exclude_pattern TextField
   - 変更: canonical → Select（`/super-admin/rule-tests/canonicals` から取得）
   - 追加: testPassed state（ゲート）
   - 変更: 作成ボタン disabled 条件 `!testPassed || creating`

4. `frontend/src/locales/ja.json` / `en.json` — ruleManagement.create キー整理

## 影響範囲

- 変更: `RuleCreateDrawer.tsx` のみ（AnalysisRulesPage.tsx は props 変更なし）
- 変更: `TcgStatusMasterCreate` スキーマ（CSV インポートには影響しない — 別パス）

## 外部・過去事例の参照と我々への応用

テストゲートパターン（フォーム送信前に動作確認を必須とする）は GitHub Actions の required status checks と同じ思想。未テストでの誤登録を防ぐ。フォーム内プレビュー→ゲート解放はフォームバリデーションの標準プラクティス（例: Stripe の支払い前確認フロー）に沿っている。

## 維持の仕組み

守り手:
- TypeScript コンパイル: `frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx`
- i18n キー整合: `frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の ruleManagement.create 以下
- Backend syntax: `backend/app/routers/super_admin_status_master.py`、`backend/app/schemas/central_masters.py`

## 戻し方

PR を revert するだけで元に戻る。DB スキーマ変更・マイグレーションなし。
