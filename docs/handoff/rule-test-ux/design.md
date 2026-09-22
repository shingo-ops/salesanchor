# design: ルールテストUX改善

## 目的
非エンジニアがルールテストを迷わず使えるようにする

## 変更内容

### 1. ゲート説明（Card金型）
- 裸の GateBadge → Card variant="container" でラップ
- バッジ横に説明テキスト追加（i18n: gateDescription）

### 2. おすすめテストケース一括追加
- バックエンド: POST /super-admin/rule-tests/cases/seed
- tcg_status_master（SSOT）の LITERAL ルールから自動生成
- REGEX はスキップ（例文が主観的）、DEFAULT は固定テキスト
- 既存テストケースと重複チェック

### 3. フォーム平易化
- 「入力テキスト」→「商品ページの文言」（i18n: inputTextLabel）
- 期待値 → Select 金型ドロップダウン（GET /canonicals で取得）
- canonical 選択で除外チェック自動ON/OFF

### 4. ConfirmModal 化
- RuleManagementPanel の window.confirm → ConfirmModal 金型
- danger=true で無効化時、通常で有効化時

### 5. i18n
- ja.json / en.json に 6 キー追加

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| ゲート説明が Card 内に表示 | テストタブ表示で目視 |
| おすすめ追加で LITERAL 5件 + DEFAULT 1件生成 | ボタン押下→テーブルに6行 |
| Select でステータス選択可能 | モーダル開→ドロップダウン確認 |
| window.confirm が消えている | ルールタブで行クリック→ConfirmModal表示 |
| i18n キー不足なし | ja/en 両方でキーが表示される |

## 外部事例
該当なし（内部 UI 改善）

## 維持の仕組み
- ADR-027 CI lint が i18n ハードコードを検出: `.github/workflows/frontend-checks.yml`
- ADR-144 UI governance gate: `.github/workflows/ui-governance.yml`

## recon 相互参照
[docs/handoff/rule-test-ux/recon.md](./recon.md)
