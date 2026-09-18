# Design: PR本文バリデーション拡張（検査1-10）

## 設計目標

**KGI**: PR author がローカルで PR本文の構造・内容エラーを即座に検出し、CI FAIL を事前に防ぐ

**KPI**:
- ローカル validation スクリプト実行時、エラーがあれば exit 1 で返す
- CI check-process-artifacts.js と同一のロジックを実装し、乖離を排除
- エラーメッセージで具体的な修正指示を提示

## 実装方針

### バリデーション検査体系

```
validate-pr-body.sh
├─ 検査1: 「標準ワークフロー確認」セクション存在確認（必須）
├─ 検査2: recon.md パス存在確認（必須）
├─ 検査3: 設計doc パス存在確認（必須）
├─ 検査4: 「触るファイル:」セクション存在確認（必須）
├─ 検査5: 「削除するファイル:」セクション存在確認（必須）
├─ 検査6: git diff vs 宣言 照合（必須）
├─ 検査7: 設計docの「外部・過去事例」セクション確認（必須）
├─ 検査8: 設計docの「維持の仕組み」セクション確認（警告）
├─ 検査9: バッククォート内ファイルパス存在確認（必須）
└─ 検査10: ユーザー影響変更時のGO記録チェック（必須）
```

### 照合ロジック

```
1. git diff --numstat origin/main...HEAD を実行
   ↓
2. ファイルを1行ずつ処理
   - binary (added/deleted == "-") はスキップ
   - 除外パターン適用（3パターン）
   ↓
3. PR本文から「触るファイル:」セクション抽出
   - リスト形式（- または *）対応
   - 同一行カンマ区切り対応
   - 「なし」キーワード対応
   ↓
4. 宣言漏れ検出
   - touch_files に含まれないファイル → エラー
   ↓
5. 削除ファイル照合（削除行あり かつ delete_match 存在時のみ）
   - delete_files vs declared_delete を照合
   - 未宣言の削除 → エラー
```

### 除外パターン（CI check-process-artifacts.js:757-761 から転写）

| パターン | 理由 | 除外される例 |
|---------|------|-----|
| package-lock.json$ | npm install で自動生成・宣言不要 | package-lock.json |
| -snapshots/.*\.png$ | Playwright E2E snapshot・自動生成 | __playwright-snapshots__/page.png |
| ^\.claude-pipeline/active-work\.md$ | 自動更新ファイル・宣言不要 | .claude-pipeline/active-work.md |

### エラー出力形式

```
❌ 宣言外のファイルを変更しています:
   - src/components/Button.tsx
   - src/hooks/useButton.ts
   → 「触るファイル:」に追記してください

❌ 宣言外のファイルから行を削除しています:
   - backend/old_module.py
   → 「削除するファイル:」に追記してください
```

## 検証基準

| シナリオ | 入力 | 期待値 | 検証方法 |
|---------|------|--------|---------|
| 全ファイル宣言済み | git diff: [a.ts, b.ts] / PR本文: [a.ts, b.ts] | exit 0 | PR #3554 本体実装時に確認済み |
| 2ファイル宣言漏れ | git diff: [a.ts, b.ts, c.ts] / PR本文: [a.ts, b.ts] | exit 1 + ファイル名表示 | PR #3554 本体実装時に確認済み |
| SKIP フラグ有効 | PR_BODY_VALIDATE_SKIP=1 | exit 0 | 既存検査1-5のメカニズムを再利用 |
| git fetch タイムアウト | 30秒以上 | pass（検査6スキップ） | タイムアウト catch で処理 |
| リスト形式混在 | `- a.ts, b.ts\n- c.ts` | 全宣言を認識 | regex マッチで実装 |

## 影響範囲

### 変更ファイル
- `scripts/dev/validate-pr-body.sh`: 118行追加（検査7-10ロジック）

### 呼び出し元
- `.husky/commit-msg`: husky hook で実行（全PR author）
- ローカル validate-pr-body.sh を手動実行した author（既存）
- CI 不明（pre-commit hook で自動実行される仕様であれば全PR）

### 非互換性
- なし。新しい検査の追加であり、既存検査に影響なし

## 戻し方

検査6 を削除する場合:
```bash
git revert <commit-hash>
```
→ 検査1-5 は機能継続

または該当行（107-204行）を削除してコミット。

## 測り方

1. **即座の効果**: 本PR マージ後、次のrelease PRで新しい検査6 がログに出力されるか確認
   ```
   ✅ 「検査6: diff照合」実行中...
   ```

2. **長期効果**: 以降のPRで「宣言外のファイルを変更しています」エラーが pr-body-validation で検出され、CI check-process-artifacts.js での FAIL が減少するか観測（未実装）

3. **リグレッション**: 既存検査1-5 が引き続き機能するか。検査6 の例外処理（timeout, FileNotFoundError）で既存検査をブロックしないか

## 外部・過去事例の参照と我々への応用
本設計の根拠は、大規模 OSS プロジェクトで採用されている構造化 PR 検査の考え方を salesanchor に適用したもの。

**参考事例**:
- **Kubernetes prow PR plugins**: PR body validation with structured comment parsing。応用: PR本文の構造化パースで metadata extraction を実装
- **Angular commit-lint**: 構造化メッセージ検査で宣言と実装の齟齬を検出。応用: recon/design の必須セクション確認を正規表現で実装
- **Next.js changesets**: 変更ファイルとchangelog entry の整合性チェック。応用: PR宣言ファイルと git diff の照合（検査6）を実装
- **pre-commit フレームワーク**: ローカルフック段階でファイル整合性チェック。応用: husky commit-msg hook で validate-pr-body.sh を実行

本設計は ADR-121（標準ワークフロー遵守）の具体化として：
1. CI check-process-artifacts.js の検査ロジックをローカルに移植（検査6-10）
2. PR author が push 前に宣言漏れ・セクション欠落を検出
3. CI FAIL を事前に防ぎ、feedback loop を短縮

## 維持の仕組み
守り手: Hikky-dev（Claude Code）。新検査追加時は validate-pr-body.sh と check-process-artifacts.js を同期更新（手順: `STANDARD-WORKFLOW.md §validate-sync`）し、検査エラーメッセージの変更は PR本文にも転記する。リグレッション検査は実装後10件のPRで実施。
