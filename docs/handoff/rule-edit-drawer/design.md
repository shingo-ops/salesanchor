# design: rule-edit-drawer

## KGI

行クリックで編集 Drawer が開き、フォームが既存ルールで埋まった状態になる。
テスト合格後に「更新」ボタンが押せ、PATCH が送信されてリストが更新される。
有効なルール（enabled=true）の場合のみ「無効にする」ボタンが表示され、押下で PATCH {enabled: false} が送信される。

| 基準 | 検証方法 |
|------|---------|
| 行クリック → Drawer が開く | ブラウザで確認 |
| フォームに既存ルール値が事前入力される | Drawer 開いてフォーム値を目視確認 |
| テスト未合格 → 更新ボタン disabled | ボタン押下不可を確認 |
| テスト合格 → 更新ボタン有効 → PATCH 成功 | Network タブで PATCH 確認 |
| enabled=true のルール → 無効化ボタン表示 | Drawer フッター確認 |
| enabled=false のルール → 無効化ボタン非表示 | Drawer フッター確認 |
| 無効化後 onSaved() → リストリロード | リスト上の badge が「無効」に変わる |
| 新規作成ボタン → 空フォームで Drawer が開く | 「新規作成」ボタン押下確認 |
| i18n: ja/en キー完全一致 | Python スクリプト実行済み（85 keys / 85 keys） |
| TypeScript: エラーなし | `tsc --noEmit` 出力なし（node_modules symlink 経由） |

## 実装方針

### RuleDrawer.tsx（新規）

- `editRule?: RuleEntry | null` prop で create/edit を切り替え
- edit モード時: `useEffect([open, editRule])` でフォームを初期化（`ruleToFormDraft`）
- create モード時: `emptyDraft` でリセット
- テストゲート: `testPassed` が false の間は submit ボタン disabled（create/edit 共通）
- フォーム変更のたびに `resetTestState()` → テスト結果をリセット
- 無効化ボタン: `isEditMode && editRule.enabled` のときのみ表示、`variant="danger"`
- PATCH payload（update）: canonical / search_pattern / match_type / effect / priority / note のみ。status_id・enabled は送らない
- PATCH payload（disable）: `{enabled: false}` のみ

### RuleManagementPanel.tsx（変更）

削除した要素:
- `toggleTarget` state
- `toggling` state（toggle 専用、DataTable の disable ガードに使っていた）
- `handleToggleConfirm` async 関数
- `ConfirmModal` import / render
- `RuleCreateDrawer` import / render

追加した要素:
- `editRule: RuleEntry | null` state
- `drawerOpen: boolean` state
- `RuleDrawer` import / render（open / onClose / onSaved / editRule prop）
- `onRowClick` → `setEditRule(row); setDrawerOpen(true)`
- 新規作成ボタン → `setEditRule(null); setDrawerOpen(true)`

### i18n 追加キー

`ruleManagement.edit.*` を ja.json:4506 / en.json:4506 に追加。
既存の `ruleManagement.create.*` キーはすべて保持。

## 外部事例

- Salesanchor BotsPage.tsx — `useRecordDrawer` + Drawer の edit パターン参照
- 今回は `useRecordDrawer` フックを使用せず直接 state 管理（RuleEntry 型が固定のため、フック抽象化が過剰）

## 守り手

| リスク | ガード |
|--------|--------|
| PATCH で status_id を誤送信するとルールが別名に変わる | RuleDrawer.tsx:185 — payload に status_id を含めない |
| enabled=true の PATCH は backend test gate に引っかかる | 無効化のみ separately（enabled:false）。有効化は UI から行わない |
| ConfirmModal import が残ると lint エラー | RuleManagementPanel.tsx から削除済み（grep 確認済み） |
| i18n キー不一致 | Python 検証スクリプト実行済み：ja=85 / en=85、差分ゼロ |
| 旧 RuleCreateDrawer.tsx が残ると二重管理 | ファイルは残置するが RuleManagementPanel からの import は削除済み。将来的に削除可 |

## 外部・過去事例の参照と我々への応用

- **BotsPage.tsx** (`frontend/src/pages/bots/BotsPage.tsx:1`): `useRecordDrawer` + Drawer の create/edit 分岐パターン。今回は RuleEntry 型が固定のため useRecordDrawer を使わず直接 state 管理にした
- **ADR-122 バッチA**: 編集を Drawer 化する設計方針（BotsPage 改修時に策定）

## 維持の仕組み

- TypeScript で `RuleEntry` 型を `RuleDrawer.tsx` で export し、`RuleManagementPanel.tsx` で import → 型ミスマッチをコンパイル時に検出
- `tsc --noEmit` は CI で常時チェック
- i18n: 同一キーの存在を `scripts/check-i18n-keys.js`（CI）が強制（ja/en 差分ゼロ）
- `validate-pr-body.sh` が次回 PR 作成時にも `触るファイル:` 宣言を強制

## recon 相互参照

- 既存 ADR 検索: `docs/handoff/rule-edit-drawer/recon.md §既存 ADR 検索結果`
- PATCH 仕様: `backend/app/routers/super_admin_status_master.py:162-195`
- 変更スコープ: `docs/handoff/rule-edit-drawer/recon.md §変更スコープ`
