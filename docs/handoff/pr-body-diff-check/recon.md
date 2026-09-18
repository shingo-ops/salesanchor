# Recon: PR本文 diff照合チェック追加（検査6）

日付: 2026-09-18
テーマ: PR本文 の「触るファイル:」「削除するファイル:」宣言と実際のgit diff結果を照合し、宣言漏れを検出する検査機能の追加

## 現状

- `scripts/dev/validate-pr-body.sh`: PR本文の必須フォーマットチェック（検査1-5）
  - 検査1: 「標準ワークフロー確認」セクション存在確認
  - 検査2: recon.md パス存在確認
  - 検査3: 設計doc パス存在確認
  - 検査4: 「触るファイル:」セクション存在確認
  - 検査5: 「削除するファイル:」セクション存在確認
  - **検査6: 未実装**

- PR #3554 で検査6 の必要性が明確化
  - author が「触るファイル:」に記入したつもりでも、実際の変更ファイルが宣言外のものを含んでいると CI check-process-artifacts.js でキャッチされて FAIL に
  - ローカル検証時点で宣言漏れを検出できれば、author 体験が向上

## 検査6 の仕様

**実装箇所**: `scripts/dev/validate-pr-body.sh: 107-204行`

**処理フロー**:
1. PR本文から「触るファイル:」セクションを抽出
2. `git diff --numstat origin/main...HEAD` で実際の変更ファイルリストを取得
3. 除外パターン適用（CI check-process-artifacts.js:757-761 と同一）
   - `package-lock.json$`
   - `-snapshots/.*\.png$`
   - `^\.claude-pipeline/active-work\.md$`
4. **宣言漏れ検出**: 変更されたファイルで、PR本文に記載されていないもの → エラー出力
5. **削除漏れ検出**: 削除行を含むファイルで、「削除するファイル:」に記載されていないもの → エラー出力

**エラーメッセージ**:
```
❌ 宣言外のファイルを変更しています:
   - path/to/undeclared-file.ts
   → 「触るファイル:」に追記してください

❌ 宣言外のファイルから行を削除しています:
   - path/to/undeclared-deletion-file.py
   → 「削除するファイル:」に追記してください
```

## テスト実績（PR #3554での検証）

- ✅ 全ファイル宣言済みPR本文 → exit 0
- ✅ 2ファイル宣言漏れPR本文 → exit 1 + ファイル名表示
- ✅ `PR_BODY_VALIDATE_SKIP=1` → exit 0

## ADR 関連参照

- ADR-155（未作成予定）: PR本文検査スコープの拡張

## 実装の根拠

`check-process-artifacts.js` との同期性を確保することで:
- 開発者が ローカル push 前に検査6で宣言漏れを検出可能
- CI での check-process-artifacts.js との重複検証で多重防衛
- 不整合の余地を排除

## 外部事例

PR body validation is standard in large projects:
- Kubernetes: prow plugin with PR decoration
- Angular: commit message linter with PR templates
- Next.js: PR check automation with artifact tracking
