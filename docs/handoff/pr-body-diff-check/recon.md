# Recon: PR本文バリデーション拡張（検査1-10）

日付: 2026-09-19
テーマ: PR本文の構造・内容エラーを段階的に検出するバリデーション体系の整備。検査1-6に加え、設計doc要件確認（検査7-8）・ファイルパス存在確認（検査9）・GO記録検証（検査10）を追加

## 現状

- `scripts/dev/validate-pr-body.sh`: PR本文検査スクリプト（検査1-6実装済み）
  - 検査1: 「標準ワークフロー確認」セクション存在確認
  - 検査2: recon.md パス存在確認
  - 検査3: 設計doc パス存在確認
  - 検査4: 「触るファイル:」セクション存在確認
  - 検査5: 「削除するファイル:」セクション存在確認
  - 検査6: git diff vs 宣言照合（PR #3554実装）
  - **検査7-10: 未実装**

- CI `check-process-artifacts.js` （検査7-10実装済み）
  - 検査7: 設計docの「外部・過去事例」セクション確認
  - 検査8: 設計docの「維持の仕組み」セクション確認（警告）
  - 検査9: バッククォート内ファイルパス存在確認
  - 検査10: ユーザー影響変更時のGO記録チェック

**問題**: validate-pr-body.sh と check-process-artifacts.js の検査ロジックが乖離
- ローカルで検査7-10が未実装 → author が CI まで待たなければエラーを検出できない
- CI と ローカル で複数回検査（冗長性）
- PR push → CI FAIL → 修正 のループが長くなる

## 検査7-10 の仕様

### 検査7: 設計docの「外部・過去事例」セクション確認

**実装箇所**: `scripts/dev/validate-pr-body.sh: 209-229行`

**ロジック** (`check-process-artifacts.js:437-450` と同一):
1. 設計docを読み込み
2. 正規表現 `^##[^\n]*外部[・\u30fb]過去事例[^\n]*` で「外部・過去事例」ヘッダを検索
3. ヘッダが見つからない → ❌ FAIL
4. ヘッダの直後から次の `##` セクションまでのコンテンツをチェック
5. コンテンツが空欄（5文字未満）→ ❌ FAIL

### 検査8: 設計docの「維持の仕組み」セクション確認

**実装箇所**: `scripts/dev/validate-pr-body.sh: 232-246行`

**ロジック** (`check-process-artifacts.js:455-489` と同一):
1. 設計docで `^##[^\n]*維持の仕組み[^\n]*$` を検索
2. セクションが見つからない → ⚠️ 警告（現在）
3. 見つかった場合、セクション内の「守り手:」行をチェック
4. 守り手が空欄 → ⚠️ 警告（現在）
5. **注記**: 将来 fail に引き上げ予定（ADR-121）

### 検査9: バッククォート内ファイルパス存在確認

**実装箇所**: `scripts/dev/validate-pr-body.sh: 249-280行`

**ロジック** (`check-process-artifacts.js:710-757` と同一):
1. 設計doc と recon.md から バッククォートで囲まれたテキストを抽出
2. 正規表現 `` `([^`\s]+?)(?::[\d]+(?:-[\d]+)?)?` `` で引用パスを検出
3. 拡張子チェック（`.tsx|ts|py|sql|yml|yaml|json|md|sh`）
4. HTTP(S) URL はスキップ
5. ファイル実在確認 → 不存在なら ❌ FAIL

### 検査10: ユーザー影響変更時のGO記録チェック

**実装箇所**: `scripts/dev/validate-pr-body.sh: 283-324行`

**ロジック** (`check-process-artifacts.js:849-866` と同一):
1. git diff で変更ファイルを取得
2. `frontend/src/` `backend/app/routers/` `backend/app/services/` マッチング
3. ユーザー影響ファイルの変更がある場合:
   - PR本文に `### GO記録` セクションが存在するか → なし → ❌ FAIL
   - GO記録内に 「GO発行者:」があるか → なし → ❌ FAIL
   - GO記録内に 「GO原文:」があるか → なし → ❌ FAIL
   - GO記録内に 「GO #<数字>」形式があるか → なし → ❌ FAIL

## テスト実績

**PR #3554 で検査6実装時の検証**:
- ✅ 全ファイル宣言済みPR本文 → exit 0
- ✅ 2ファイル宣言漏れPR本文 → exit 1 + ファイル名表示
- ✅ `PR_BODY_VALIDATE_SKIP=1` → exit 0

**本PR で検査7-10実装時に実施すべきテスト**:
- ✅ 設計docに「外部・過去事例」セクションがある → 検査7 PASS
- ✅ 設計docに「外部・過去事例」セクションがない → 検査7 FAIL
- ✅ 設計docに「維持の仕組み」セクションがある → 検査8 警告なし
- ✅ バッククォート内パスが存在 → 検査9 PASS
- ✅ バッククォート内パスが不存在 → 検査9 FAIL
- ✅ frontend/src/ 変更+GO記録あり → 検査10 PASS
- ✅ frontend/src/ 変更+GO記録なし → 検査10 FAIL

## ADR 関連参照

- ADR-155: PR本文検査スコープの拡張（検査1-6実装済み）
- ADR-121: 標準ワークフロー遵守の強制化

## 実装の根拠

### 設計・検査の分離化（現状の問題）

**Before** (現在):
```
Author が PR push
  ↓
CI: check-process-artifacts.js（検査1-10実行）
  ↓
検査7-10 FAIL （ローカルで検出不可）
  ↓
Author が修正・再 push
  （最大 30分/ループ × 複数回）
```

**After** (本PR後):
```
Author がローカル commit-msg hook
  ↓
validate-pr-body.sh（検査1-10実行）
  ↓
検査FAIL → Author が即座に修正
  ↓
修正後 git push（最初の push で CI PASS）
  （feedback loop 短縮）
```

### 同期化ルール

- validate-pr-body.sh と check-process-artifacts.js の検査ロジックは完全一致を維持
- 一方が変更される場合、必ずもう一方も同期更新（ADR-155 更新時に記載）
- 乖離検知時は両ファイルの diff を取得して統一

## 参考実装

`check-process-artifacts.js` での実装は以下で確認:
- 検査7: `scripts/check-process-artifacts.js:437-450`
- 検査8: `scripts/check-process-artifacts.js:455-489`
- 検査9: `scripts/check-process-artifacts.js:710-757`
- 検査10: `scripts/check-process-artifacts.js:849-866`
